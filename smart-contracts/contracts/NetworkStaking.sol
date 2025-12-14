// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title NetworkStaking
 * @notice Staking contract for NWR tokens to earn bonus rewards and governance power
 * @dev Implements tiered staking with reward multipliers
 */
contract NetworkStaking is Ownable, ReentrancyGuard {
    
    // ==================== Types ====================
    
    struct StakeInfo {
        uint256 amount;
        uint256 startTime;
        uint256 lockDuration;
        uint256 rewardMultiplier;
        uint256 lastClaimTime;
        uint256 accumulatedRewards;
    }
    
    struct StakingTier {
        uint256 minAmount;
        uint256 multiplier;     // In basis points (10000 = 1x)
        uint256 minLockDays;
        string name;
    }
    
    // ==================== State ====================
    
    IERC20 public stakingToken;
    
    mapping(address => StakeInfo) public stakes;
    mapping(uint256 => StakingTier) public tiers;
    uint256 public tierCount;
    
    uint256 public totalStaked;
    uint256 public rewardPool;
    uint256 public rewardRatePerSecond;
    uint256 public constant BASIS_POINTS = 10000;
    
    uint256 public earlyUnstakePenalty = 1000; // 10% penalty
    uint256 public minStakeDuration = 7 days;
    
    // ==================== Events ====================
    
    event Staked(address indexed user, uint256 amount, uint256 lockDuration, uint256 tier);
    event Unstaked(address indexed user, uint256 amount, uint256 penalty);
    event RewardsClaimed(address indexed user, uint256 amount);
    event RewardPoolFunded(uint256 amount);
    event TierAdded(uint256 indexed tierId, string name, uint256 minAmount, uint256 multiplier);
    
    // ==================== Constructor ====================
    
    constructor(address _stakingToken) Ownable(msg.sender) {
        require(_stakingToken != address(0), "Invalid token");
        stakingToken = IERC20(_stakingToken);
        
        rewardRatePerSecond = 1e15; // 0.001 tokens per second per staked token
        
        // Initialize default tiers
        _addTier(1000 * 1e18,   10000, 7,   "Bronze");      // 1x multiplier, 7 days
        _addTier(10000 * 1e18,  12500, 30,  "Silver");      // 1.25x multiplier, 30 days
        _addTier(50000 * 1e18,  15000, 90,  "Gold");        // 1.5x multiplier, 90 days
        _addTier(100000 * 1e18, 20000, 180, "Platinum");    // 2x multiplier, 180 days
        _addTier(500000 * 1e18, 30000, 365, "Diamond");     // 3x multiplier, 365 days
    }
    
    // ==================== Staking Functions ====================
    
    /**
     * @notice Stake tokens with a specified lock duration
     * @param amount Amount of tokens to stake
     * @param lockDays Lock duration in days
     */
    function stake(uint256 amount, uint256 lockDays) external nonReentrant {
        require(amount > 0, "Cannot stake 0");
        require(lockDays >= 7, "Minimum 7 days lock");
        
        // Calculate tier and multiplier
        (uint256 tier, uint256 multiplier) = _calculateTier(amount, lockDays);
        
        // Claim any pending rewards first
        if (stakes[msg.sender].amount > 0) {
            _claimRewards(msg.sender);
        }
        
        // Transfer tokens
        require(stakingToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        
        // Update stake
        StakeInfo storage stakeInfo = stakes[msg.sender];
        stakeInfo.amount += amount;
        stakeInfo.startTime = block.timestamp;
        stakeInfo.lockDuration = lockDays * 1 days;
        stakeInfo.rewardMultiplier = multiplier;
        stakeInfo.lastClaimTime = block.timestamp;
        
        totalStaked += amount;
        
        emit Staked(msg.sender, amount, lockDays, tier);
    }
    
    /**
     * @notice Unstake tokens (may incur penalty if before lock expiry)
     */
    function unstake(uint256 amount) external nonReentrant {
        StakeInfo storage stakeInfo = stakes[msg.sender];
        require(stakeInfo.amount >= amount, "Insufficient stake");
        
        // Claim pending rewards
        _claimRewards(msg.sender);
        
        // Calculate penalty if early unstake
        uint256 penalty = 0;
        if (block.timestamp < stakeInfo.startTime + stakeInfo.lockDuration) {
            penalty = (amount * earlyUnstakePenalty) / BASIS_POINTS;
        }
        
        uint256 amountAfterPenalty = amount - penalty;
        
        stakeInfo.amount -= amount;
        totalStaked -= amount;
        
        // Transfer penalty to reward pool
        if (penalty > 0) {
            rewardPool += penalty;
        }
        
        // Transfer tokens back
        require(stakingToken.transfer(msg.sender, amountAfterPenalty), "Transfer failed");
        
        emit Unstaked(msg.sender, amount, penalty);
    }
    
    /**
     * @notice Claim accumulated staking rewards
     */
    function claimRewards() external nonReentrant {
        _claimRewards(msg.sender);
    }
    
    // ==================== Internal Functions ====================
    
    function _claimRewards(address user) internal {
        StakeInfo storage stakeInfo = stakes[user];
        if (stakeInfo.amount == 0) return;
        
        uint256 pending = _calculatePendingRewards(user);
        if (pending == 0) return;
        
        stakeInfo.lastClaimTime = block.timestamp;
        stakeInfo.accumulatedRewards += pending;
        
        if (rewardPool >= pending) {
            rewardPool -= pending;
            require(stakingToken.transfer(user, pending), "Transfer failed");
            emit RewardsClaimed(user, pending);
        }
    }
    
    function _calculatePendingRewards(address user) internal view returns (uint256) {
        StakeInfo storage stakeInfo = stakes[user];
        if (stakeInfo.amount == 0) return 0;
        
        uint256 timeElapsed = block.timestamp - stakeInfo.lastClaimTime;
        uint256 baseReward = (stakeInfo.amount * rewardRatePerSecond * timeElapsed) / 1e18;
        uint256 multipliedReward = (baseReward * stakeInfo.rewardMultiplier) / BASIS_POINTS;
        
        return multipliedReward;
    }
    
    function _calculateTier(uint256 amount, uint256 lockDays) internal view returns (uint256, uint256) {
        uint256 bestTier = 0;
        uint256 bestMultiplier = BASIS_POINTS;
        
        for (uint256 i = 0; i < tierCount; i++) {
            StakingTier storage tier = tiers[i];
            if (amount >= tier.minAmount && lockDays >= tier.minLockDays) {
                if (tier.multiplier > bestMultiplier) {
                    bestTier = i;
                    bestMultiplier = tier.multiplier;
                }
            }
        }
        
        return (bestTier, bestMultiplier);
    }
    
    function _addTier(
        uint256 minAmount,
        uint256 multiplier,
        uint256 minLockDays,
        string memory name
    ) internal {
        tiers[tierCount] = StakingTier({
            minAmount: minAmount,
            multiplier: multiplier,
            minLockDays: minLockDays,
            name: name
        });
        emit TierAdded(tierCount, name, minAmount, multiplier);
        tierCount++;
    }
    
    // ==================== View Functions ====================
    
    function getStakeInfo(address user) external view returns (
        uint256 amount,
        uint256 startTime,
        uint256 lockDuration,
        uint256 multiplier,
        uint256 pendingRewards,
        bool canUnstakeWithoutPenalty
    ) {
        StakeInfo storage stakeInfo = stakes[user];
        return (
            stakeInfo.amount,
            stakeInfo.startTime,
            stakeInfo.lockDuration,
            stakeInfo.rewardMultiplier,
            _calculatePendingRewards(user),
            block.timestamp >= stakeInfo.startTime + stakeInfo.lockDuration
        );
    }
    
    function getVotingPower(address user) external view returns (uint256) {
        StakeInfo storage stakeInfo = stakes[user];
        return (stakeInfo.amount * stakeInfo.rewardMultiplier) / BASIS_POINTS;
    }
    
    function getTier(uint256 tierId) external view returns (
        uint256 minAmount,
        uint256 multiplier,
        uint256 minLockDays,
        string memory name
    ) {
        StakingTier storage tier = tiers[tierId];
        return (tier.minAmount, tier.multiplier, tier.minLockDays, tier.name);
    }
    
    // ==================== Admin Functions ====================
    
    function fundRewardPool(uint256 amount) external {
        require(stakingToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        rewardPool += amount;
        emit RewardPoolFunded(amount);
    }
    
    function updateRewardRate(uint256 newRate) external onlyOwner {
        rewardRatePerSecond = newRate;
    }
    
    function updatePenalty(uint256 newPenalty) external onlyOwner {
        require(newPenalty <= 5000, "Max 50% penalty");
        earlyUnstakePenalty = newPenalty;
    }
    
    function addTier(
        uint256 minAmount,
        uint256 multiplier,
        uint256 minLockDays,
        string memory name
    ) external onlyOwner {
        _addTier(minAmount, multiplier, minLockDays, name);
    }
}
