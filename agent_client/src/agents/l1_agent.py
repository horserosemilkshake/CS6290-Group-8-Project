"""
L1 Agent main logic: Coordinate the entire workflow
Follows least privilege principle, segregates trusted/untrusted contexts
"""
import asyncio
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from ..utils.logger import logger
from ..models.schemas import (
    PlanRequest, PlanResponse, TxPlan, UnsignedTransaction,
    PolicyLog, SwapIntent, QuoteRequest, PolicyRequest, ToolResponse, QuoteResponse
)
from ..llm.llm_planner import llm_planner # type: ignore
from ..tools.tool_coordinator import tool_coordinator
from ..config.settings import settings
from policy_engine.engine import evaluate_policy


# ==========================================================================
# Defense configuration: "bare" | "l1" | "l1l2"
#   bare  — Config0: no guardrails at all (baseline)
#   l1    — Config1: L1 input/output guardrails only
#   l1l2  — Config2: L1 + L2 policy engine (default, full defense)
# ==========================================================================
_defense_config: str = os.environ.get("DEFENSE_CONFIG", "l1l2")


def get_defense_config() -> str:
    return _defense_config


def set_defense_config(config: str) -> None:
    global _defense_config
    valid = ("bare", "l1", "l1l2")
    if config not in valid:
        raise ValueError(f"Invalid defense config '{config}', must be one of {valid}")
    _defense_config = config
    logger.info(f"[Config] Defense config set to: {config}")


# ==============================================================================
# L1 Guardrails - Integrated directly to avoid circular imports
# ==============================================================================

