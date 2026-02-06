// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SoulToken.sol";
import "../src/SoulGuard.sol";

contract DeployScript is Script {
    function run() external {
        // Read deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        // Read Ownable Executor address (must be pre-deployed or use Rhinestone's)
        address ownableExecutor = vm.envAddress("OWNABLE_EXECUTOR_ADDRESS");

        // Read ECDSA Validator address (must be pre-deployed or use Rhinestone's)
        address ecdsaValidator = vm.envAddress("ECDSA_VALIDATOR_ADDRESS");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy SoulToken
        SoulToken soulToken = new SoulToken();
        console.log("SoulToken deployed at:", address(soulToken));

        // 2. Deploy SoulGuard
        SoulGuard soulGuard = new SoulGuard(
            address(soulToken),
            ownableExecutor,
            ecdsaValidator
        );
        console.log("SoulGuard deployed at:", address(soulGuard));

        // 3. Set base URI for metadata endpoint
        string memory baseURI = vm.envOr("BASE_URI", string(""));
        if (bytes(baseURI).length > 0) {
            soulToken.setBaseURI(baseURI);
            console.log("BaseURI set to:", baseURI);
        }

        vm.stopBroadcast();

        // Log deployment summary
        console.log("=== Deployment Summary ===");
        console.log("Network: Base Sepolia");
        console.log("SoulToken:", address(soulToken));
        console.log("SoulGuard:", address(soulGuard));
        console.log("OwnableExecutor:", ownableExecutor);
        console.log("ECDSAValidator:", ecdsaValidator);
    }
}
