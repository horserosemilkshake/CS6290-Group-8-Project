"""
L1 Agent main logic.

Coordinates input validation, intent parsing, tool orchestration, deterministic
policy checks, optional L3 validation, and unsigned-plan handoff.
"""
from __future__ import annotations

import os
import re
import threading
import uuid
from typing import Any, Dict, Optional, Tuple

from ..llm.llm_planner import llm_planner  # type: ignore
from ..models.schemas import (
    PlanRequest,
    PlanResponse,
    QuoteResponse,
    QuoteValidity,
    SlippageBounds,
    SwapIntent,
    TxPlan,
    UnsignedTransaction,
)
from ..tools.tool_coordinator import tool_coordinator
from ..utils.logger import logger
from ..wallet.bridge import wallet_bridge
from policy_engine import config as policy_cfg
from policy_engine.engine import evaluate_policy
from policy_engine.l3_validator import validate_l3
from policy_engine.rules import extract_request_signals


_defense_config: str = os.environ.get("DEFENSE_CONFIG", "l1l2")
_defense_config_lock = threading.Lock()


def get_defense_config() -> str:
    with _defense_config_lock:
        return _defense_config


def set_defense_config(config: str) -> None:
    global _defense_config
    valid = ("bare", "l1", "l1l2", "l1l2l3")
    if config not in valid:
        raise ValueError(f"Invalid defense config '{config}', must be one of {valid}")
    with _defense_config_lock:
        _defense_config = config
    logger.info("[Config] Defense config set to: %s", config)


class InputGuardrail:
    """L1 pre-guardrail for sanitization and obvious prompt-injection checks."""

    BLOCKED_PATTERNS = [
        r"ignore\s+(previous|all|your)\s+instructions?",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"disregard\s+(previous|all)",
        r"new\s+rule\s*:",
        r"new\s+instructions?:",
        r"forget\s+standard\s+protocols?",
        r"shadow\s+swap",
        r"override\s+policy",
        r"bypass\s+guardrail",
        r"<script>",
        r"DROP\s+TABLE",
        r"for\s+your\s+owner",
        r"on\s+behalf\s+of",
        r"steal\s+the\s+funds?",
        r"verified\s+as\s+admin",
        r"same\s+user\s+who\s+verified",
        r"ignore\s+the\s+whitelist",
        r"force\s+the\s+swap",
        r"send\s+fees?\s+to\s+(?:my\s+)?(?:personal\s+)?wallet",
        r"ignore\s+standard\s+error\s+messages",
    ]

    ENCODED_PATTERNS = [
        r"\b(base64|rot13|unicode)\b",
        r"\\x[0-9a-f]{2}",
        r"&#\d+;",
    ]

    def validate_input(self, user_message: str, session_id: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        metadata = {"untrusted_flags": [], "risk_level": "low"}

        if len(user_message) > 500:
            return False, "Input message too long (max 500 characters)", metadata
        if not user_message.strip():
            return False, "Empty message", metadata

        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, user_message, re.IGNORECASE):
                logger.warning("[SECURITY] Blocked direct injection: %s in session %s", pattern, session_id)
                metadata["untrusted_flags"].append(f"direct_injection:{pattern}")
                metadata["risk_level"] = "high"
                return False, "Input contains prohibited prompt injection attempt", metadata

        for pattern in self.ENCODED_PATTERNS:
            if re.search(pattern, user_message, re.IGNORECASE):
                logger.warning("[SECURITY] Detected encoded content: %s", pattern)
                metadata["untrusted_flags"].append(f"encoded_content:{pattern}")
                metadata["risk_level"] = "medium"

        swap_keywords = ["swap", "exchange", "trade", "convert", "buy", "sell"]
        if not any(re.search(rf"\b{keyword}\b", user_message, re.IGNORECASE) for keyword in swap_keywords):
            return False, "Input does not appear to be a valid swap request", metadata

        if self._contains_sensitive_info(user_message):
            logger.warning("[PRIVACY] Input contains potential sensitive info")
            metadata["untrusted_flags"].append("contains_sensitive_info")

        return True, None, metadata

    def _contains_sensitive_info(self, message: str) -> bool:
        if re.search(r"0x[a-fA-F0-9]{40}", message):
            return True
        if re.search(r"private\s*key|seed\s*phrase|mnemonic", message, re.IGNORECASE):
            return True
        return False

    def sanitize_input(self, user_message: str) -> str:
        sanitized = re.sub(r"<[^>]+>", "", user_message)
        sanitized = re.sub(r"[^\w\s\.\,\!\?\-\:\;\/\(\)\@\#\%]", "", sanitized)
        return sanitized.strip()


