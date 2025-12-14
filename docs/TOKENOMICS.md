# IoT Network Tokenomics Whitepaper

## Network Reward Token (NWR)

### Executive Summary

The Network Reward Token (NWR) is the native utility token of the Decentralized IoT Network, designed to incentivize device owners to share their network bandwidth and create a peer-to-peer internet infrastructure. This document outlines the token economics, distribution, and governance mechanisms.

---

## 1. Token Overview

| Property | Value |
|----------|-------|
| **Name** | Network Reward Token |
| **Symbol** | NWR |
| **Standard** | ERC-20 |
| **Decimals** | 18 |
| **Total Supply** | 1,000,000,000 NWR |
| **Initial Circulating** | 100,000,000 NWR (10%) |

## 2. Token Distribution

```
┌─────────────────────────────────────────────────┐
│           TOKEN DISTRIBUTION (1B NWR)           │
├─────────────────────────────────────────────────┤
│  ████████████████████░░░░░  Network Rewards 50% │
│  ████████░░░░░░░░░░░░░░░░░  Team & Advisors 15% │
│  ██████░░░░░░░░░░░░░░░░░░░  Ecosystem Fund  12% │
│  █████░░░░░░░░░░░░░░░░░░░░  Private Sale    10% │
│  ████░░░░░░░░░░░░░░░░░░░░░  Public Sale      8% │
│  ███░░░░░░░░░░░░░░░░░░░░░░  Liquidity        5% │
└─────────────────────────────────────────────────┘
```

### 2.1 Allocation Details

| Allocation | Amount | Vesting |
|------------|--------|---------|
| **Network Rewards** | 500M NWR | Released over 10 years via mining |
| **Team & Advisors** | 150M NWR | 4-year vest, 1-year cliff |
| **Ecosystem Fund** | 120M NWR | DAO controlled |
| **Private Sale** | 100M NWR | 6-month cliff, 18-month vest |
| **Public Sale** | 80M NWR | 25% TGE, 6-month vest |
| **Liquidity** | 50M NWR | Initial DEX liquidity |

## 3. Earning Mechanism

### 3.1 Base Reward Formula

```
Reward = (BytesTransmitted × RewardRate × QualityMultiplier) / 100
```

Where:
- **BytesTransmitted**: Data relayed in bytes
- **RewardRate**: 0.000001 NWR per byte (adjustable via governance)
- **QualityMultiplier**: (QualityScore + 15) / 100

### 3.2 Quality Score Components

| Factor | Weight | Description |
|--------|--------|-------------|
| Uptime | 30% | % of time online in 30 days |
| Latency | 25% | Average response time |
| Bandwidth | 25% | Available bandwidth capacity |
| Reliability | 20% | Successful connection rate |

### 3.3 Staking Multipliers

| Tier | Min Stake | Lock Period | Multiplier |
|------|-----------|-------------|------------|
| Bronze | 1,000 NWR | 7 days | 1.0x |
| Silver | 10,000 NWR | 30 days | 1.25x |
| Gold | 50,000 NWR | 90 days | 1.5x |
| Platinum | 100,000 NWR | 180 days | 2.0x |
| Diamond | 500,000 NWR | 365 days | 3.0x |

## 4. Governance

### 4.1 DAO Structure

NWR holders can participate in governance through:

1. **Proposal Creation**: Requires 10,000 NWR
2. **Voting**: 1 NWR = 1 vote (staking multipliers apply)
3. **Quorum**: 100,000 NWR minimum participation
4. **Timelock**: 2-day delay before execution

### 4.2 Governable Parameters

- Reward rate per byte
- Minimum quality score threshold
- Staking multipliers
- Oracle authorization
- Treasury spending

### 4.3 Proposal Types

| Type | Description | Voting Period |
|------|-------------|---------------|
| Parameter Change | Adjust network parameters | 7 days |
| Treasury Spend | Allocate ecosystem funds | 14 days |
| Protocol Upgrade | Smart contract changes | 21 days |
| Emergency Action | Security patches | 3 days |

## 5. Token Utility

### 5.1 Primary Uses

```
┌──────────────────────────────────────────────┐
│               TOKEN UTILITY                   │
├──────────────────────────────────────────────┤
│  💰 EARN      Share bandwidth → Earn NWR     │
│  🎯 STAKE     Lock tokens → Boost rewards    │
│  🗳️ VOTE      Governance participation       │
│  🌉 BRIDGE    Cross-chain transfers          │
│  💎 NFT       Device ownership as NFTs       │
│  🔗 COLLATERAL  Enterprise SLA deposits      │
└──────────────────────────────────────────────┘
```

### 5.2 Fee Structure

| Action | Fee | Destination |
|--------|-----|-------------|
| Reward Claim | 0% | - |
| Staking | 0% | - |
| Unstaking (early) | 10% | Reward Pool |
| Cross-chain Bridge | 0.5% | Treasury |
| NFT Minting | 5 NWR | Treasury |

## 6. Emissions Schedule

### 6.1 Yearly Rewards Release

| Year | Emission | Cumulative | % of Total |
|------|----------|------------|------------|
| 1 | 100M NWR | 100M | 20% |
| 2 | 80M NWR | 180M | 36% |
| 3 | 65M NWR | 245M | 49% |
| 4 | 55M NWR | 300M | 60% |
| 5 | 45M NWR | 345M | 69% |
| 6-10 | 31M/year | 500M | 100% |

### 6.2 Halving Mechanism

Emissions reduce by 20% annually, ensuring long-term sustainability.

## 7. Cross-Chain Support

### 7.1 Supported Networks

| Network | Chain ID | Status |
|---------|----------|--------|
| Ethereum | 1 | ✅ Live |
| Polygon | 137 | ✅ Live |
| BNB Chain | 56 | ✅ Live |
| Arbitrum | 42161 | 🚧 Coming |
| Optimism | 10 | 🚧 Coming |

### 7.2 Bridge Security

- Multi-signature validator set (3/5 required)
- Daily transfer limits
- Emergency pause capability
- 24-hour timelock for large transfers (>100K NWR)

## 8. Security Measures

### 8.1 Smart Contract Security

- OpenZeppelin security patterns
- ReentrancyGuard on all external calls
- Pausable emergency controls
- Rate limiting on critical functions
- Multi-oracle data submission

### 8.2 Economic Security

- Slashing for malicious oracles
- Staking lockups reduce volatility
- Treasury managed by DAO
- Gradual emissions prevent inflation shock

## 9. Roadmap

### Phase 1: Foundation (Q1-Q2)
- ✅ ERC-20 token deployment
- ✅ Basic staking mechanism
- ✅ Initial reward distribution

### Phase 2: Governance (Q2-Q3)
- ✅ DAO governance launch
- ✅ Proposal and voting system
- 🔄 Multi-chain deployment

### Phase 3: Expansion (Q3-Q4)
- 🔄 Cross-chain bridge
- 🔄 NFT device ownership
- ⏳ Mobile staking integration

### Phase 4: Enterprise (Q4+)
- ⏳ Enterprise SLA contracts
- ⏳ Institutional staking
- ⏳ Advanced analytics

## 10. Conclusion

The Network Reward Token creates a sustainable economic model for decentralized internet infrastructure. By aligning incentives between device owners, network users, and token holders, NWR enables a truly peer-to-peer network that scales organically while maintaining quality and reliability.

---

*Last Updated: December 2024*
*Version: 1.0*

**Disclaimer**: This document is for informational purposes only and does not constitute financial advice. Token economics are subject to change based on governance decisions.
