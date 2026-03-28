// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SwapGuard
/// @notice L3 on-chain enforcement for DeFi agent swaps.
/// @dev Mirrors a subset of L2 policy-engine rules:
///      R-01 token allowlist, R-02 router allowlist,
///      R-03 slippage cap, R-04 per-tx value cap.
contract SwapGuard {
    /// @dev 1inch-convention sentinel representing native ETH.
    address public constant NATIVE_ETH = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;

    address public owner;
    mapping(address => bool) public allowedTokens;
    mapping(address => bool) public allowedRouters;
    uint256 public maxValueWei;
    uint256 public maxSlippageBps;

    event TokenAllowlistUpdated(address indexed token, bool allowed);
    event RouterAllowlistUpdated(address indexed router, bool allowed);
    event MaxValueUpdated(uint256 oldValue, uint256 newValue);
    event MaxSlippageUpdated(uint256 oldValue, uint256 newValue);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(uint256 _maxValueWei) {
        owner = msg.sender;
        maxValueWei = _maxValueWei;
        maxSlippageBps = 1000;
    }

    function setAllowedToken(address token, bool allowed) external onlyOwner {
        allowedTokens[token] = allowed;
        emit TokenAllowlistUpdated(token, allowed);
    }

    function setAllowedRouter(address router, bool allowed) external onlyOwner {
        allowedRouters[router] = allowed;
        emit RouterAllowlistUpdated(router, allowed);
    }

    function setMaxValue(uint256 _maxValueWei) external onlyOwner {
        uint256 old = maxValueWei;
        maxValueWei = _maxValueWei;
        emit MaxValueUpdated(old, _maxValueWei);
    }

    function setMaxSlippageBps(uint256 _maxSlippageBps) external onlyOwner {
        uint256 old = maxSlippageBps;
        maxSlippageBps = _maxSlippageBps;
        emit MaxSlippageUpdated(old, _maxSlippageBps);
    }

    /// @notice Pre-flight validation called via eth_call before submitting a real tx.
    /// @param sellToken Address of sell token (use NATIVE_ETH for ETH).
    /// @param buyToken Address of buy token (use NATIVE_ETH for ETH).
    /// @param router Target DEX router address.
    /// @param ethEquivalentValue ETH-equivalent value in wei, computed off-chain.
    /// @param realizedSlippageBps Realized slippage in bps, computed off-chain from the quote.
    function validateSwap(
        address sellToken,
        address buyToken,
        address router,
        uint256 ethEquivalentValue,
        uint256 realizedSlippageBps
    ) external view {
        require(allowedTokens[sellToken], "R-01: sell token not allowed");
        require(allowedTokens[buyToken], "R-01: buy token not allowed");
        require(allowedRouters[router], "R-02: router not allowed");
        require(realizedSlippageBps <= maxSlippageBps, "R-03: slippage exceeds cap");
        require(ethEquivalentValue <= maxValueWei, "R-04: value exceeds cap");
    }
}
