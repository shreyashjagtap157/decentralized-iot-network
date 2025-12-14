const { ethers } = require("hardhat");
const fs = require("fs");
const yaml = require("js-yaml");

async function main() {
  console.log("🚀 Starting multi-chain deployment...\n");

  // Load configuration
  const config = yaml.load(fs.readFileSync("deploy-config.yaml", "utf8"));
  const network = hre.network.name;
  const networkConfig = config.networks[network] || config.testnets[network];

  if (!networkConfig) {
    throw new Error(`Network ${network} not found in config`);
  }

  console.log(`📡 Deploying to ${network} (Chain ID: ${networkConfig.chain_id})`);
  console.log("─".repeat(50));

  const [deployer] = await ethers.getSigners();
  console.log(`👤 Deployer: ${deployer.address}`);
  console.log(`💰 Balance: ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} ${networkConfig.native_token}\n`);

  const deployedContracts = {};

  // ==================== Deploy Token ====================
  console.log("📦 Deploying NetworkCompensation (Token)...");
  const NetworkCompensation = await ethers.getContractFactory("NetworkCompensation");
  const token = await NetworkCompensation.deploy(
    config.deployment.oracle_address || deployer.address,
    config.deployment.initial_reward_rate
  );
  await token.waitForDeployment();
  deployedContracts.token = await token.getAddress();
  console.log(`   ✅ Token: ${deployedContracts.token}`);

  // ==================== Deploy Governance ====================
  console.log("📦 Deploying NetworkGovernance...");
  const NetworkGovernance = await ethers.getContractFactory("NetworkGovernance");
  const governance = await NetworkGovernance.deploy(deployedContracts.token);
  await governance.waitForDeployment();
  deployedContracts.governance = await governance.getAddress();
  console.log(`   ✅ Governance: ${deployedContracts.governance}`);

  // ==================== Deploy Staking ====================
  console.log("📦 Deploying NetworkStaking...");
  const NetworkStaking = await ethers.getContractFactory("NetworkStaking");
  const staking = await NetworkStaking.deploy(deployedContracts.token);
  await staking.waitForDeployment();
  deployedContracts.staking = await staking.getAddress();
  console.log(`   ✅ Staking: ${deployedContracts.staking}`);

  // ==================== Deploy Bridge ====================
  console.log("📦 Deploying CrossChainBridge...");
  const CrossChainBridge = await ethers.getContractFactory("CrossChainBridge");
  const bridge = await CrossChainBridge.deploy(
    deployedContracts.token,
    networkConfig.chain_id
  );
  await bridge.waitForDeployment();
  deployedContracts.bridge = await bridge.getAddress();
  console.log(`   ✅ Bridge: ${deployedContracts.bridge}`);

  // ==================== Deploy NFT ====================
  console.log("📦 Deploying DeviceNFT...");
  const DeviceNFT = await ethers.getContractFactory("DeviceNFT");
  const nft = await DeviceNFT.deploy(`https://api.iot-network.io/nft/`);
  await nft.waitForDeployment();
  deployedContracts.nft = await nft.getAddress();
  console.log(`   ✅ NFT: ${deployedContracts.nft}`);

  // ==================== Configure Contracts ====================
  console.log("\n⚙️  Configuring contracts...");

  // Set network contract in NFT
  await nft.setNetworkContract(deployedContracts.token);
  console.log("   ✓ NFT network contract set");

  // Add validators to bridge
  for (const validator of config.validators || []) {
    if (validator.address && validator.address !== "${VALIDATOR_1}") {
      await bridge.addValidator(validator.address);
      console.log(`   ✓ Added validator: ${validator.name}`);
    }
  }

  // ==================== Save Deployment ====================
  console.log("\n💾 Saving deployment...");
  
  const deployment = {
    network: network,
    chainId: networkConfig.chain_id,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: deployedContracts,
  };

  const deploymentsDir = "./deployments";
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir);
  }

  fs.writeFileSync(
    `${deploymentsDir}/${network}.json`,
    JSON.stringify(deployment, null, 2)
  );

  // ==================== Summary ====================
  console.log("\n" + "═".repeat(50));
  console.log("📋 DEPLOYMENT SUMMARY");
  console.log("═".repeat(50));
  console.log(`Network:     ${network}`);
  console.log(`Chain ID:    ${networkConfig.chain_id}`);
  console.log(`Explorer:    ${networkConfig.explorer}`);
  console.log("");
  console.log("Contracts:");
  for (const [name, address] of Object.entries(deployedContracts)) {
    console.log(`  ${name.padEnd(12)} ${address}`);
  }
  console.log("");
  console.log(`📄 Deployment saved to: deployments/${network}.json`);
  console.log("═".repeat(50));

  // ==================== Verification Hints ====================
  console.log("\n📝 To verify contracts on explorer:");
  console.log(`npx hardhat verify --network ${network} ${deployedContracts.token} ${config.deployment.oracle_address || deployer.address} ${config.deployment.initial_reward_rate}`);
  console.log(`npx hardhat verify --network ${network} ${deployedContracts.governance} ${deployedContracts.token}`);
  console.log(`npx hardhat verify --network ${network} ${deployedContracts.staking} ${deployedContracts.token}`);
  console.log(`npx hardhat verify --network ${network} ${deployedContracts.bridge} ${deployedContracts.token} ${networkConfig.chain_id}`);
  console.log(`npx hardhat verify --network ${network} ${deployedContracts.nft} "https://api.iot-network.io/nft/"`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