class OutputGuardrail:
    """L1 post-guardrail for structured LLM and quote outputs."""

    FORBIDDEN_TOOLS = [
        "broadcast_transaction",
        "sign_transaction",
        "transfer_funds",
        "approve_unlimited",
    ]

    def validate_llm_output(self, llm_output: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        for field in ("intent", "reasoning"):
            if field not in llm_output:
                return False, f"Missing required field: {field}"

        intent = llm_output.get("intent", {})
        required_intent_fields = ["chain_id", "sell_token", "buy_token", "sell_amount"]
        if not all(key in intent for key in required_intent_fields):
            return False, "Invalid intent structure"

        try:
            amount = int(intent["sell_amount"])
            if amount <= 0:
                return False, "Sell amount must be positive"
        except (ValueError, TypeError):
            return False, "Invalid sell_amount format"

        reasoning = llm_output.get("reasoning", "").lower()
        for tool in self.FORBIDDEN_TOOLS:
            if tool.lower() in reasoning:
                logger.error("[SECURITY] LLM attempted to call forbidden tool: %s", tool)
                return False, f"Output contains forbidden tool call: {tool}"

        if self._contains_privacy_leak(llm_output):
            return False, "Output contains potential privacy leak"

        return True, None

    def _contains_privacy_leak(self, output: Dict[str, Any]) -> bool:
        return bool(re.search(r"tx_hash|transaction_hash", str(output), re.IGNORECASE))

    def validate_quote(self, quote: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        required = ["to_token_amount", "gas_price_gwei", "estimated_gas", "tx"]
        if not all(key in quote for key in required):
            return False, "Quote missing required fields"
        return True, None


input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()


class L1Agent:
    """Primary coordinator for processing user requests."""

    _TOKEN_DECIMALS = {
        "ETH": 18,
        "WETH": 18,
        "DAI": 18,
        "USDC": 6,
        "USDT": 6,
        "WBTC": 8,
    }

    async def process_request(self, request: PlanRequest) -> PlanResponse:
        request_id = request.request_id
        config = get_defense_config()
        logger.info("[Agent] Processing request %s (defense=%s)", request_id, config)

        enable_l1 = config in ("l1", "l1l2", "l1l2l3")
        enable_l2 = config in ("l1l2", "l1l2l3")
        enable_l3 = config == "l1l2l3"
        metadata: Dict[str, Any] = {"untrusted_flags": [], "risk_level": "low"}

        try:
            if enable_l1:
                is_valid, error_msg, metadata = input_guardrail.validate_input(
                    request.user_message,
                    request.session_id,
                )
                if not is_valid:
                    logger.warning("[L1] Input rejected: %s, flags: %s", error_msg, metadata.get("untrusted_flags"))
                    return self._refusal_response(
                        request_id,
                        "INPUT_REJECTED",
                        error_msg or "Input validation failed",
                        metadata,
                    )

                if metadata.get("risk_level") in ["medium", "high"]:
                    metadata["requires_spotlight"] = True

                sanitized_message = input_guardrail.sanitize_input(request.user_message)
                if sanitized_message != request.user_message:
                    metadata["untrusted_flags"].append("sanitized_markup_or_control_content")
                    logger.info("[L1] Sanitized untrusted markup/control content for %s", request_id)
            else:
                sanitized_message = request.user_message

            swap_intent: SwapIntent = await llm_planner.parse_intent(sanitized_message)

            if enable_l1:
                intent_dict = {"intent": swap_intent.model_dump(), "reasoning": "parsed by LLM"}
                is_valid, error_msg = output_guardrail.validate_llm_output(intent_dict)
                if not is_valid:
                    logger.error("[L1] LLM output validation failed: %s", error_msg)
                    return self._error_response(
                        request_id,
                        "OUTPUT_VALIDATION_FAILED",
                        error_msg or "Unknown validation error",
                    )

            user_addr = "0x...user_wallet_address..."
            if request.parameters:
                user_addr = request.parameters.get("user_address", user_addr)
            swap_intent.user_address = user_addr
            swap_intent.request_signals = extract_request_signals(request.user_message)

            try:
                tool_response = await tool_coordinator(swap_intent)
            except RuntimeError as exc:
                logger.error("[Tool] Tool coordination failed for %s: %s", request_id, str(exc))
                return self._error_response(request_id, "TOOL_ERROR", str(exc))

            if not tool_response or not tool_response.quote:
                return self._error_response(request_id, "TOOL_ERROR", "Failed to get quotes")

            best_quote = tool_response.quote
            if enable_l1:
                is_valid, error_msg = output_guardrail.validate_quote(best_quote.model_dump())
                if not is_valid:
                    return self._error_response(
                        request_id,
                        "QUOTE_VALIDATION_FAILED",
                        error_msg or "Quote validation failed",
                    )

            if enable_l2:
                norm_resp = self._normalize_for_l2(request_id, swap_intent, tool_response)
                if isinstance(norm_resp, PlanResponse):
                    return norm_resp

                try:
                    policy_response = evaluate_policy(swap_intent, tool_response)
                except Exception as exc:
                    logger.error("[L2] Policy evaluation error for request %s: %s", request_id, str(exc))
                    return self._error_response(
                        request_id,
                        "BLOCKED_BY_POLICY",
                        "Policy evaluation error: failed to evaluate policy",
                    )
            else:
                policy_response = {"decision": "ALLOW", "violations": [], "checked_at": None, "audit": {}}

            if policy_response.get("decision") == "BLOCK":
                violations = policy_response.get("violations", [])
                first = violations[0] if violations else {}
                reason = first.get("description", "Transaction blocked by security policy")
                logger.warning("[L2] Policy blocked request %s: %s", request_id, violations)
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)

            if enable_l3:
                l3_result = validate_l3(swap_intent, tool_response)
                l3_decision = l3_result.get("decision", "SKIP")
                if l3_decision == "BLOCK":
                    l3_violations = l3_result.get("violations", [])
                    first = l3_violations[0] if l3_violations else {}
                    reason = first.get("description", "Transaction blocked by L3 on-chain enforcement")
                    logger.warning("[L3] On-chain blocked request %s: %s", request_id, l3_violations)
                    return self._error_response(request_id, "BLOCKED_BY_L3", reason)
                if l3_decision == "SKIP":
                    logger.info("[L3] Skipped (not configured): %s", l3_result.get("reason", ""))
                else:
                    logger.info("[L3] On-chain validation passed for %s", request_id)

            plan_id = f"plan_{uuid.uuid4().hex[:8]}"
            unsigned_tx = UnsignedTransaction(
                chain_id=swap_intent.chain_id,
                to=best_quote.tx.to,
                data=best_quote.tx.data,
                value=best_quote.tx.value,
                gas=best_quote.estimated_gas,
                nonce=None,
            )

            summary = self._create_summary(swap_intent, best_quote)
            quote_metadata = getattr(best_quote, "metadata", {}) or {}
            policy_audit = policy_response.get("audit", {}) or {}
            tx_plan = TxPlan(
                plan_id=plan_id,
                request_id=request_id,
                status="PENDING_OWNER_ACTION",
                summary=summary,
                intent=swap_intent,
                quote=best_quote,
                policy_decision=policy_response.get("decision", "UNKNOWN"),
                unsigned_tx=unsigned_tx,
                slippage_bounds=SlippageBounds(
                    max_slippage_bps=int(quote_metadata.get("max_slippage_bps", policy_cfg.MAX_SLIPPAGE_BPS)),
                    computed_slippage_bps=policy_audit.get("computed_slippage_bps"),
                ),
                quote_validity=QuoteValidity(
                    quoted_at=str(quote_metadata.get("quoted_at")),
                    expires_at=str(quote_metadata.get("quote_expires_at")),
                    ttl_seconds=int(quote_metadata.get("quote_ttl_seconds", policy_cfg.QUOTE_TTL_SECONDS)),
                ),
                tool_audit=getattr(tool_response, "audit", {}) or {},
            )
            tx_plan.wallet_handoff = wallet_bridge.create_handoff(request_id=request_id, plan_id=plan_id)

            logger.info("[Agent] Generated TxPlan %s, awaiting owner signature", plan_id)
            return PlanResponse(request_id=request_id, status="NEEDS_OWNER_SIGNATURE", tx_plan=tx_plan)

        except Exception as exc:
            logger.error("[Agent] Error processing request %s: %s", request_id, str(exc))
            return self._error_response(request_id, "INTERNAL_ERROR", str(exc))

    def _refusal_response(
        self,
        request_id: str,
        code: str,
        message: str,
        metadata: Dict[str, Any],
    ) -> PlanResponse:
        return PlanResponse(
            request_id=request_id,
            status="REJECTED",
            tx_plan=None,
            error={
                "code": code,
                "message": f"Request rejected: {message}",
                "details": {
                    "untrusted_flags": metadata.get("untrusted_flags", []),
                    "risk_level": metadata.get("risk_level", "unknown"),
                },
            },
        )

    def _error_response(self, request_id: str, error_code: str, message: str) -> PlanResponse:
        return PlanResponse(
            request_id=request_id,
            status=error_code,
            tx_plan=None,
            error={"code": error_code, "message": message, "details": {}},
        )

    def _sanitize_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = quote.copy()
        if "transaction_calldata_preview" in sanitized:
            calldata = sanitized["transaction_calldata_preview"]
            if len(calldata) > 20:
                sanitized["transaction_calldata_preview"] = calldata[:10] + "..." + calldata[-6:]
        return sanitized

    def _normalize_for_l2(self, request_id: str, intent: SwapIntent, tool_response: Any):
        """Ensure the structures expected by the L2 policy engine are present."""
        try:
            raw_snapshot = getattr(tool_response, "market_snapshot", None) or {}
            normalized_snapshot: Dict[str, float] = {}
            for key, value in raw_snapshot.items():
                try:
                    normalized_snapshot[str(key).upper()] = float(value)
                except Exception:
                    normalized_snapshot[str(key).upper()] = 0.0

            for token in (intent.sell_token, intent.buy_token):
                if token and token.upper() not in normalized_snapshot:
                    logger.info("[L2] market_snapshot missing price for %s, inserting fallback 0.0", token)
                    normalized_snapshot[token.upper()] = 0.0

            tool_response.market_snapshot = normalized_snapshot

            quote = getattr(tool_response, "quote", None)
            if quote is None:
                reason = "Missing quote required by policy engine"
                logger.warning("[L2] %s for request %s", reason, request_id)
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)

            if not hasattr(quote, "estimated_gas") or quote.estimated_gas in (None, ""):
                quote.estimated_gas = "0"

            metadata = getattr(quote, "metadata", None) or {}
            metadata.setdefault("max_slippage_bps", policy_cfg.MAX_SLIPPAGE_BPS)
            metadata.setdefault("quote_ttl_seconds", policy_cfg.QUOTE_TTL_SECONDS)
            if not metadata.get("quoted_at"):
                reason = "Quote missing quoted_at metadata required by policy engine"
                logger.warning("[L2] %s for request %s", reason, request_id)
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)
            if not metadata.get("quote_expires_at"):
                reason = "Quote missing quote_expires_at metadata required by policy engine"
                logger.warning("[L2] %s for request %s", reason, request_id)
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)
            quote.metadata = metadata

            tx = getattr(quote, "tx", None)
            if not tx:
                reason = "Quote missing tx object required by L2 policy"
                logger.warning("[L2] %s for request %s", reason, request_id)
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)

            missing = []
            for field in ("to", "data", "value"):
                value = getattr(tx, field, None)
                if value is None or (isinstance(value, str) and not value.strip()):
                    missing.append(field)
            if missing:
                reason = f"Quote.tx missing required fields: {', '.join(missing)}"
                logger.warning("[L2] %s for request %s", reason, request_id)
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)

            return None
        except Exception as exc:
            logger.error("[L2] Normalization error for request %s: %s", request_id, str(exc))
            return self._error_response(
                request_id,
                "BLOCKED_BY_POLICY",
                "Normalization error before policy evaluation",
            )

    def _create_summary(self, intent: SwapIntent, quote: QuoteResponse) -> str:
        sell_amount = self._format_amount(intent.sell_amount, intent.sell_token)
        buy_amount = self._format_amount(quote.to_token_amount, intent.buy_token)
        return f"Swap {sell_amount} {intent.sell_token} for ~{buy_amount} {intent.buy_token}"

    def _format_amount(self, amount_str: str, token: str = "") -> str:
        try:
            decimals = self._TOKEN_DECIMALS.get(token.upper(), 18)
            amount = int(amount_str) / 10 ** decimals
            return f"{amount:.4f}"
        except Exception:
            return amount_str

    def _get_token_symbol(self, address: str) -> str:
        token_map = {
            "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "ETH",
            "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
        }
        return token_map.get(address.lower(), "UNKNOWN")


l1_agent = L1Agent()
