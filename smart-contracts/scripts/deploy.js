const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  const oracleAddress = deployer.address; // Using deployer as oracle for now
  const rewardRate = 1; // 1 token per byte

  const NetworkCompensation = await ethers.getContractFactory("NetworkCompensation");
  const networkCompensation = await NetworkCompensation.deploy(oracleAddress, rewardRate);

  await networkCompensation.deployed();

  console.log("NetworkCompensation deployed to:", networkCompensation.address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
