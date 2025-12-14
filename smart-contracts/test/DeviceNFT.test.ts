import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("DeviceNFT", function () {
    let deviceNFT: any;
    let owner: SignerWithAddress;
    let user1: SignerWithAddress;
    let user2: SignerWithAddress;

    const BASE_URI = "https://api.iot-network.io/nft/";

    beforeEach(async function () {
        [owner, user1, user2] = await ethers.getSigners();

        const DeviceNFT = await ethers.getContractFactory("DeviceNFT");
        deviceNFT = await DeviceNFT.deploy(BASE_URI);
        await deviceNFT.waitForDeployment();
    });

    describe("Minting", function () {
        it("should mint a new device NFT", async function () {
            await deviceNFT.mintDevice(
                user1.address,
                "ESP32_ABC123",
                "ESP32",
                `${BASE_URI}metadata/ESP32_ABC123.json`
            );

            const owner = await deviceNFT.ownerOf(1);
            expect(owner).to.equal(user1.address);
        });

        it("should store device metadata", async function () {
            await deviceNFT.mintDevice(
                user1.address,
                "ESP32_ABC123",
                "ESP32",
                `${BASE_URI}metadata/ESP32_ABC123.json`
            );

            const metadata = await deviceNFT.getDeviceMetadata(1);
            expect(metadata.deviceId).to.equal("ESP32_ABC123");
            expect(metadata.deviceType).to.equal("ESP32");
            expect(metadata.isActive).to.be.true;
        });

        it("should emit DeviceMinted event", async function () {
            await expect(
                deviceNFT.mintDevice(
                    user1.address,
                    "ESP32_ABC123",
                    "ESP32",
                    `${BASE_URI}metadata/ESP32_ABC123.json`
                )
            ).to.emit(deviceNFT, "DeviceMinted");
        });

        it("should reject duplicate device IDs", async function () {
            await deviceNFT.mintDevice(
                user1.address,
                "ESP32_ABC123",
                "ESP32",
                `${BASE_URI}metadata/ESP32_ABC123.json`
            );

            await expect(
                deviceNFT.mintDevice(
                    user2.address,
                    "ESP32_ABC123",
                    "ESP32",
                    `${BASE_URI}metadata/ESP32_ABC123.json`
                )
            ).to.be.revertedWith("Device already registered");
        });

        it("should increment total devices", async function () {
            await deviceNFT.mintDevice(user1.address, "device_1", "ESP32", "uri1");
            await deviceNFT.mintDevice(user2.address, "device_2", "RaspberryPi", "uri2");

            const total = await deviceNFT.totalDevices();
            expect(total).to.equal(2);
        });
    });

    describe("Device Lookup", function () {
        beforeEach(async function () {
            await deviceNFT.mintDevice(user1.address, "ESP32_001", "ESP32", "uri1");
            await deviceNFT.mintDevice(user1.address, "ESP32_002", "ESP32", "uri2");
            await deviceNFT.mintDevice(user2.address, "PI_001", "RaspberryPi", "uri3");
        });

        it("should get device by device ID", async function () {
            const result = await deviceNFT.getDeviceByDeviceId("ESP32_001");
            expect(result.tokenId).to.equal(1);
        });

        it("should get owner devices", async function () {
            const devices = await deviceNFT.getOwnerDevices(user1.address);
            expect(devices.length).to.equal(2);
            expect(devices[0]).to.equal(1);
            expect(devices[1]).to.equal(2);
        });

        it("should return empty array for non-owner", async function () {
            const [, , , nonOwner] = await ethers.getSigners();
            const devices = await deviceNFT.getOwnerDevices(nonOwner.address);
            expect(devices.length).to.equal(0);
        });
    });

    describe("Stats Update", function () {
        beforeEach(async function () {
            await deviceNFT.mintDevice(user1.address, "ESP32_001", "ESP32", "uri1");
            await deviceNFT.setNetworkContract(owner.address);
        });

        it("should update device stats", async function () {
            await deviceNFT.updateDeviceStats(
                "ESP32_001",
                ethers.parseEther("100"), // rewards
                1000000000, // 1GB
                95 // quality
            );

            const metadata = await deviceNFT.getDeviceMetadata(1);
            expect(metadata.totalRewardsEarned).to.equal(ethers.parseEther("100"));
            expect(metadata.qualityScore).to.equal(95);
        });

        it("should accumulate rewards", async function () {
            await deviceNFT.updateDeviceStats("ESP32_001", ethers.parseEther("50"), 500000000, 90);
            await deviceNFT.updateDeviceStats("ESP32_001", ethers.parseEther("30"), 300000000, 92);

            const metadata = await deviceNFT.getDeviceMetadata(1);
            expect(metadata.totalRewardsEarned).to.equal(ethers.parseEther("80"));
        });

        it("should emit DeviceUpdated event", async function () {
            await expect(
                deviceNFT.updateDeviceStats("ESP32_001", ethers.parseEther("100"), 1000000000, 95)
            ).to.emit(deviceNFT, "DeviceUpdated");
        });

        it("should reject unauthorized updates", async function () {
            await expect(
                deviceNFT.connect(user2).updateDeviceStats("ESP32_001", 100, 1000, 90)
            ).to.be.revertedWith("Not authorized");
        });
    });

    describe("Deactivation", function () {
        beforeEach(async function () {
            await deviceNFT.mintDevice(user1.address, "ESP32_001", "ESP32", "uri1");
        });

        it("should allow owner to deactivate", async function () {
            await deviceNFT.connect(user1).deactivateDevice("ESP32_001");

            const metadata = await deviceNFT.getDeviceMetadata(1);
            expect(metadata.isActive).to.be.false;
        });

        it("should emit DeviceDeactivated event", async function () {
            await expect(
                deviceNFT.connect(user1).deactivateDevice("ESP32_001")
            ).to.emit(deviceNFT, "DeviceDeactivated");
        });

        it("should reject non-owner deactivation", async function () {
            await expect(
                deviceNFT.connect(user2).deactivateDevice("ESP32_001")
            ).to.be.revertedWith("Not owner");
        });
    });

    describe("Token URI", function () {
        it("should return correct token URI", async function () {
            const tokenURI = `${BASE_URI}metadata/ESP32_001.json`;
            await deviceNFT.mintDevice(user1.address, "ESP32_001", "ESP32", tokenURI);

            const uri = await deviceNFT.tokenURI(1);
            expect(uri).to.equal(tokenURI);
        });

        it("should allow updating base URI", async function () {
            await deviceNFT.setBaseURI("https://new-api.example.com/");
            // Verify new mints use new base
        });
    });

    describe("ERC721 Standard", function () {
        beforeEach(async function () {
            await deviceNFT.mintDevice(user1.address, "ESP32_001", "ESP32", "uri1");
        });

        it("should support ERC721 interface", async function () {
            const supportsERC721 = await deviceNFT.supportsInterface("0x80ac58cd");
            expect(supportsERC721).to.be.true;
        });

        it("should allow transfers", async function () {
            await deviceNFT.connect(user1).transferFrom(user1.address, user2.address, 1);

            const newOwner = await deviceNFT.ownerOf(1);
            expect(newOwner).to.equal(user2.address);
        });

        it("should allow approvals", async function () {
            await deviceNFT.connect(user1).approve(user2.address, 1);

            const approved = await deviceNFT.getApproved(1);
            expect(approved).to.equal(user2.address);
        });
    });
});