class InputGuardrail:
    """L1 Pre-guardrail: Input sanitization, risk filtering, removing untrusted instructions"""
    
    # Direct Prompt Injection patterns
    BLOCKED_PATTERNS = [
        r"ignore\s+(previous|all|your)\s+instructions?",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"disregard\s+(previous|all)",
        r"new\s+instructions?:",
        r"override\s+policy",
        r"bypass\s+guardrail",
        r"<script>",
        r"DROP\s+TABLE",
        r"for\s+your\s+owner",  # Impersonating owner
        r"on\s+behalf\s+of",
    ]
    
    # Indirect/Encoded Injection patterns
    ENCODED_PATTERNS = [
        r"base64|rot13|hex|unicode",  # Encoding hints
        r"\\x[0-9a-f]{2}",  # Hex encoding
        r"&#\d+;",  # HTML entity encoding
    ]
    
    def validate_input(self, user_message: str, session_id: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Validate user input, returns: (is_valid, error_message, metadata)
        metadata contains untrusted_content_flags for auditing
        """
        metadata = {
            "untrusted_flags": [],
            "risk_level": "low"
        }
        
        # 1. Check message length
        if len(user_message) > 500:
            return False, "Input message too long (max 500 characters)", metadata
        
        if not user_message.strip():
            return False, "Empty message", metadata
        
        # 2. Check direct prompt injection
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, user_message, re.IGNORECASE):
                logger.warning(f"[SECURITY] Blocked direct injection: {pattern} in session {session_id}")
                metadata["untrusted_flags"].append(f"direct_injection:{pattern}")
                metadata["risk_level"] = "high"
                return False, "Input contains prohibited prompt injection attempt", metadata
        
        # 3. Check encoded/indirect injection
        for pattern in self.ENCODED_PATTERNS:
            if re.search(pattern, user_message, re.IGNORECASE):
                logger.warning(f"[SECURITY] Detected encoded content: {pattern}")
                metadata["untrusted_flags"].append(f"encoded_content:{pattern}")
                metadata["risk_level"] = "medium"
        
        # 4. Check for swap-related keywords (must be a swap request)
        swap_keywords = ["swap", "exchange", "trade", "convert", "buy", "sell"]
        if not any(kw in user_message.lower() for kw in swap_keywords):
            return False, "Input does not appear to be a valid swap request", metadata
        
        # 5. Privacy protection: Check for sensitive info leakage
        if self._contains_sensitive_info(user_message):
            logger.warning(f"[PRIVACY] Input contains potential sensitive info")
            metadata["untrusted_flags"].append("contains_sensitive_info")
        
        return True, None, metadata
    
    def _contains_sensitive_info(self, message: str) -> bool:
        """Check if contains sensitive information (address, private key, etc.)"""
        # Check for Ethereum address format
        if re.search(r"0x[a-fA-F0-9]{40}", message):
            return True
        # Check for private key keywords
        if re.search(r"private\s*key|seed\s*phrase|mnemonic", message, re.IGNORECASE):
            return True
        return False
    
    def sanitize_input(self, user_message: str) -> str:
        """
        Sanitize input, remove untrusted content
        Preserve original intent but remove potential injection code
        """
        # Remove HTML tags
        sanitized = re.sub(r'<[^>]+>', '', user_message)
        # Remove special characters
        sanitized = re.sub(r'[^\w\s\.\,\!\?]', '', sanitized)
        return sanitized.strip()


class OutputGuardrail:
    """L1 Post-guardrail: Validate LLM output structure, ensure no unsafe text or tool calls"""
    
    # Forbidden tool calls (excessive-agency prevention)
    FORBIDDEN_TOOLS = [
        "broadcast_transaction",
        "sign_transaction",
        "transfer_funds",
        "approve_unlimited"
    ]
    
    def validate_llm_output(self, llm_output: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate LLM output format and content"""
        # 1. Check required fields
        required_fields = ["intent", "reasoning"]
        for field in required_fields:
            if field not in llm_output:
                return False, f"Missing required field: {field}"
        
        # 2. Validate intent structure
        intent = llm_output.get("intent", {})
        required_intent_fields = ["chain_id", "sell_token", "buy_token", "sell_amount"]
        if not all(k in intent for k in required_intent_fields):
            return False, "Invalid intent structure"
        
        # 3. Validate amount format
        try:
            amount = int(intent["sell_amount"])
            if amount <= 0:
                return False, "Sell amount must be positive"
        except (ValueError, TypeError):
            return False, "Invalid sell_amount format"
        
        # 4. Check for forbidden tool calls
        reasoning = llm_output.get("reasoning", "").lower()
        for tool in self.FORBIDDEN_TOOLS:
            if tool.lower() in reasoning:
                logger.error(f"[SECURITY] LLM attempted to call forbidden tool: {tool}")
                return False, f"Output contains forbidden tool call: {tool}"
        
        # 5. Ensure no privacy leakage
        if self._contains_privacy_leak(llm_output):
            return False, "Output contains potential privacy leak"
        
        return True, None
    
    def _contains_privacy_leak(self, output: Dict[str, Any]) -> bool:
        """Check if output contains privacy leakage"""
        output_str = str(output)
        # Check for transaction hash, address, etc.
        if re.search(r"tx_hash|transaction_hash", output_str, re.IGNORECASE):
            return True
        return False
    
    def validate_quote(self, quote: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate basic compliance of quote data"""
        # Check fields that actually exist in QuoteResponse
        required = ["to_token_amount", "gas_price_gwei", "estimated_gas", "tx"]
        if not all(k in quote for k in required):
            return False, "Quote missing required fields"
        return True, None


# Global instances for use within the L1Agent class
input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()


# ==============================================================================
# L1 Agent
# ==============================================================================



class L1Agent:
    """
    The L1 Agent is the primary coordinator for processing user requests.
    It orchestrates the workflow from input validation to final transaction plan generation.
    """

    async def process_request(self, request: PlanRequest) -> PlanResponse:
        """
        Main entry point for processing user requests.
        Behavior depends on _defense_config:
          bare  — skip L1 + L2 (Config0 baseline)
          l1    — L1 only, skip L2 (Config1)
          l1l2  — full defense (Config2, default)
        """
        request_id = request.request_id
        config = _defense_config
        logger.info(f"[Agent] Processing request {request_id} (defense={config})")

        enable_l1 = config in ("l1", "l1l2")
        enable_l2 = config == "l1l2"
        metadata: Dict[str, Any] = {"untrusted_flags": [], "risk_level": "low"}

        try:
            # ========== Step 1: L1 Pre-guardrail - Input validation ==========
            if enable_l1:
                is_valid, error_msg, metadata = input_guardrail.validate_input(
                    request.user_message,
                    request.session_id
                )

                if not is_valid:
                    logger.warning(f"[L1] Input rejected: {error_msg}, flags: {metadata.get('untrusted_flags')}")
                    return self._refusal_response(
                        request_id,
                        "INPUT_REJECTED",
                        error_msg or "Input validation failed",
                        metadata
                    )

                if metadata.get("risk_level") in ["medium", "high"]:
                    logger.warning(f"[L1] Untrusted content detected: {metadata['untrusted_flags']}")
                    metadata["requires_spotlight"] = True

                sanitized_message = input_guardrail.sanitize_input(request.user_message)
            else:
                sanitized_message = request.user_message

            # ========== Step 2: LLM Planner - Parse intent ==========
            swap_intent: SwapIntent = await llm_planner.parse_intent(sanitized_message)

            # ========== Step 3: L1 Post-guardrail - Validate LLM output ==========
            if enable_l1:
                intent_dict = {
                    "intent": swap_intent.dict(),
                    "reasoning": "parsed by LLM"
                }
                is_valid, error_msg = output_guardrail.validate_llm_output(intent_dict)
                if not is_valid:
                    logger.error(f"[L1] LLM output validation failed: {error_msg}")
                    return self._error_response(request_id, "OUTPUT_VALIDATION_FAILED", error_msg or "Unknown validation error")

            # ========== Step 4: Tool Coordinator - Get DEX quotes ==========
            user_addr = "0x...user_wallet_address..."
            if request.parameters:
                user_addr = request.parameters.get("user_address", user_addr)
            swap_intent.user_address = user_addr

            tool_response = await tool_coordinator(swap_intent)

            if not tool_response or not tool_response.quote:
                return self._error_response(request_id, "TOOL_ERROR", "Failed to get quotes")

            best_quote = tool_response.quote
            if enable_l1:
                is_valid, error_msg = output_guardrail.validate_quote(best_quote.dict())
                if not is_valid:
                    return self._error_response(request_id, "QUOTE_VALIDATION_FAILED", error_msg or "Quote validation failed")

            # ========== Step 5: L2 Policy Engine - Deterministic policy check ==========
            if enable_l2:
                policy_response = evaluate_policy(swap_intent, tool_response)
            else:
                policy_response = {"decision": "ALLOW", "violations": [], "checked_at": None}

            # ========== Step 6: Policy decision handling ==========
            if policy_response.get("decision") == "BLOCK":
                violations = policy_response.get("violations", [])
                first = violations[0] if violations else {}
                reason = first.get("description", "Transaction blocked by security policy")
                logger.warning(f"[L2] Policy blocked request {request_id}: {violations}")
                return self._error_response(request_id, "BLOCKED_BY_POLICY", reason)

            # ========== Step 7: Construct unsigned transaction plan (HITL pause point) ==========
            plan_id = f"plan_{uuid.uuid4().hex[:8]}"
            
            unsigned_tx = UnsignedTransaction(
                chain_id=swap_intent.chain_id,
                to=best_quote.tx.to,
                data=best_quote.tx.data,
                value=swap_intent.sell_amount,
                gas=best_quote.estimated_gas,
                nonce=None
            )
            
            summary = self._create_summary(swap_intent, best_quote)
            
            tx_plan = TxPlan(
                plan_id=plan_id,
                request_id=request_id,
                status="NEEDS_OWNER_SIGNATURE",
                summary=summary,
                intent=swap_intent,
                quote=best_quote,
                policy_decision=policy_response.get("decision", "UNKNOWN"),
                unsigned_tx=unsigned_tx,
            )
            
            logger.info(f"[Agent] Generated TxPlan {plan_id}, awaiting owner signature")
            
            return PlanResponse(
                request_id=request_id,
                status="NEEDS_OWNER_SIGNATURE",
                tx_plan=tx_plan
            )
            
        except Exception as e:
            logger.error(f"[Agent] Error processing request {request_id}: {str(e)}")
            return self._error_response(request_id, "INTERNAL_ERROR", str(e))

    def _refusal_response(
        self, 
        request_id: str, 
        code: str, 
        message: str,
        metadata: Dict[str, Any]
    ) -> PlanResponse:
        """
        Construct refusal response (for adversarial input)
        Includes refusal reason and detected malicious flags
        """
        return PlanResponse(
            request_id=request_id,
            status="REJECTED",
            tx_plan=None,
            error={
                "code": code,
                "message": f"Request rejected: {message}",
                "details": {
                    "untrusted_flags": metadata.get("untrusted_flags", []),
                    "risk_level": metadata.get("risk_level", "unknown")
                }
            }
        )
    
    def _error_response(self, request_id: str, error_code: str, message: str) -> PlanResponse:
        """Construct error response"""
        return PlanResponse(
            request_id=request_id,
            status=error_code,
            tx_plan=None,
            error={
                "code": error_code,
                "message": message,
                "details": {}
            }
        )
    
    def _blocked_response(
        self, 
        request_id: str, 
        policy_response,
        metadata: Dict[str, Any]
    ) -> PlanResponse:
        """Construct policy blocked response"""
        violation = policy_response.violations[0] if policy_response.violations else {}
        return PlanResponse(
            request_id=request_id,
            status="BLOCKED_BY_POLICY",
            tx_plan=None,
            error={
                "code": f"POLICY_VIOLATION_{violation.get('rule_id', 'UNKNOWN').upper()}",
                "message": f"Request blocked by policy. {violation.get('description', 'Policy violation')}",
                "details": {
                    "violations": policy_response.violations,
                    "risk_metadata": metadata
                }
            }
        )
    
    def _sanitize_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize quote data
        Remove fields that may leak privacy
        """
        sanitized = quote.copy()
        # Shorten calldata
        if "transaction_calldata_preview" in sanitized:
            calldata = sanitized["transaction_calldata_preview"]
            if len(calldata) > 20:
                sanitized["transaction_calldata_preview"] = calldata[:10] + "..." + calldata[-6:]
        return sanitized
    
    def _create_summary(self, intent: SwapIntent, quote: "QuoteResponse") -> str:
        """Create transaction summary (no sensitive information)"""
        sell_amount = self._format_amount(intent.sell_amount)
        buy_amount = self._format_amount(quote.to_token_amount)
        return f"Swap {sell_amount} {intent.sell_token} for ≈{buy_amount} {intent.buy_token}"
    
    def _format_amount(self, amount_str: str) -> str:
        """Format amount for display"""
        try:
            amount = int(amount_str) / 10**18
            return f"{amount:.4f}"
        except:
            return amount_str
    
    def _get_token_symbol(self, address: str) -> str:
        """Get token symbol from address"""
        token_map = {
            "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "ETH",
            "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH"
        }
        return token_map.get(address.lower(), "UNKNOWN")


# Global instance
l1_agent = L1Agent()
