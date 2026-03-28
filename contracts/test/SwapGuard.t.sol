// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {SwapGuard} from "../src/SwapGuard.sol";

contract SwapGuardTest is Test {
    SwapGuard guard;

    address constant NATIVE_ETH = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    address constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant ONEINCH_V5 = 0x1111111254fb6c44bAC0beD2854e76F90643097d;

    address constant SCAM_TOKEN = address(0xdead);
    address constant UNKNOWN_ROUTER = address(0xbeef);

    uint256 constant MAX_VALUE = 5 ether;

    function setUp() public {
        guard = new SwapGuard(MAX_VALUE);

        guard.setAllowedToken(NATIVE_ETH, true);
        guard.setAllowedToken(WETH, true);
        guard.setAllowedToken(USDC, true);
        guard.setAllowedRouter(ONEINCH_V5, true);
    }

    function test_allowedTokenPair_passes() public view {
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 1 ether, 25);
    }

    function test_unknownSellToken_reverts() public {
        vm.expectRevert("R-01: sell token not allowed");
        guard.validateSwap(SCAM_TOKEN, USDC, ONEINCH_V5, 1 ether, 25);
    }

    function test_unknownBuyToken_reverts() public {
        vm.expectRevert("R-01: buy token not allowed");
        guard.validateSwap(WETH, SCAM_TOKEN, ONEINCH_V5, 1 ether, 25);
    }

    function test_allowedRouter_passes() public view {
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 1 ether, 25);
    }

    function test_unknownRouter_reverts() public {
        vm.expectRevert("R-02: router not allowed");
        guard.validateSwap(WETH, USDC, UNKNOWN_ROUTER, 1 ether, 25);
    }

    function test_withinSlippageCap_passes() public view {
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 1 ether, 1000);
    }

    function test_exceedsSlippageCap_reverts() public {
        vm.expectRevert("R-03: slippage exceeds cap");
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 1 ether, 1001);
    }

    function test_withinValueCap_passes() public view {
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 4.9 ether, 25);
    }

    function test_exceedsValueCap_reverts() public {
        vm.expectRevert("R-04: value exceeds cap");
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 5.1 ether, 25);
    }

    function test_exactCapBoundary_passes() public view {
        guard.validateSwap(WETH, USDC, ONEINCH_V5, 5 ether, 25);
    }

    function test_multiViolation_reverts() public {
        vm.expectRevert("R-01: sell token not allowed");
        guard.validateSwap(SCAM_TOKEN, USDC, UNKNOWN_ROUTER, 10 ether, 5000);
    }
}
