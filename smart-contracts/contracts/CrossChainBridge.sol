// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title CrossChainBridge
 * @notice Bridge contract for cross-chain NWR token transfers
 * @dev Implements lock-and-mint / burn-and-release mechanism with validator signatures
 */
contract CrossChainBridge is Ownable, ReentrancyGuard, Pausable {
    
    // ==================== Types ====================
    
    struct BridgeRequest {
        address sender;
        address recipient;
        uint256 amount;
        uint256 sourceChain;
        uint256 destChain;
        uint256 timestamp;
        bytes32 txHash;
        bool processed;
    }
    
    struct ChainConfig {
        bool enabled;
        uint256 minAmount;
        uint256 maxAmount;
        uint256 dailyLimit;
        uint256 dailyUsed;
        uint256 lastReset;
        address bridgeContract;
    }
    
    // ==================== State ====================
    
    IERC20 public token;
    
    uint256 public currentChainId;
    uint256 public bridgeFee = 50; // 0.5% in basis points
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public requestCount;
    
    mapping(uint256 => ChainConfig) public chains;
    mapping(bytes32 => BridgeRequest) public requests;
    mapping(bytes32 => bool) public processedHashes;
    mapping(address => bool) public validators;
    uint256 public validatorCount;
    uint256 public requiredSignatures = 2;
    
    uint256[] public supportedChains;
    
    // Chain IDs
    uint256 public constant ETHEREUM = 1;
    uint256 public constant POLYGON = 137;
    uint256 public constant BSC = 56;
    uint256 public constant ARBITRUM = 42161;
    uint256 public constant OPTIMISM = 10;
    
    // ==================== Events ====================
    
    event BridgeInitiated(
        bytes32 indexed requestId,
        address indexed sender,
        address recipient,
        uint256 amount,
        uint256 destChain
    );
    event BridgeCompleted(
        bytes32 indexed requestId,
        address indexed recipient,
        uint256 amount,
        uint256 sourceChain
    );
    event ValidatorAdded(address indexed validator);
    event ValidatorRemoved(address indexed validator);
    event ChainEnabled(uint256 indexed chainId, address bridgeContract);
    event ChainDisabled(uint256 indexed chainId);
    event FeeUpdated(uint256 newFee);
    
    // ==================== Modifiers ====================
    
    modifier onlyValidator() {
        require(validators[msg.sender], "Not a validator");
        _;
    }
    
    modifier validChain(uint256 chainId) {
        require(chains[chainId].enabled, "Chain not supported");
        _;
    }
    
    // ==================== Constructor ====================
    
    constructor(address _token, uint256 _chainId) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token");
        token = IERC20(_token);
        currentChainId = _chainId;
        
        // Add deployer as initial validator
        validators[msg.sender] = true;
        validatorCount = 1;
        
        // Initialize supported chains
        _initializeChain(ETHEREUM, 100 * 1e18, 1000000 * 1e18, 10000000 * 1e18);
        _initializeChain(POLYGON, 10 * 1e18, 1000000 * 1e18, 10000000 * 1e18);
        _initializeChain(BSC, 10 * 1e18, 1000000 * 1e18, 10000000 * 1e18);
        _initializeChain(ARBITRUM, 50 * 1e18, 1000000 * 1e18, 10000000 * 1e18);
    }
    
    function _initializeChain(
        uint256 chainId,
        uint256 minAmount,
        uint256 maxAmount,
        uint256 dailyLimit
    ) internal {
        chains[chainId] = ChainConfig({
            enabled: chainId != currentChainId,
            minAmount: minAmount,
            maxAmount: maxAmount,
            dailyLimit: dailyLimit,
            dailyUsed: 0,
            lastReset: block.timestamp,
            bridgeContract: address(0)
        });
        supportedChains.push(chainId);
    }
    
    // ==================== Bridge Functions ====================
    
    /**
     * @notice Initiate a bridge transfer to another chain
     * @param recipient Address on destination chain
     * @param amount Amount of tokens to bridge
     * @param destChain Destination chain ID
     */
    function bridge(
        address recipient,
        uint256 amount,
        uint256 destChain
    ) external nonReentrant whenNotPaused validChain(destChain) returns (bytes32) {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be > 0");
        
        ChainConfig storage config = chains[destChain];
        require(amount >= config.minAmount, "Below minimum");
        require(amount <= config.maxAmount, "Above maximum");
        
        // Check daily limit
        _resetDailyLimitIfNeeded(destChain);
        require(config.dailyUsed + amount <= config.dailyLimit, "Daily limit exceeded");
        config.dailyUsed += amount;
        
        // Calculate fee
        uint256 fee = (amount * bridgeFee) / BASIS_POINTS;
        uint256 netAmount = amount - fee;
        
        // Lock tokens
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        // Create request
        requestCount++;
        bytes32 requestId = keccak256(abi.encodePacked(
            currentChainId,
            destChain,
            msg.sender,
            recipient,
            amount,
            block.timestamp,
            requestCount
        ));
        
        requests[requestId] = BridgeRequest({
            sender: msg.sender,
            recipient: recipient,
            amount: netAmount,
            sourceChain: currentChainId,
            destChain: destChain,
            timestamp: block.timestamp,
            txHash: bytes32(0),
            processed: false
        });
        
        emit BridgeInitiated(requestId, msg.sender, recipient, netAmount, destChain);
        
        return requestId;
    }
    
    /**
     * @notice Complete a bridge transfer from another chain (called by validators)
     * @param requestId The bridge request ID from source chain
     * @param recipient Recipient address
     * @param amount Amount to release
     * @param sourceChain Source chain ID
     * @param signatures Array of validator signatures
     */
    function completeBridge(
        bytes32 requestId,
        address recipient,
        uint256 amount,
        uint256 sourceChain,
        bytes[] calldata signatures
    ) external nonReentrant whenNotPaused {
        require(!processedHashes[requestId], "Already processed");
        require(signatures.length >= requiredSignatures, "Insufficient signatures");
        
        // Verify signatures
        bytes32 messageHash = keccak256(abi.encodePacked(
            requestId,
            recipient,
            amount,
            sourceChain,
            currentChainId
        ));
        
        uint256 validSignatures = 0;
        address[] memory signers = new address[](signatures.length);
        
        for (uint256 i = 0; i < signatures.length; i++) {
            address signer = _recoverSigner(messageHash, signatures[i]);
            
            // Check if valid validator and not duplicate
            if (validators[signer]) {
                bool isDuplicate = false;
                for (uint256 j = 0; j < validSignatures; j++) {
                    if (signers[j] == signer) {
                        isDuplicate = true;
                        break;
                    }
                }
                if (!isDuplicate) {
                    signers[validSignatures] = signer;
                    validSignatures++;
                }
            }
        }
        
        require(validSignatures >= requiredSignatures, "Not enough valid signatures");
        
        processedHashes[requestId] = true;
        
        // Release tokens
        require(token.transfer(recipient, amount), "Transfer failed");
        
        emit BridgeCompleted(requestId, recipient, amount, sourceChain);
    }
    
    function _resetDailyLimitIfNeeded(uint256 chainId) internal {
        ChainConfig storage config = chains[chainId];
        if (block.timestamp >= config.lastReset + 1 days) {
            config.dailyUsed = 0;
            config.lastReset = block.timestamp;
        }
    }
    
    function _recoverSigner(bytes32 messageHash, bytes memory signature) internal pure returns (address) {
        bytes32 ethSignedMessageHash = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32",
            messageHash
        ));
        
        require(signature.length == 65, "Invalid signature length");
        
        bytes32 r;
        bytes32 s;
        uint8 v;
        
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        
        if (v < 27) v += 27;
        require(v == 27 || v == 28, "Invalid signature v");
        
        return ecrecover(ethSignedMessageHash, v, r, s);
    }
    
    // ==================== View Functions ====================
    
    function getRequest(bytes32 requestId) external view returns (BridgeRequest memory) {
        return requests[requestId];
    }
    
    function getSupportedChains() external view returns (uint256[] memory) {
        return supportedChains;
    }
    
    function getChainConfig(uint256 chainId) external view returns (
        bool enabled,
        uint256 minAmount,
        uint256 maxAmount,
        uint256 dailyLimit,
        uint256 dailyRemaining
    ) {
        ChainConfig storage config = chains[chainId];
        uint256 remaining = config.dailyLimit > config.dailyUsed ? 
            config.dailyLimit - config.dailyUsed : 0;
        return (config.enabled, config.minAmount, config.maxAmount, config.dailyLimit, remaining);
    }
    
    function estimateFee(uint256 amount) external view returns (uint256) {
        return (amount * bridgeFee) / BASIS_POINTS;
    }
    
    // ==================== Admin Functions ====================
    
    function addValidator(address validator) external onlyOwner {
        require(!validators[validator], "Already validator");
        validators[validator] = true;
        validatorCount++;
        emit ValidatorAdded(validator);
    }
    
    function removeValidator(address validator) external onlyOwner {
        require(validators[validator], "Not a validator");
        require(validatorCount > requiredSignatures, "Cannot go below required");
        validators[validator] = false;
        validatorCount--;
        emit ValidatorRemoved(validator);
    }
    
    function enableChain(uint256 chainId, address bridgeContract) external onlyOwner {
        chains[chainId].enabled = true;
        chains[chainId].bridgeContract = bridgeContract;
        emit ChainEnabled(chainId, bridgeContract);
    }
    
    function disableChain(uint256 chainId) external onlyOwner {
        chains[chainId].enabled = false;
        emit ChainDisabled(chainId);
    }
    
    function updateFee(uint256 newFee) external onlyOwner {
        require(newFee <= 500, "Max 5% fee");
        bridgeFee = newFee;
        emit FeeUpdated(newFee);
    }
    
    function updateRequiredSignatures(uint256 newRequired) external onlyOwner {
        require(newRequired > 0 && newRequired <= validatorCount, "Invalid requirement");
        requiredSignatures = newRequired;
    }
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function withdrawFees(address to) external onlyOwner {
        uint256 balance = token.balanceOf(address(this));
        require(token.transfer(to, balance), "Transfer failed");
    }
}
