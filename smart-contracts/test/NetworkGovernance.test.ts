import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("NetworkGovernance", function () {
    let governance: any;
    let token: any;
    let owner: SignerWithAddress;
    let proposer: SignerWithAddress;
    let voter1: SignerWithAddress;
    let voter2: SignerWithAddress;

    const PROPOSAL_THRESHOLD = ethers.parseEther("10000");
    const QUORUM_VOTES = ethers.parseEther("100000");

    beforeEach(async function () {
        [owner, proposer, voter1, voter2] = await ethers.getSigners();

        // Deploy mock token
        const Token = await ethers.getContractFactory("NetworkCompensation");
        token = await Token.deploy(owner.address, 1000000000000n);
        await token.waitForDeployment();

        // Deploy governance
        const Governance = await ethers.getContractFactory("NetworkGovernance");
        governance = await Governance.deploy(await token.getAddress());
        await governance.waitForDeployment();

        // Distribute tokens
        await token.transfer(proposer.address, ethers.parseEther("50000"));
        await token.transfer(voter1.address, ethers.parseEther("80000"));
        await token.transfer(voter2.address, ethers.parseEther("40000"));
    });

    describe("Proposal Creation", function () {
        it("should allow user with enough tokens to create proposal", async function () {
            const tx = await governance.connect(proposer).propose(
                0, // ProposalType.ParameterChange
                "Increase Reward Rate",
                "Proposal to increase the base reward rate by 10%",
                ethers.ZeroAddress,
                "0x",
                0
            );

            const receipt = await tx.wait();
            expect(receipt.status).to.equal(1);

            const proposalCount = await governance.proposalCount();
            expect(proposalCount).to.equal(1);
        });

        it("should reject proposal from user with insufficient tokens", async function () {
            const [, , , , poorUser] = await ethers.getSigners();

            await expect(
                governance.connect(poorUser).propose(
                    0,
                    "Test Proposal",
                    "Description",
                    ethers.ZeroAddress,
                    "0x",
                    0
                )
            ).to.be.revertedWith("Below proposal threshold");
        });

        it("should emit ProposalCreated event", async function () {
            await expect(
                governance.connect(proposer).propose(
                    0,
                    "Test Proposal",
                    "Description",
                    ethers.ZeroAddress,
                    "0x",
                    0
                )
            ).to.emit(governance, "ProposalCreated");
        });
    });

    describe("Voting", function () {
        let proposalId: bigint;

        beforeEach(async function () {
            await governance.connect(proposer).propose(
                0,
                "Test Proposal",
                "Description",
                ethers.ZeroAddress,
                "0x",
                0
            );
            proposalId = 1n;

            // Fast forward past voting delay
            await ethers.provider.send("evm_increaseTime", [86400 + 1]); // 1 day + 1 second
            await ethers.provider.send("evm_mine", []);
        });

        it("should allow voting on active proposal", async function () {
            await governance.connect(voter1).castVote(proposalId, 1); // Vote FOR

            const receipt = await governance.getReceipt(proposalId, voter1.address);
            expect(receipt.hasVoted).to.equal(true);
            expect(receipt.support).to.equal(1);
        });

        it("should not allow double voting", async function () {
            await governance.connect(voter1).castVote(proposalId, 1);

            await expect(
                governance.connect(voter1).castVote(proposalId, 1)
            ).to.be.revertedWith("Already voted");
        });

        it("should correctly tally votes", async function () {
            await governance.connect(voter1).castVote(proposalId, 1); // FOR
            await governance.connect(voter2).castVote(proposalId, 0); // AGAINST

            const info = await governance.getProposalInfo(proposalId);
            expect(info.forVotes).to.equal(ethers.parseEther("80000"));
            expect(info.againstVotes).to.equal(ethers.parseEther("40000"));
        });

        it("should emit VoteCast event", async function () {
            await expect(
                governance.connect(voter1).castVote(proposalId, 1)
            ).to.emit(governance, "VoteCast");
        });
    });

    describe("Proposal States", function () {
        let proposalId: bigint;

        beforeEach(async function () {
            await governance.connect(proposer).propose(
                0,
                "Test Proposal",
                "Description",
                ethers.ZeroAddress,
                "0x",
                0
            );
            proposalId = 1n;
        });

        it("should be Pending before voting delay", async function () {
            const state = await governance.state(proposalId);
            expect(state).to.equal(0); // Pending
        });

        it("should be Active during voting period", async function () {
            await ethers.provider.send("evm_increaseTime", [86400 + 1]);
            await ethers.provider.send("evm_mine", []);

            const state = await governance.state(proposalId);
            expect(state).to.equal(1); // Active
        });

        it("should be Defeated if no quorum", async function () {
            // Fast forward past voting delay
            await ethers.provider.send("evm_increaseTime", [86400 + 1]);
            await ethers.provider.send("evm_mine", []);

            // Only voter2 votes (not enough for quorum)
            await governance.connect(voter2).castVote(proposalId, 1);

            // Fast forward past voting period
            await ethers.provider.send("evm_increaseTime", [604800 + 1]);
            await ethers.provider.send("evm_mine", []);

            const state = await governance.state(proposalId);
            expect(state).to.equal(3); // Defeated
        });

        it("should be Succeeded if quorum met and majority for", async function () {
            await ethers.provider.send("evm_increaseTime", [86400 + 1]);
            await ethers.provider.send("evm_mine", []);

            await governance.connect(voter1).castVote(proposalId, 1);
            await governance.connect(voter2).castVote(proposalId, 1);

            await ethers.provider.send("evm_increaseTime", [604800 + 172800 + 1]); // Past timelock
            await ethers.provider.send("evm_mine", []);

            const state = await governance.state(proposalId);
            expect(state).to.equal(4); // Succeeded
        });
    });

    describe("Cancellation", function () {
        it("should allow proposer to cancel", async function () {
            await governance.connect(proposer).propose(
                0,
                "Test Proposal",
                "Description",
                ethers.ZeroAddress,
                "0x",
                0
            );

            await governance.connect(proposer).cancel(1);

            const state = await governance.state(1);
            expect(state).to.equal(2); // Canceled
        });

        it("should allow anyone to cancel if proposer below threshold", async function () {
            await governance.connect(proposer).propose(
                0,
                "Test Proposal",
                "Description",
                ethers.ZeroAddress,
                "0x",
                0
            );

            // Proposer transfers tokens away
            await token.connect(proposer).transfer(owner.address, ethers.parseEther("45000"));

            // Anyone can now cancel
            await governance.connect(voter1).cancel(1);

            const state = await governance.state(1);
            expect(state).to.equal(2); // Canceled
        });
    });
});
