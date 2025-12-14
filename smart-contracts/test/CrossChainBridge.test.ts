import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("CrossChainBridge", function () {
    let bridge: any;
    let token: any;
    let owner: SignerWithAddress;
    let user: SignerWithAddress;
    let validator1: SignerWithAddress;
    let validator2: SignerWithAddress;

    const CHAIN_ID = 1; // Ethereum
    const DEST_CHAIN = 137; // Polygon

    beforeEach(async function () {
        [owner, user, validator1, validator2] = await ethers.getSigners();

        // Deploy mock token
        const Token = await ethers.getContractFactory("NetworkCompensation");
        token = await Token.deploy(owner.address, 1000000000000n);
        await token.waitForDeployment();

        // Deploy bridge
        const Bridge = await ethers.getContractFactory("CrossChainBridge");
        bridge = await Bridge.deploy(await token.getAddress(), CHAIN_ID);
        await bridge.waitForDeployment();

        // Add validators
        await bridge.addValidator(validator1.address);
        await bridge.addValidator(validator2.address);

        // Fund user and bridge
        await token.transfer(user.address, ethers.parseEther("100000"));
        await token.transfer(await bridge.getAddress(), ethers.parseEther("1000000"));

        // Approve bridge
        await token.connect(user).approve(await bridge.getAddress(), ethers.MaxUint256);
    });

    describe("Bridge Initiation", function () {
        it("should allow bridging to supported chain", async function () {
            const amount = ethers.parseEther("1000");

            await bridge.connect(user).bridge(user.address, amount, DEST_CHAIN);

            // Check tokens were locked
            const bridgeBalance = await token.balanceOf(await bridge.getAddress());
            expect(bridgeBalance).to.be.gte(amount);
        });

        it("should emit BridgeInitiated event", async function () {
            const amount = ethers.parseEther("1000");

            await expect(
                bridge.connect(user).bridge(user.address, amount, DEST_CHAIN)
            ).to.emit(bridge, "BridgeInitiated");
        });

        it("should deduct fee from amount", async function () {
            const amount = ethers.parseEther("1000");
            const fee = await bridge.estimateFee(amount);

            expect(fee).to.equal(ethers.parseEther("5")); // 0.5% of 1000
        });

        it("should reject amount below minimum", async function () {
            const amount = ethers.parseEther("1"); // Below 10 minimum

            await expect(
                bridge.connect(user).bridge(user.address, amount, DEST_CHAIN)
            ).to.be.revertedWith("Below minimum");
        });

        it("should reject unsupported destination chain", async function () {
            const amount = ethers.parseEther("1000");
            const unsupportedChain = 999;

            await expect(
                bridge.connect(user).bridge(user.address, amount, unsupportedChain)
            ).to.be.revertedWith("Chain not supported");
        });

        it("should reject when paused", async function () {
            await bridge.pause();

            await expect(
                bridge.connect(user).bridge(user.address, ethers.parseEther("1000"), DEST_CHAIN)
            ).to.be.reverted;
        });
    });

    describe("Bridge Completion", function () {
        it("should complete bridge with valid signatures", async function () {
            const requestId = ethers.randomBytes(32);
            const amount = ethers.parseEther("995"); // After fee
            const sourceChain = DEST_CHAIN;

            // Create message hash
            const messageHash = ethers.solidityPackedKeccak256(
                ["bytes32", "address", "uint256", "uint256", "uint256"],
                [requestId, user.address, amount, sourceChain, CHAIN_ID]
            );

            // Sign with validators
            const sig1 = await validator1.signMessage(ethers.getBytes(messageHash));
            const sig2 = await validator2.signMessage(ethers.getBytes(messageHash));

            const balanceBefore = await token.balanceOf(user.address);

            await bridge.completeBridge(
                requestId,
                user.address,
                amount,
                sourceChain,
                [sig1, sig2]
            );

            const balanceAfter = await token.balanceOf(user.address);
            expect(balanceAfter - balanceBefore).to.equal(amount);
        });

        it("should reject with insufficient signatures", async function () {
            const requestId = ethers.randomBytes(32);
            const amount = ethers.parseEther("995");
            const sourceChain = DEST_CHAIN;

            const messageHash = ethers.solidityPackedKeccak256(
                ["bytes32", "address", "uint256", "uint256", "uint256"],
                [requestId, user.address, amount, sourceChain, CHAIN_ID]
            );

            const sig1 = await validator1.signMessage(ethers.getBytes(messageHash));

            await expect(
                bridge.completeBridge(
                    requestId,
                    user.address,
                    amount,
                    sourceChain,
                    [sig1] // Only 1 signature
                )
            ).to.be.revertedWith("Insufficient signatures");
        });

        it("should reject duplicate processing", async function () {
            const requestId = ethers.randomBytes(32);
            const amount = ethers.parseEther("995");
            const sourceChain = DEST_CHAIN;

            const messageHash = ethers.solidityPackedKeccak256(
                ["bytes32", "address", "uint256", "uint256", "uint256"],
                [requestId, user.address, amount, sourceChain, CHAIN_ID]
            );

            const sig1 = await validator1.signMessage(ethers.getBytes(messageHash));
            const sig2 = await validator2.signMessage(ethers.getBytes(messageHash));

            await bridge.completeBridge(
                requestId,
                user.address,
                amount,
                sourceChain,
                [sig1, sig2]
            );

            await expect(
                bridge.completeBridge(
                    requestId,
                    user.address,
                    amount,
                    sourceChain,
                    [sig1, sig2]
                )
            ).to.be.revertedWith("Already processed");
        });
    });

    describe("Validator Management", function () {
        it("should allow adding validators", async function () {
            const [, , , , newValidator] = await ethers.getSigners();

            await bridge.addValidator(newValidator.address);

            expect(await bridge.validators(newValidator.address)).to.be.true;
        });

        it("should allow removing validators", async function () {
            await bridge.removeValidator(validator2.address);

            expect(await bridge.validators(validator2.address)).to.be.false;
        });

        it("should not allow removing below required signatures", async function () {
            await bridge.removeValidator(validator2.address);

            await expect(
                bridge.removeValidator(validator1.address)
            ).to.be.revertedWith("Cannot go below required");
        });

        it("should emit events for validator changes", async function () {
            const [, , , , newValidator] = await ethers.getSigners();

            await expect(
                bridge.addValidator(newValidator.address)
            ).to.emit(bridge, "ValidatorAdded");

            await expect(
                bridge.removeValidator(newValidator.address)
            ).to.emit(bridge, "ValidatorRemoved");
        });
    });

    describe("Chain Management", function () {
        it("should return supported chains", async function () {
            const chains = await bridge.getSupportedChains();
            expect(chains.length).to.be.gte(4);
        });

        it("should return chain config", async function () {
            const config = await bridge.getChainConfig(DEST_CHAIN);
            expect(config.enabled).to.be.true;
            expect(config.minAmount).to.be.gt(0);
        });

        it("should allow enabling/disabling chains", async function () {
            await bridge.disableChain(DEST_CHAIN);

            const config = await bridge.getChainConfig(DEST_CHAIN);
            expect(config.enabled).to.be.false;

            await expect(
                bridge.connect(user).bridge(user.address, ethers.parseEther("1000"), DEST_CHAIN)
            ).to.be.revertedWith("Chain not supported");
        });
    });

    describe("Fee Management", function () {
        it("should allow updating fee", async function () {
            await bridge.updateFee(100); // 1%

            const fee = await bridge.estimateFee(ethers.parseEther("1000"));
            expect(fee).to.equal(ethers.parseEther("10")); // 1% of 1000
        });

        it("should reject fee over 5%", async function () {
            await expect(
                bridge.updateFee(600) // 6%
            ).to.be.revertedWith("Max 5% fee");
        });

        it("should allow withdrawing fees", async function () {
            // Bridge some tokens to generate fees
            await bridge.connect(user).bridge(user.address, ethers.parseEther("10000"), DEST_CHAIN);

            const balanceBefore = await token.balanceOf(owner.address);
            await bridge.withdrawFees(owner.address);
            const balanceAfter = await token.balanceOf(owner.address);

            expect(balanceAfter).to.be.gt(balanceBefore);
        });
    });
});
