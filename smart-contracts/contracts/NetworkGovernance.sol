// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title NetworkGovernance
 * @notice DAO governance contract for decentralized network parameter management
 * @dev Implements proposal creation, voting, and execution with timelock
 */
contract NetworkGovernance is Ownable, ReentrancyGuard {
    
    // ==================== Types ====================
    
    enum ProposalState { Pending, Active, Canceled, Defeated, Succeeded, Queued, Executed, Expired }
    enum ProposalType { ParameterChange, OracleUpdate, EmergencyAction, ProtocolUpgrade, TreasurySpend }
    
    struct Proposal {
        uint256 id;
        address proposer;
        ProposalType proposalType;
        string title;
        string description;
        bytes callData;
        address target;
        uint256 value;
        uint256 startTime;
        uint256 endTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool canceled;
        mapping(address => Receipt) receipts;
    }
    
    struct Receipt {
        bool hasVoted;
        uint8 support; // 0=against, 1=for, 2=abstain
        uint256 votes;
    }
    
    struct ProposalInfo {
        uint256 id;
        address proposer;
        ProposalType proposalType;
        string title;
        string description;
        uint256 startTime;
        uint256 endTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool canceled;
    }
    
    // ==================== State ====================
    
    IERC20 public governanceToken;
    
    uint256 public proposalCount;
    mapping(uint256 => Proposal) public proposals;
    
    // Governance parameters (can be changed via governance)
    uint256 public votingDelay = 1 days;        // Time before voting starts
    uint256 public votingPeriod = 7 days;       // Voting duration
    uint256 public proposalThreshold = 10000 * 1e18;  // Tokens needed to propose
    uint256 public quorumVotes = 100000 * 1e18;       // Votes needed for quorum
    uint256 public timelockDelay = 2 days;      // Delay before execution
    
    // Network parameters managed by governance
    uint256 public rewardRate;
    uint256 public minimumQuality;
    uint256 public maxDevicesPerUser;
    
    // ==================== Events ====================
    
    event ProposalCreated(uint256 indexed id, address proposer, string title, ProposalType proposalType);
    event VoteCast(address indexed voter, uint256 indexed proposalId, uint8 support, uint256 votes);
    event ProposalExecuted(uint256 indexed id);
    event ProposalCanceled(uint256 indexed id);
    event ParameterUpdated(string parameter, uint256 oldValue, uint256 newValue);
    
    // ==================== Constructor ====================
    
    constructor(address _governanceToken) Ownable(msg.sender) {
        require(_governanceToken != address(0), "Invalid token");
        governanceToken = IERC20(_governanceToken);
        
        // Set initial parameters
        rewardRate = 1e12;          // 0.000001 tokens per byte
        minimumQuality = 50;
        maxDevicesPerUser = 100;
    }
    
    // ==================== Proposal Functions ====================
    
    /**
     * @notice Create a new governance proposal
     */
    function propose(
        ProposalType proposalType,
        string memory title,
        string memory description,
        address target,
        bytes memory callData,
        uint256 value
    ) external returns (uint256) {
        require(
            governanceToken.balanceOf(msg.sender) >= proposalThreshold,
            "Below proposal threshold"
        );
        
        proposalCount++;
        uint256 proposalId = proposalCount;
        
        Proposal storage proposal = proposals[proposalId];
        proposal.id = proposalId;
        proposal.proposer = msg.sender;
        proposal.proposalType = proposalType;
        proposal.title = title;
        proposal.description = description;
        proposal.target = target;
        proposal.callData = callData;
        proposal.value = value;
        proposal.startTime = block.timestamp + votingDelay;
        proposal.endTime = proposal.startTime + votingPeriod;
        
        emit ProposalCreated(proposalId, msg.sender, title, proposalType);
        
        return proposalId;
    }
    
    /**
     * @notice Cast a vote on a proposal
     * @param proposalId The ID of the proposal
     * @param support 0=against, 1=for, 2=abstain
     */
    function castVote(uint256 proposalId, uint8 support) external {
        require(support <= 2, "Invalid vote type");
        
        Proposal storage proposal = proposals[proposalId];
        require(state(proposalId) == ProposalState.Active, "Voting not active");
        
        Receipt storage receipt = proposal.receipts[msg.sender];
        require(!receipt.hasVoted, "Already voted");
        
        uint256 votes = governanceToken.balanceOf(msg.sender);
        require(votes > 0, "No voting power");
        
        receipt.hasVoted = true;
        receipt.support = support;
        receipt.votes = votes;
        
        if (support == 0) {
            proposal.againstVotes += votes;
        } else if (support == 1) {
            proposal.forVotes += votes;
        } else {
            proposal.abstainVotes += votes;
        }
        
        emit VoteCast(msg.sender, proposalId, support, votes);
    }
    
    /**
     * @notice Execute a successful proposal
     */
    function execute(uint256 proposalId) external nonReentrant {
        require(state(proposalId) == ProposalState.Succeeded, "Not ready for execution");
        
        Proposal storage proposal = proposals[proposalId];
        proposal.executed = true;
        
        // Execute the proposal
        if (proposal.target != address(0) && proposal.callData.length > 0) {
            (bool success, ) = proposal.target.call{value: proposal.value}(proposal.callData);
            require(success, "Execution failed");
        }
        
        emit ProposalExecuted(proposalId);
    }
    
    /**
     * @notice Cancel a proposal (only proposer or if proposer below threshold)
     */
    function cancel(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        require(
            msg.sender == proposal.proposer || 
            governanceToken.balanceOf(proposal.proposer) < proposalThreshold,
            "Cannot cancel"
        );
        require(!proposal.executed, "Already executed");
        
        proposal.canceled = true;
        emit ProposalCanceled(proposalId);
    }
    
    // ==================== View Functions ====================
    
    function state(uint256 proposalId) public view returns (ProposalState) {
        Proposal storage proposal = proposals[proposalId];
        
        if (proposal.canceled) return ProposalState.Canceled;
        if (proposal.executed) return ProposalState.Executed;
        if (block.timestamp < proposal.startTime) return ProposalState.Pending;
        if (block.timestamp <= proposal.endTime) return ProposalState.Active;
        
        // Voting ended
        if (proposal.forVotes <= proposal.againstVotes) return ProposalState.Defeated;
        if (proposal.forVotes + proposal.againstVotes < quorumVotes) return ProposalState.Defeated;
        
        // Check timelock
        if (block.timestamp < proposal.endTime + timelockDelay) return ProposalState.Queued;
        if (block.timestamp > proposal.endTime + timelockDelay + 14 days) return ProposalState.Expired;
        
        return ProposalState.Succeeded;
    }
    
    function getProposalInfo(uint256 proposalId) external view returns (ProposalInfo memory) {
        Proposal storage p = proposals[proposalId];
        return ProposalInfo({
            id: p.id,
            proposer: p.proposer,
            proposalType: p.proposalType,
            title: p.title,
            description: p.description,
            startTime: p.startTime,
            endTime: p.endTime,
            forVotes: p.forVotes,
            againstVotes: p.againstVotes,
            abstainVotes: p.abstainVotes,
            executed: p.executed,
            canceled: p.canceled
        });
    }
    
    function getReceipt(uint256 proposalId, address voter) external view returns (
        bool hasVoted, uint8 support, uint256 votes
    ) {
        Receipt storage receipt = proposals[proposalId].receipts[voter];
        return (receipt.hasVoted, receipt.support, receipt.votes);
    }
    
    // ==================== Parameter Updates (via governance) ====================
    
    function updateRewardRate(uint256 newRate) external onlyOwner {
        uint256 oldRate = rewardRate;
        rewardRate = newRate;
        emit ParameterUpdated("rewardRate", oldRate, newRate);
    }
    
    function updateMinimumQuality(uint256 newMinimum) external onlyOwner {
        uint256 oldMinimum = minimumQuality;
        minimumQuality = newMinimum;
        emit ParameterUpdated("minimumQuality", oldMinimum, newMinimum);
    }
    
    function updateVotingPeriod(uint256 newPeriod) external onlyOwner {
        uint256 oldPeriod = votingPeriod;
        votingPeriod = newPeriod;
        emit ParameterUpdated("votingPeriod", oldPeriod, newPeriod);
    }
    
    function updateQuorum(uint256 newQuorum) external onlyOwner {
        uint256 oldQuorum = quorumVotes;
        quorumVotes = newQuorum;
        emit ParameterUpdated("quorumVotes", oldQuorum, newQuorum);
    }
}

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}
