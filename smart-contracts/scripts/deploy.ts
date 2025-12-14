import hre from 'hardhat';
import fs from 'fs';
import path from 'path';

async function main() {
    const { ethers, network } = (hre as any);
    const [deployer] = await ethers.getSigners();

    console.log("Deploying contracts with the account:", deployer.address);
    console.log("Account balance:", ethers.utils.formatEther(await deployer.getBalance()));

    // Deploy NetworkCompensation contract
    const NetworkCompensation = await ethers.getContractFactory("NetworkCompensation");

    // Constructor parameters
    const oracleAddress = deployer.address; // Using deployer as oracle for now
    const rewardRate = ethers.utils.parseEther("0.000001"); // 0.000001 ETH per byte

    console.log("Deploying NetworkCompensation contract...");
    const networkCompensation = await NetworkCompensation.deploy(oracleAddress, rewardRate);

    await networkCompensation.deployed();

    console.log("NetworkCompensation deployed to:", networkCompensation.address);
    console.log("Oracle address:", oracleAddress);
    console.log("Reward rate:", ethers.utils.formatEther(rewardRate), "ETH per byte");

    // Verify deployment
    const deployedRewardRate = await networkCompensation.rewardRate();
    const deployedOracle = await networkCompensation.oracle();

    console.log("Verified - Reward rate:", ethers.utils.formatEther(deployedRewardRate));
    console.log("Verified - Oracle address:", deployedOracle);

    // Save deployment info
    const deploymentInfo = {
        contractAddress: networkCompensation.address,
        oracleAddress: deployedOracle,
        rewardRate: ethers.utils.formatEther(deployedRewardRate),
        network: network.name,
        blockNumber: await ethers.provider.getBlockNumber(),
        gasUsed: networkCompensation.deployTransaction.gasLimit?.toString(),
        transactionHash: networkCompensation.deployTransaction.hash,
        timestamp: new Date().toISOString()
    };

    console.log("\n📋 Deployment Summary:");
    console.log(JSON.stringify(deploymentInfo, null, 2));

    // Save deployment info to file
    const deploymentsDir = path.join(__dirname, '..', 'deployments');
    if (!fs.existsSync(deploymentsDir)) {
        fs.mkdirSync(deploymentsDir, { recursive: true });
    }

    const deploymentFile = path.join(deploymentsDir, `${network.name}.json`);
    fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
    console.log(`\n💾 Deployment info saved to: ${deploymentFile}`);

    // Update environment file with contract address
    const envFile = path.join(__dirname, '..', '..', 'web-dashboard', '.env.local');
    let envContent = '';

    if (fs.existsSync(envFile)) {
        envContent = fs.readFileSync(envFile, 'utf8');
    }

    // Update contract address in environment
    const contractAddressLine = `NEXT_PUBLIC_NETWORK_COMPENSATION_CONTRACT=${networkCompensation.address}`;

    if (envContent.includes('NEXT_PUBLIC_NETWORK_COMPENSATION_CONTRACT=')) {
        envContent = envContent.replace(
            /NEXT_PUBLIC_NETWORK_COMPENSATION_CONTRACT=.*/,
            contractAddressLine
        );
    } else {
        envContent += `\n${contractAddressLine}\n`;
    }

    fs.writeFileSync(envFile, envContent);
    console.log(`\n🔧 Updated contract address in ${envFile}`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
