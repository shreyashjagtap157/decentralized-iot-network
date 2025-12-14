// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title DeviceNFT
 * @notice NFT representation of IoT devices for ownership and rewards
 * @dev Each NFT represents a registered device in the network
 */
contract DeviceNFT is ERC721, ERC721URIStorage, Ownable {
    using Counters for Counters.Counter;
    
    // ==================== Types ====================
    
    struct DeviceMetadata {
        string deviceId;
        string deviceType;
        uint256 registrationDate;
        uint256 totalRewardsEarned;
        uint256 totalDataTransferred;
        uint256 qualityScore;
        bool isActive;
    }
    
    // ==================== State ====================
    
    Counters.Counter private _tokenIdCounter;
    
    mapping(uint256 => DeviceMetadata) public deviceMetadata;
    mapping(string => uint256) public deviceIdToTokenId;
    mapping(address => uint256[]) public ownerDevices;
    
    string public baseTokenURI;
    address public networkContract;
    
    // ==================== Events ====================
    
    event DeviceMinted(uint256 indexed tokenId, string deviceId, address owner);
    event DeviceUpdated(uint256 indexed tokenId, uint256 rewards, uint256 dataTransferred);
    event DeviceDeactivated(uint256 indexed tokenId);
    
    // ==================== Constructor ====================
    
    constructor(string memory _baseURI) ERC721("IoT Device NFT", "IOTDEV") Ownable(msg.sender) {
        baseTokenURI = _baseURI;
    }
    
    // ==================== Minting ====================
    
    /**
     * @notice Mint a new device NFT
     * @param to Owner address
     * @param deviceId Unique device identifier
     * @param deviceType Type of device (e.g., "ESP32", "RaspberryPi")
     * @param tokenURI Metadata URI
     */
    function mintDevice(
        address to,
        string memory deviceId,
        string memory deviceType,
        string memory tokenURI
    ) external returns (uint256) {
        require(deviceIdToTokenId[deviceId] == 0, "Device already registered");
        
        _tokenIdCounter.increment();
        uint256 tokenId = _tokenIdCounter.current();
        
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);
        
        deviceMetadata[tokenId] = DeviceMetadata({
            deviceId: deviceId,
            deviceType: deviceType,
            registrationDate: block.timestamp,
            totalRewardsEarned: 0,
            totalDataTransferred: 0,
            qualityScore: 100,
            isActive: true
        });
        
        deviceIdToTokenId[deviceId] = tokenId;
        ownerDevices[to].push(tokenId);
        
        emit DeviceMinted(tokenId, deviceId, to);
        
        return tokenId;
    }
    
    // ==================== Updates ====================
    
    /**
     * @notice Update device statistics (called by network contract)
     */
    function updateDeviceStats(
        string memory deviceId,
        uint256 rewardsEarned,
        uint256 dataTransferred,
        uint256 qualityScore
    ) external {
        require(msg.sender == networkContract || msg.sender == owner(), "Not authorized");
        
        uint256 tokenId = deviceIdToTokenId[deviceId];
        require(tokenId != 0, "Device not found");
        
        DeviceMetadata storage metadata = deviceMetadata[tokenId];
        metadata.totalRewardsEarned += rewardsEarned;
        metadata.totalDataTransferred += dataTransferred;
        metadata.qualityScore = qualityScore;
        
        emit DeviceUpdated(tokenId, rewardsEarned, dataTransferred);
    }
    
    /**
     * @notice Deactivate a device
     */
    function deactivateDevice(string memory deviceId) external {
        uint256 tokenId = deviceIdToTokenId[deviceId];
        require(tokenId != 0, "Device not found");
        require(ownerOf(tokenId) == msg.sender || msg.sender == owner(), "Not owner");
        
        deviceMetadata[tokenId].isActive = false;
        emit DeviceDeactivated(tokenId);
    }
    
    // ==================== View Functions ====================
    
    function getDeviceMetadata(uint256 tokenId) external view returns (DeviceMetadata memory) {
        return deviceMetadata[tokenId];
    }
    
    function getDeviceByDeviceId(string memory deviceId) external view returns (
        uint256 tokenId,
        DeviceMetadata memory metadata
    ) {
        tokenId = deviceIdToTokenId[deviceId];
        require(tokenId != 0, "Device not found");
        return (tokenId, deviceMetadata[tokenId]);
    }
    
    function getOwnerDevices(address owner) external view returns (uint256[] memory) {
        return ownerDevices[owner];
    }
    
    function totalDevices() external view returns (uint256) {
        return _tokenIdCounter.current();
    }
    
    // ==================== Admin ====================
    
    function setNetworkContract(address _networkContract) external onlyOwner {
        networkContract = _networkContract;
    }
    
    function setBaseURI(string memory _baseURI) external onlyOwner {
        baseTokenURI = _baseURI;
    }
    
    // ==================== Overrides ====================
    
    function _baseURI() internal view override returns (string memory) {
        return baseTokenURI;
    }
    
    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }
    
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
    
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }
}
