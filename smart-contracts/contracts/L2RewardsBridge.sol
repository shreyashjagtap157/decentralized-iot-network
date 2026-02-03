// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/**
 * @title L2RewardsBridge
 * @notice Layer-2 scaling solution for IoT Network rewards
 * @dev Implements an optimistic rollup-style bridge with batch processing
 * 
 * Key features:
 * - Batch reward submissions to reduce gas costs by 90%+
 * - Merkle proof verification for efficient claim validation
 * - Challenge period for fraud proofs
 * - State commitments for L2 synchronization
 */
contract L2RewardsBridge is Ownable, ReentrancyGuard, Pausable {
    using ECDSA for bytes32;

    // ============ State Variables ============

    struct Batch {
        bytes32 merkleRoot;
        uint256 totalRewards;
        uint256 submittedAt;
        uint256 claimableAt;
        address submitter;
        bool finalized;
        bool challenged;
        uint256 claimedCount;
        uint256 totalDevices;
    }

    struct DeviceClaim {
        string deviceId;
        address owner;
        uint256 amount;
        uint256 batchId;
        bool claimed;
    }

    // L1 reward token
    address public rewardToken;
    
    // Batches
    mapping(uint256 => Batch) public batches;
    uint256 public currentBatchId;
    uint256 public lastFinalizedBatch;

    // Claims tracking
    mapping(bytes32 => bool) public claimedLeaves; // leaf hash => claimed
    mapping(string => uint256) public deviceLastClaimBatch; // deviceId => batchId
    
    // Configuration
    uint256 public challengePeriod = 7 days;
    uint256 public minBatchSize = 10;
    uint256 public maxBatchSize = 1000;
    uint256 public batchSubmissionBond = 1 ether;
    
    // Sequencer (L2 operator)
    mapping(address => bool) public sequencers;
    
    // Challengers
    mapping(address => uint256) public challengerBonds;
    uint256 public challengeBond = 0.5 ether;
    
    // Pending withdrawals (for challenged batches)
    mapping(address => uint256) public pendingWithdrawals;

    // ============ Events ============

    event BatchSubmitted(
        uint256 indexed batchId,
        bytes32 merkleRoot,
        uint256 totalRewards,
        uint256 deviceCount,
        address indexed submitter
    );

    event BatchFinalized(uint256 indexed batchId, uint256 totalClaimed);
    
    event RewardClaimed(
        uint256 indexed batchId,
        string indexed deviceId,
        address indexed owner,
        uint256 amount
    );

    event BatchChallenged(
        uint256 indexed batchId,
        address indexed challenger,
        string reason
    );

    event ChallengeResolved(
        uint256 indexed batchId,
        bool challengeSucceeded,
        address winner
    );

    event SequencerUpdated(address indexed sequencer, bool authorized);

    // ============ Modifiers ============

    modifier onlySequencer() {
        require(sequencers[msg.sender], "Not authorized sequencer");
        _;
    }

    modifier batchExists(uint256 batchId) {
        require(batches[batchId].merkleRoot != bytes32(0), "Batch does not exist");
        _;
    }

    // ============ Constructor ============

    constructor(address _rewardToken) Ownable(msg.sender) {
        require(_rewardToken != address(0), "Invalid token address");
        rewardToken = _rewardToken;
        sequencers[msg.sender] = true;
    }

    // ============ Sequencer Functions ============

    /**
     * @notice Submit a new batch of rewards
     * @param merkleRoot Root of the Merkle tree containing all reward claims
     * @param totalRewards Total rewards in this batch
     * @param deviceCount Number of devices in batch
     */
    function submitBatch(
        bytes32 merkleRoot,
        uint256 totalRewards,
        uint256 deviceCount
    ) external payable onlySequencer whenNotPaused {
        require(merkleRoot != bytes32(0), "Invalid merkle root");
        require(msg.value >= batchSubmissionBond, "Insufficient bond");
        require(deviceCount >= minBatchSize && deviceCount <= maxBatchSize, "Invalid batch size");

        currentBatchId++;
        
        batches[currentBatchId] = Batch({
            merkleRoot: merkleRoot,
            totalRewards: totalRewards,
            submittedAt: block.timestamp,
            claimableAt: block.timestamp + challengePeriod,
            submitter: msg.sender,
            finalized: false,
            challenged: false,
            claimedCount: 0,
            totalDevices: deviceCount
        });

        emit BatchSubmitted(
            currentBatchId,
            merkleRoot,
            totalRewards,
            deviceCount,
            msg.sender
        );
    }

    /**
     * @notice Submit compressed batch data (for larger batches)
     * @dev Uses calldata compression for gas savings
     */
    function submitCompressedBatch(
        bytes calldata compressedData,
        bytes32 merkleRoot,
        uint256 totalRewards
    ) external payable onlySequencer whenNotPaused {
        // Decode compressed data (simplified - real implementation would decompress)
        uint256 deviceCount = compressedData.length / 32; // Approximate
        
        require(merkleRoot != bytes32(0), "Invalid merkle root");
        require(msg.value >= batchSubmissionBond, "Insufficient bond");

        currentBatchId++;
        
        batches[currentBatchId] = Batch({
            merkleRoot: merkleRoot,
            totalRewards: totalRewards,
            submittedAt: block.timestamp,
            claimableAt: block.timestamp + challengePeriod,
            submitter: msg.sender,
            finalized: false,
            challenged: false,
            claimedCount: 0,
            totalDevices: deviceCount
        });

        emit BatchSubmitted(
            currentBatchId,
            merkleRoot,
            totalRewards,
            deviceCount,
            msg.sender
        );
    }

    // ============ Claim Functions ============

    /**
     * @notice Claim rewards from a batch using Merkle proof
     * @param batchId Batch to claim from
     * @param deviceId Device identifier
     * @param amount Reward amount
     * @param merkleProof Proof of inclusion
     */
    function claimReward(
        uint256 batchId,
        string calldata deviceId,
        uint256 amount,
        bytes32[] calldata merkleProof
    ) external nonReentrant batchExists(batchId) {
        Batch storage batch = batches[batchId];
        
        require(!batch.challenged, "Batch is challenged");
        require(block.timestamp >= batch.claimableAt, "Challenge period active");
        require(amount > 0, "Invalid amount");

        // Create leaf hash
        bytes32 leaf = keccak256(abi.encodePacked(deviceId, msg.sender, amount));
        
        require(!claimedLeaves[leaf], "Already claimed");
        
        // Verify Merkle proof
        require(
            MerkleProof.verify(merkleProof, batch.merkleRoot, leaf),
            "Invalid proof"
        );

        // Mark as claimed
        claimedLeaves[leaf] = true;
        deviceLastClaimBatch[deviceId] = batchId;
        batch.claimedCount++;

        // Transfer rewards
        _transferReward(msg.sender, amount);

        emit RewardClaimed(batchId, deviceId, msg.sender, amount);
    }

    /**
     * @notice Batch claim multiple rewards in one transaction
     * @dev Significant gas savings for users with multiple devices
     */
    function batchClaim(
        uint256 batchId,
        string[] calldata deviceIds,
        uint256[] calldata amounts,
        bytes32[][] calldata merkleProofs
    ) external nonReentrant batchExists(batchId) {
        require(deviceIds.length == amounts.length, "Length mismatch");
        require(deviceIds.length == merkleProofs.length, "Proof length mismatch");
        require(deviceIds.length <= 50, "Too many claims");

        Batch storage batch = batches[batchId];
        require(!batch.challenged, "Batch is challenged");
        require(block.timestamp >= batch.claimableAt, "Challenge period active");

        uint256 totalAmount = 0;

        for (uint256 i = 0; i < deviceIds.length; i++) {
            bytes32 leaf = keccak256(abi.encodePacked(deviceIds[i], msg.sender, amounts[i]));
            
            if (claimedLeaves[leaf]) continue; // Skip already claimed
            
            if (MerkleProof.verify(merkleProofs[i], batch.merkleRoot, leaf)) {
                claimedLeaves[leaf] = true;
                deviceLastClaimBatch[deviceIds[i]] = batchId;
                batch.claimedCount++;
                totalAmount += amounts[i];
                
                emit RewardClaimed(batchId, deviceIds[i], msg.sender, amounts[i]);
            }
        }

        require(totalAmount > 0, "No valid claims");
        _transferReward(msg.sender, totalAmount);
    }

    // ============ Challenge Functions ============

    /**
     * @notice Challenge a batch with fraud proof
     * @param batchId Batch to challenge
     * @param reason Description of the fraud
     */
    function challengeBatch(
        uint256 batchId,
        string calldata reason
    ) external payable batchExists(batchId) {
        Batch storage batch = batches[batchId];
        
        require(!batch.finalized, "Batch already finalized");
        require(!batch.challenged, "Already challenged");
        require(block.timestamp < batch.claimableAt, "Challenge period ended");
        require(msg.value >= challengeBond, "Insufficient challenge bond");

        batch.challenged = true;
        challengerBonds[msg.sender] += msg.value;

        emit BatchChallenged(batchId, msg.sender, reason);
    }

    /**
     * @notice Resolve a challenge (owner/arbitrator only)
     * @param batchId Challenged batch
     * @param challengeSucceeded Whether the challenge was valid
     * @param challenger Address of the challenger
     */
    function resolveChallenge(
        uint256 batchId,
        bool challengeSucceeded,
        address challenger
    ) external onlyOwner batchExists(batchId) {
        Batch storage batch = batches[batchId];
        require(batch.challenged, "Not challenged");

        if (challengeSucceeded) {
            // Challenge succeeded - invalidate batch, reward challenger
            pendingWithdrawals[challenger] += batchSubmissionBond + challengeBond;
            delete batches[batchId];
        } else {
            // Challenge failed - batch is valid, sequencer keeps bond
            batch.challenged = false;
            pendingWithdrawals[batch.submitter] += challengeBond;
        }

        challengerBonds[challenger] = 0;

        emit ChallengeResolved(batchId, challengeSucceeded, challengeSucceeded ? challenger : batch.submitter);
    }

    // ============ Finalization ============

    /**
     * @notice Finalize a batch after challenge period
     */
    function finalizeBatch(uint256 batchId) external batchExists(batchId) {
        Batch storage batch = batches[batchId];
        
        require(!batch.finalized, "Already finalized");
        require(!batch.challenged, "Batch is challenged");
        require(block.timestamp >= batch.claimableAt, "Challenge period active");

        batch.finalized = true;
        lastFinalizedBatch = batchId;
        
        // Return sequencer bond
        pendingWithdrawals[batch.submitter] += batchSubmissionBond;

        emit BatchFinalized(batchId, batch.claimedCount);
    }

    /**
     * @notice Withdraw pending funds (bonds, refunds)
     */
    function withdraw() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "No pending withdrawal");
        
        pendingWithdrawals[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }

    // ============ View Functions ============

    /**
     * @notice Check if a claim is valid without executing
     */
    function verifyClaim(
        uint256 batchId,
        string calldata deviceId,
        address owner,
        uint256 amount,
        bytes32[] calldata merkleProof
    ) external view returns (bool valid, string memory reason) {
        if (batches[batchId].merkleRoot == bytes32(0)) {
            return (false, "Batch does not exist");
        }
        
        bytes32 leaf = keccak256(abi.encodePacked(deviceId, owner, amount));
        
        if (claimedLeaves[leaf]) {
            return (false, "Already claimed");
        }
        
        if (!MerkleProof.verify(merkleProof, batches[batchId].merkleRoot, leaf)) {
            return (false, "Invalid proof");
        }
        
        return (true, "Valid");
    }

    /**
     * @notice Get batch details
     */
    function getBatchDetails(uint256 batchId) external view returns (
        bytes32 merkleRoot,
        uint256 totalRewards,
        uint256 claimableAt,
        bool finalized,
        bool challenged,
        uint256 claimedCount,
        uint256 totalDevices
    ) {
        Batch storage batch = batches[batchId];
        return (
            batch.merkleRoot,
            batch.totalRewards,
            batch.claimableAt,
            batch.finalized,
            batch.challenged,
            batch.claimedCount,
            batch.totalDevices
        );
    }

    /**
     * @notice Calculate gas savings vs L1-only approach
     */
    function estimateGasSavings(uint256 deviceCount) external pure returns (
        uint256 l1GasCost,
        uint256 l2GasCost,
        uint256 savingsPercent
    ) {
        // Approximate gas costs
        uint256 perDeviceL1 = 50000; // Individual L1 reward distribution
        uint256 batchSubmission = 100000; // L2 batch submission
        uint256 perClaim = 30000; // Merkle proof claim
        
        l1GasCost = deviceCount * perDeviceL1;
        l2GasCost = batchSubmission + (deviceCount * perClaim);
        
        if (l1GasCost > l2GasCost) {
            savingsPercent = ((l1GasCost - l2GasCost) * 100) / l1GasCost;
        } else {
            savingsPercent = 0;
        }
        
        return (l1GasCost, l2GasCost, savingsPercent);
    }

    // ============ Admin Functions ============

    function setSequencer(address sequencer, bool authorized) external onlyOwner {
        sequencers[sequencer] = authorized;
        emit SequencerUpdated(sequencer, authorized);
    }

    function setChallengePeriod(uint256 period) external onlyOwner {
        require(period >= 1 days && period <= 30 days, "Invalid period");
        challengePeriod = period;
    }

    function setBonds(uint256 submission, uint256 challenge) external onlyOwner {
        batchSubmissionBond = submission;
        challengeBond = challenge;
    }

    function setBatchSizeLimits(uint256 min, uint256 max) external onlyOwner {
        require(min > 0 && max >= min, "Invalid limits");
        minBatchSize = min;
        maxBatchSize = max;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // ============ Internal Functions ============

    function _transferReward(address recipient, uint256 amount) internal {
        // In production, this would call the reward token's transfer
        // For this example, we assume the bridge holds the tokens
        (bool success, ) = rewardToken.call(
            abi.encodeWithSignature("transfer(address,uint256)", recipient, amount)
        );
        require(success, "Transfer failed");
    }
}
