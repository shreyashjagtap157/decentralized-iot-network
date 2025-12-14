import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("NetworkStaking", function () {
    let staking: any;
    let token: any;
    let owner: SignerWithAddress;
    let staker1: SignerWithAddress;
    let staker2: SignerWithAddress;

    beforeEach(async function () {
        [owner, staker1, staker2] = await ethers.getSigners();

        // Deploy mock token
        const Token = await ethers.getContractFactory("NetworkCompensation");
        token = await Token.deploy(owner.address, 1000000000000n);
        await token.waitForDeployment();

        // Deploy staking
        const Staking = await ethers.getContractFactory("NetworkStaking");
        staking = await Staking.deploy(await token.getAddress());
        await staking.waitForDeployment();

        // Fund staking contract reward pool
        await token.transfer(await staking.getAddress(), ethers.parseEther("1000000"));
        await staking.fundRewardPool(ethers.parseEther("100000"));

        // Give stakers tokens
        await token.transfer(staker1.address, ethers.parseEther("100000"));
        await token.transfer(staker2.address, ethers.parseEther("500000"));

        // Approve staking contract
        await token.connect(staker1).approve(await staking.getAddress(), ethers.MaxUint256);
        await token.connect(staker2).approve(await staking.getAddress(), ethers.MaxUint256);
    });

    describe("Staking", function () {
        it("should allow staking tokens", async function () {
            await staking.connect(staker1).stake(ethers.parseEther("10000"), 30);

            const info = await staking.getStakeInfo(staker1.address);
            expect(info.amount).to.equal(ethers.parseEther("10000"));
        });

        it("should reject staking 0 tokens", async function () {
            await expect(
                staking.connect(staker1).stake(0, 30)
            ).to.be.revertedWith("Cannot stake 0");
        });

        it("should reject staking with lock less than 7 days", async function () {
            await expect(
                staking.connect(staker1).stake(ethers.parseEther("1000"), 5)
            ).to.be.revertedWith("Minimum 7 days lock");
        });

        it("should emit Staked event", async function () {
            await expect(
                staking.connect(staker1).stake(ethers.parseEther("10000"), 30)
            ).to.emit(staking, "Staked");
        });

        it("should update total staked", async function () {
            await staking.connect(staker1).stake(ethers.parseEther("10000"), 30);
            await staking.connect(staker2).stake(ethers.parseEther("50000"), 90);

            const totalStaked = await staking.totalStaked();
            expect(totalStaked).to.equal(ethers.parseEther("60000"));
        });
    });

    describe("Tiers", function () {
        it("should assign Bronze tier for minimum stake", async function () {
            await staking.connect(staker1).stake(ethers.parseEther("1000"), 7);

            const info = await staking.getStakeInfo(staker1.address);
            expect(info.multiplier).to.equal(10000n); // 1x = 10000 basis points
        });

        it("should assign Silver tier for qualifying stake", async function () {
            await staking.connect(staker1).stake(ethers.parseEther("10000"), 30);

            const info = await staking.getStakeInfo(staker1.address);
            expect(info.multiplier).to.equal(12500n); // 1.25x
        });

        it("should assign Gold tier for larger stake", async function () {
            await staking.connect(staker1).stake(ethers.parseEther("50000"), 90);

            const info = await staking.getStakeInfo(staker1.address);
            expect(info.multiplier).to.equal(15000n); // 1.5x
        });

        it("should return all tiers", async function () {
            const tierCount = await staking.tierCount();
            expect(tierCount).to.equal(5);

            const tier0 = await staking.getTier(0);
            expect(tier0.name).to.equal("Bronze");

            const tier4 = await staking.getTier(4);
            expect(tier4.name).to.equal("Diamond");
        });
    });

    describe("Unstaking", function () {
        beforeEach(async function () {
            await staking.connect(staker1).stake(ethers.parseEther("10000"), 30);
        });

        it("should apply penalty for early unstake", async function () {
            const balanceBefore = await token.balanceOf(staker1.address);

            await staking.connect(staker1).unstake(ethers.parseEther("10000"));

            const balanceAfter = await token.balanceOf(staker1.address);
            const received = balanceAfter - balanceBefore;

            // Should receive 90% (10% penalty)
            expect(received).to.equal(ethers.parseEther("9000"));
        });

        it("should not apply penalty after lock period", async function () {
            // Fast forward 30 days
            await ethers.provider.send("evm_increaseTime", [30 * 24 * 60 * 60 + 1]);
            await ethers.provider.send("evm_mine", []);

            const balanceBefore = await token.balanceOf(staker1.address);

            await staking.connect(staker1).unstake(ethers.parseEther("10000"));

            const balanceAfter = await token.balanceOf(staker1.address);
            const received = balanceAfter - balanceBefore;

            // Should receive 100%
            expect(received).to.equal(ethers.parseEther("10000"));
        });

        it("should emit Unstaked event", async function () {
            await expect(
                staking.connect(staker1).unstake(ethers.parseEther("10000"))
            ).to.emit(staking, "Unstaked");
        });

        it("should reject unstaking more than staked", async function () {
            await expect(
                staking.connect(staker1).unstake(ethers.parseEther("20000"))
            ).to.be.revertedWith("Insufficient stake");
        });
    });

    describe("Rewards", function () {
        beforeEach(async function () {
            await staking.connect(staker1).stake(ethers.parseEther("10000"), 30);
        });

        it("should accumulate rewards over time", async function () {
            // Fast forward 1 day
            await ethers.provider.send("evm_increaseTime", [86400]);
            await ethers.provider.send("evm_mine", []);

            const info = await staking.getStakeInfo(staker1.address);
            expect(info.pendingRewards).to.be.gt(0);
        });

        it("should allow claiming rewards", async function () {
            // Fast forward 7 days
            await ethers.provider.send("evm_increaseTime", [7 * 86400]);
            await ethers.provider.send("evm_mine", []);

            const balanceBefore = await token.balanceOf(staker1.address);

            await staking.connect(staker1).claimRewards();

            const balanceAfter = await token.balanceOf(staker1.address);
            expect(balanceAfter).to.be.gt(balanceBefore);
        });

        it("should emit RewardsClaimed event", async function () {
            await ethers.provider.send("evm_increaseTime", [86400]);
            await ethers.provider.send("evm_mine", []);

            await expect(
                staking.connect(staker1).claimRewards()
            ).to.emit(staking, "RewardsClaimed");
        });
    });

    describe("Voting Power", function () {
        it("should calculate voting power based on stake and multiplier", async function () {
            await staking.connect(staker1).stake(ethers.parseEther("10000"), 30);

            const votingPower = await staking.getVotingPower(staker1.address);
            // 10000 * 1.25 = 12500
            expect(votingPower).to.equal(ethers.parseEther("12500"));
        });

        it("should return 0 for non-stakers", async function () {
            const [, , , nonStaker] = await ethers.getSigners();
            const votingPower = await staking.getVotingPower(nonStaker.address);
            expect(votingPower).to.equal(0);
        });
    });

    describe("Admin Functions", function () {
        it("should allow owner to update reward rate", async function () {
            await staking.connect(owner).updateRewardRate(2000000000000000n);
            // Verify by checking rewards accumulation
        });

        it("should allow owner to update penalty", async function () {
            await staking.connect(owner).updatePenalty(500); // 5%
        });

        it("should reject penalty over 50%", async function () {
            await expect(
                staking.connect(owner).updatePenalty(6000) // 60%
            ).to.be.revertedWith("Max 50% penalty");
        });

        it("should allow adding new tiers", async function () {
            await staking.connect(owner).addTier(
                ethers.parseEther("1000000"),
                40000, // 4x
                730, // 2 years
                "Legendary"
            );

            const tierCount = await staking.tierCount();
            expect(tierCount).to.equal(6);
        });
    });
});
