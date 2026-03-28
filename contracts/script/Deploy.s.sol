// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SwapGuard.sol";

/// @notice Deploys SwapGuard and seeds the allowlists.
///         Works on local Anvil, mainnet fork, and Sepolia.
///
///   Usage:
///     forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast
contract DeploySwapGuard is Script {
    // ── Well-known mainnet addresses (also valid on mainnet fork) ─────────
    address constant WETH  = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant USDC  = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant USDT  = 0xdAC17F958D2ee523a2206206994597C13D831ec7;
    address constant DAI   = 0x6B175474E89094C44Da98b954EedeAC495271d0F;

    address constant ONEINCH_V5 = 0x1111111254fb6c44bAC0beD2854e76F90643097d;
    address constant ONEINCH_V6 = 0x1111111254EEB25477B68fb85Ed929f73A960582;
    address constant ZRX_PROXY  = 0xDef1C0ded9bec7F1a1670819833240f027b25EfF;

    // 5 ETH cap, matching L2 MAX_SINGLE_TX_VALUE_ETH
    uint256 constant MAX_VALUE_WEI = 5 ether;

    function run() external {
        vm.startBroadcast();

        SwapGuard guard = new SwapGuard(MAX_VALUE_WEI);

        // R-01: seed token allowlist
        guard.setAllowedToken(guard.NATIVE_ETH(), true);
        guard.setAllowedToken(WETH, true);
        guard.setAllowedToken(USDC, true);
        guard.setAllowedToken(USDT, true);
        guard.setAllowedToken(DAI,  true);

        // R-02: seed router allowlist
        guard.setAllowedRouter(ONEINCH_V5, true);
        guard.setAllowedRouter(ONEINCH_V6, true);
        guard.setAllowedRouter(ZRX_PROXY,  true);

        vm.stopBroadcast();

        console.log("SwapGuard deployed at:", address(guard));
        console.log("  maxValueWei:", guard.maxValueWei());
        console.log("  maxSlippageBps:", guard.maxSlippageBps());
        console.log("  owner:", guard.owner());
    }
}
