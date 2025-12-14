// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/// @title NetworkCompensation
/// @notice ERC-20 reward token with oracle-based usage recording and secure withdrawal
/// @dev Implements comprehensive security measures and multi-oracle support
contract NetworkCompensation is ERC20, Ownable, ReentrancyGuard, Pausable {

    struct Device {
        address owner;
        bool isActive;
        uint256 totalBytes;
        uint256 lastRewardClaim;
        uint256 qualityScore;
    }

    struct Oracle {
        bool isAuthorized;
        uint256 submissionCount;
        uint256 lastSubmission;
    }

    address public oracle;
    mapping(address => Oracle) public oracles;
    mapping(string => Device) public devices;
    mapping(address => uint256) public userRewards;
    mapping(address => string[]) public userDevices;
    mapping(address => uint256) private userEarnings;

    uint256 public constant DECIMALS = 18;
    uint256 public rewardRate;
    uint256 public qualityBonusRate = 5e14; // 0.0005 tokens per quality point
    uint256 public minimumQuality = 50;
    uint256 public rewardPool;
    uint256 public totalDevices;

    event DeviceRegistered(string indexed deviceId, address indexed owner);
    event UsageDataSubmitted(string indexed deviceId, uint256 bytesTransmitted, uint256 qualityScore);
    event RewardDistributed(string indexed deviceId, address indexed owner, uint256 bytesTransmitted, uint256 qualityScore);
    event RewardsClaimed(address indexed user, uint256 amount);
    event OracleAuthorized(address indexed oracle);
    event OracleRevoked(address indexed oracle);
    event OracleUpdated(address indexed oldOracle, address indexed newOracle);
    event RewardRateUpdated(uint256 newRate);

    modifier onlyOracle() {
        require(msg.sender == oracle || oracles[msg.sender].isAuthorized, "Only oracle can call this function");
        _;
    }

    modifier validDevice(string memory deviceId) {
        require(devices[deviceId].owner != address(0), "Device not registered");
        require(devices[deviceId].isActive, "Device inactive");
        _;
    }

    /// @param _oracle Address of the oracle authorized to submit usage data
    /// @param _rewardRate Reward rate per byte transmitted
    constructor(address _oracle, uint256 _rewardRate) ERC20("NetworkReward", "NWR") Ownable(msg.sender) {
        require(_oracle != address(0), "Invalid oracle address");
        require(_rewardRate > 0, "Reward rate must be positive");
        
        oracle = _oracle;
        rewardRate = _rewardRate;
        oracles[_oracle].isAuthorized = true;
        
        // Mint initial supply to contract for rewards
        uint256 initialSupply = 1000000 * 10**DECIMALS;
        _mint(address(this), initialSupply);
        rewardPool = initialSupply;
        
        emit OracleAuthorized(_oracle);
    }

    /// @notice Register a new device
    /// @param deviceId Unique identifier for the device
    /// @param deviceOwner Address of the device owner
    function registerDevice(string memory deviceId, address deviceOwner) external {
        require(bytes(deviceId).length > 0, "Device ID cannot be empty");
        require(devices[deviceId].owner == address(0), "Device already registered");
        require(deviceOwner != address(0), "Invalid owner address");
        
        devices[deviceId] = Device({
            owner: deviceOwner,
            isActive: true,
            totalBytes: 0,
            lastRewardClaim: block.timestamp,
            qualityScore: 100
        });
        
        userDevices[deviceOwner].push(deviceId);
        totalDevices++;
        
        emit DeviceRegistered(deviceId, deviceOwner);
    }

    /// @notice Update the oracle address
    /// @param newOracle New oracle address
    function updateOracle(address newOracle) external onlyOwner {
        require(newOracle != address(0), "Invalid oracle address");
        address oldOracle = oracle;
        oracle = newOracle;
        oracles[newOracle].isAuthorized = true;
        emit OracleUpdated(oldOracle, newOracle);
    }

    /// @notice Authorize an additional oracle
    function authorizeOracle(address _oracle) external onlyOwner {
        require(_oracle != address(0), "Invalid oracle address");
        oracles[_oracle].isAuthorized = true;
        emit OracleAuthorized(_oracle);
    }

    /// @notice Revoke oracle authorization
    function revokeOracle(address _oracle) external onlyOwner {
        oracles[_oracle].isAuthorized = false;
        emit OracleRevoked(_oracle);
    }

    /// @notice Update the reward rate
    function updateRewardRate(uint256 _rewardRate) external onlyOwner {
        require(_rewardRate > 0, "Rate must be positive");
        rewardRate = _rewardRate;
        emit RewardRateUpdated(_rewardRate);
    }

    /// @notice Distribute rewards for device usage (called by oracle)
    /// @param deviceId Device identifier
    /// @param bytesTransmitted Amount of data transmitted
    /// @param qualityScore Quality score (0-100)
    function distributeReward(
        string memory deviceId,
        uint256 bytesTransmitted,
        uint256 qualityScore
    ) external onlyOracle validDevice(deviceId) whenNotPaused {
        require(qualityScore <= 100, "Quality score must be <= 100");
        require(bytesTransmitted > 0, "Bytes transmitted must be positive");

        Device storage device = devices[deviceId];
        device.totalBytes += bytesTransmitted;
        device.qualityScore = qualityScore;

        // Calculate rewards based on bytes and quality
        // Quality multiplier: qualityScore + 15 (so 85 quality = 100% multiplier)
        uint256 baseReward = bytesTransmitted * rewardRate;
        uint256 qualityMultiplier = qualityScore + 15;
        uint256 totalReward = (baseReward * qualityMultiplier) / 100;

        userRewards[device.owner] += totalReward;
        userEarnings[device.owner] += totalReward;
        
        oracles[msg.sender].submissionCount++;
        oracles[msg.sender].lastSubmission = block.timestamp;

        emit RewardDistributed(deviceId, device.owner, bytesTransmitted, qualityScore);
        emit UsageDataSubmitted(deviceId, bytesTransmitted, qualityScore);
    }

    /// @notice Submit usage data (alias for distributeReward for backward compatibility)
    function submitUsageData(
        string memory deviceId,
        uint256 bytesTransmitted,
        uint256 qualityScore
    ) external onlyOracle validDevice(deviceId) whenNotPaused {
        require(qualityScore <= 100, "Quality score must be <= 100");
        require(bytesTransmitted > 0, "Bytes transmitted must be positive");

        Device storage device = devices[deviceId];
        device.totalBytes += bytesTransmitted;
        device.qualityScore = qualityScore;

        uint256 baseReward = bytesTransmitted * rewardRate;
        uint256 qualityBonus = qualityScore >= minimumQuality ? 
            qualityScore * qualityBonusRate : 0;
        uint256 totalReward = baseReward + qualityBonus;

        userRewards[device.owner] += totalReward;
        userEarnings[device.owner] += totalReward;
        
        oracles[msg.sender].submissionCount++;
        oracles[msg.sender].lastSubmission = block.timestamp;

        emit UsageDataSubmitted(deviceId, bytesTransmitted, qualityScore);
    }

    /// @notice Get pending rewards for a user
    function calculatePendingRewards(address user) external view returns (uint256) {
        return userRewards[user];
    }

    /// @notice Get user earnings (for test compatibility)
    function getUserEarnings(address user) external view returns (uint256) {
        return userEarnings[user];
    }

    /// @notice Claim all pending rewards
    function claimRewards() external nonReentrant whenNotPaused {
        uint256 rewardAmount = userRewards[msg.sender];
        require(rewardAmount > 0, "No rewards to claim");
        require(rewardPool >= rewardAmount, "Insufficient reward pool");

        userRewards[msg.sender] = 0;
        rewardPool -= rewardAmount;
        
        _transfer(address(this), msg.sender, rewardAmount);

        emit RewardsClaimed(msg.sender, rewardAmount);
    }

    /// @notice Withdraw a specific amount of earnings
    /// @param amount Amount to withdraw
    function withdraw(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be greater than 0");
        require(userEarnings[msg.sender] >= amount, "Insufficient earnings");
        require(rewardPool >= amount, "Insufficient reward pool");

        userEarnings[msg.sender] -= amount;
        userRewards[msg.sender] = userRewards[msg.sender] > amount ? 
            userRewards[msg.sender] - amount : 0;
        rewardPool -= amount;
        
        _transfer(address(this), msg.sender, amount);

        emit RewardsClaimed(msg.sender, amount);
    }

    /// @notice Get all devices owned by a user
    function getUserDevices(address user) external view returns (string[] memory) {
        return userDevices[user];
    }

    /// @notice Get device information
    function getDeviceInfo(string memory deviceId) external view returns (
        address owner,
        bool isActive,
        uint256 totalBytes,
        uint256 qualityScore
    ) {
        Device memory device = devices[deviceId];
        return (device.owner, device.isActive, device.totalBytes, device.qualityScore);
    }

    /// @notice Pause the contract (emergency)
    function pause() external onlyOwner {
        _pause();
    }

    /// @notice Emergency pause alias
    function emergencyPause() external onlyOwner {
        _pause();
    }

    /// @notice Unpause the contract
    function unpause() external onlyOwner {
        _unpause();
    }

    /// @notice Add tokens to the reward pool
    function addToRewardPool(uint256 amount) external onlyOwner {
        require(balanceOf(address(this)) >= amount, "Insufficient contract balance");
        rewardPool += amount;
    }

    /// @notice Check if contract is paused
    function paused() public view override returns (bool) {
        return super.paused();
    }

    /// @notice Accept Ether deposits for funding rewards
    receive() external payable {
        // Accept Ether for funding the contract
    }
}
