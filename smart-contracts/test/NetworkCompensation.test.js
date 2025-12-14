const { expect } = require("chai");
const hre = require("hardhat");
const { ethers } = hre;

describe("NetworkCompensation", function () {
  let networkCompensation;
  let owner;
  let oracle;
  let user1;
  let user2;
  let addrs;

  const REWARD_RATE = ethers.utils.parseEther("0.000001"); // 0.000001 ETH per byte
  const DEVICE_ID = "ESP32_001";
  const BYTES_TRANSMITTED = 1000;
  const QUALITY_SCORE = 85;

  beforeEach(async function () {
    [owner, oracle, user1, user2, ...addrs] = await ethers.getSigners();

    const NetworkCompensation = await ethers.getContractFactory("NetworkCompensation");
    networkCompensation = await NetworkCompensation.deploy(
      oracle.address,
      REWARD_RATE
    );
    await networkCompensation.deployed();
  });

  describe("Deployment", function () {
    it("Should set the right oracle", async function () {
      expect(await networkCompensation.oracle()).to.equal(oracle.address);
    });

    it("Should set the correct reward rate", async function () {
      expect(await networkCompensation.rewardRate()).to.equal(REWARD_RATE);
    });

    it("Should set the right owner", async function () {
      expect(await networkCompensation.owner()).to.equal(owner.address);
    });
  });

  describe("Device Registration", function () {
    it("Should register a device successfully", async function () {
      await expect(
        networkCompensation.connect(user1).registerDevice(DEVICE_ID, user1.address)
      )
        .to.emit(networkCompensation, "DeviceRegistered")
        .withArgs(DEVICE_ID, user1.address);

      const device = await networkCompensation.devices(DEVICE_ID);
      expect(device.owner).to.equal(user1.address);
      expect(device.isActive).to.be.true;
    });

    it("Should fail to register device with empty ID", async function () {
      await expect(
        networkCompensation.connect(user1).registerDevice("", user1.address)
      ).to.be.revertedWith("Device ID cannot be empty");
    });

    it("Should fail to register device twice", async function () {
      await networkCompensation.connect(user1).registerDevice(DEVICE_ID, user1.address);
      
      await expect(
        networkCompensation.connect(user1).registerDevice(DEVICE_ID, user1.address)
      ).to.be.revertedWith("Device already registered");
    });
  });

  describe("Reward Distribution", function () {
    beforeEach(async function () {
      // Register device first
      await networkCompensation.connect(user1).registerDevice(DEVICE_ID, user1.address);
      
      // Fund the contract
      await owner.sendTransaction({
        to: networkCompensation.address,
        value: ethers.utils.parseEther("10.0")
      });
    });

    it("Should distribute rewards correctly", async function () {
      const initialBalance = await networkCompensation.getUserEarnings(user1.address);
      
      await expect(
        networkCompensation.connect(oracle).distributeReward(
          DEVICE_ID,
          BYTES_TRANSMITTED,
          QUALITY_SCORE
        )
      )
        .to.emit(networkCompensation, "RewardDistributed")
        .withArgs(DEVICE_ID, user1.address, BYTES_TRANSMITTED, QUALITY_SCORE);

      const finalBalance = await networkCompensation.getUserEarnings(user1.address);
      
      // Calculate expected reward: base * qualityMultiplier
      const baseReward = REWARD_RATE.mul(BYTES_TRANSMITTED);
      const qualityMultiplier = QUALITY_SCORE + 15; // 85 + 15 = 100%
      const expectedReward = baseReward.mul(qualityMultiplier).div(100);
      
      expect(finalBalance.sub(initialBalance)).to.equal(expectedReward);
    });

    it("Should only allow oracle to distribute rewards", async function () {
      await expect(
        networkCompensation.connect(user1).distributeReward(
          DEVICE_ID,
          BYTES_TRANSMITTED,
          QUALITY_SCORE
        )
      ).to.be.revertedWith("Only oracle can call this function");
    });

    it("Should handle quality scores correctly", async function () {
      const lowQuality = 50;
      const highQuality = 95;
      
      // Test low quality
      await networkCompensation.connect(oracle).distributeReward(
        DEVICE_ID,
        BYTES_TRANSMITTED,
        lowQuality
      );
      
      const lowQualityReward = await networkCompensation.getUserEarnings(user1.address);
      
      // Reset earnings for comparison
      await networkCompensation.connect(user1).withdraw(lowQualityReward);
      
      // Test high quality
      await networkCompensation.connect(oracle).distributeReward(
        DEVICE_ID,
        BYTES_TRANSMITTED,
        highQuality
      );
      
      const highQualityReward = await networkCompensation.getUserEarnings(user1.address);
      
      expect(highQualityReward).to.be.gt(0);
    });
  });

  describe("Withdrawals", function () {
    beforeEach(async function () {
      await networkCompensation.connect(user1).registerDevice(DEVICE_ID, user1.address);
      
      await owner.sendTransaction({
        to: networkCompensation.address,
        value: ethers.utils.parseEther("10.0")
      });
      
      await networkCompensation.connect(oracle).distributeReward(
        DEVICE_ID,
        BYTES_TRANSMITTED,
        QUALITY_SCORE
      );
    });

    it("Should allow users to withdraw their earnings", async function () {
      const earnings = await networkCompensation.getUserEarnings(user1.address);
      const initialBalance = await user1.getBalance();
      
      const tx = await networkCompensation.connect(user1).withdraw(earnings);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed.mul(receipt.effectiveGasPrice);
      
      const finalBalance = await user1.getBalance();
      const expectedBalance = initialBalance.add(earnings).sub(gasUsed);
      
      expect(finalBalance).to.be.closeTo(expectedBalance, ethers.utils.parseEther("0.001"));
      expect(await networkCompensation.getUserEarnings(user1.address)).to.equal(0);
    });

    it("Should fail to withdraw more than earnings", async function () {
      const earnings = await networkCompensation.getUserEarnings(user1.address);
      
      await expect(
        networkCompensation.connect(user1).withdraw(earnings.add(1))
      ).to.be.revertedWith("Insufficient earnings");
    });

    it("Should fail to withdraw zero amount", async function () {
      await expect(
        networkCompensation.connect(user1).withdraw(0)
      ).to.be.revertedWith("Amount must be greater than 0");
    });
  });

  describe("Contract Management", function () {
    it("Should allow owner to update oracle", async function () {
      const newOracle = user2.address;
      
      await expect(
        networkCompensation.connect(owner).updateOracle(newOracle)
      )
        .to.emit(networkCompensation, "OracleUpdated")
        .withArgs(oracle.address, newOracle);
      
      expect(await networkCompensation.oracle()).to.equal(newOracle);
    });

    it("Should allow owner to update reward rate", async function () {
      const newRewardRate = ethers.utils.parseEther("0.000002");
      
      await networkCompensation.connect(owner).updateRewardRate(newRewardRate);
      expect(await networkCompensation.rewardRate()).to.equal(newRewardRate);
    });

    it("Should allow owner to pause and unpause", async function () {
      await networkCompensation.connect(owner).pause();
      expect(await networkCompensation.paused()).to.be.true;
      
      await networkCompensation.connect(owner).unpause();
      expect(await networkCompensation.paused()).to.be.false;
    });

    it("Should prevent non-owners from administrative functions", async function () {
      await expect(
        networkCompensation.connect(user1).updateOracle(user2.address)
      ).to.be.revertedWith("Ownable: caller is not the owner");
      
      await expect(
        networkCompensation.connect(user1).pause()
      ).to.be.revertedWith("Ownable: caller is not the owner");
    });
  });
});
