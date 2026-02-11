"""
L1 Agent main logic: Coordinate the entire workflow
Follows least privilege principle, segregates trusted/untrusted contexts
"""
import uuid
from datetime import datetime
from typing import Dict, Any
from ..utils.logger import logger
from ..models.schemas import (
    PlanRequest, PlanResponse, TxPlan, UnsignedTransaction,
    PolicyLog, SwapIntent, QuoteRequest, PolicyRequest
)
from .guardrails import input_guardrail, output_guardrail
from .llm_planner import llm_planner
from ..tools.tool_coordinator import tool_coordinator
from ..policy.policy_engine import policy_engine


class L1Agent:
    """
    L1 Agent: Main coordinator
    
    Workflow:
    1. L1 Pre-guardrail: Input validation, malicious content detection
    2. LLM Planner: Parse intent (no decision-making)
    3. Tool Coordinator: Get quotes
    4. L1 Post-guardrail: Validate output structure
    5. L2 Policy Engine: Deterministic policy check (cannot be overridden by LLM)
    6. HITL Pause: Return unsigned TxPlan, await owner confirmation
    """
    
    async def process_request(self, request: PlanRequest) -> PlanResponse:
        """
        Main entry point for processing user requests
        
        Privacy protection:
        - Does not require user to provide wallet address or balance
        - Does not leak transaction history
        - Does not publish TX hash
        """
        request_id = request.request_id
        logger.info(f"[Agent] Processing request {request_id}")
        
        try:
            # ========== Step 1: L1 Pre-guardrail - Input validation ==========
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
            
            # If encoded content detected, mark as untrusted
            if metadata.get("risk_level") in ["medium", "high"]:
                logger.warning(f"[L1] Untrusted content detected: {metadata['untrusted_flags']}")
                # Continue processing but spotlight in logs
                metadata["requires_spotlight"] = True
            
            # Sanitize input
            sanitized_message = input_guardrail.sanitize_input(request.user_message)
            
            # ========== Step 2: LLM Planner - Parse intent ==========
            # Only pass sanitized message, no untrusted external data
            parsed = llm_planner.parse_intent(sanitized_message, context_metadata=metadata)
            
            # Check parsing result
            if not parsed.get("intent") or parsed.get("confidence") == "low":
                return self._refusal_response(
                    request_id,
                    "PARSING_FAILED",
                    parsed.get("reasoning", "Could not parse valid swap intent"),
                    metadata
                )
            
            # ========== Step 3: L1 Post-guardrail - Validate LLM output ==========
            is_valid, error_msg = output_guardrail.validate_llm_output(parsed)
            if not is_valid:
                logger.error(f"[L1] LLM output validation failed: {error_msg}")
                return self._error_response(request_id, "OUTPUT_VALIDATION_FAILED", error_msg or "Unknown validation error")
            
            # ========== Step 4: Tool Coordinator - Get DEX quotes ==========
            quote_request = QuoteRequest(
                request_id=request_id,
                intent=SwapIntent(**parsed["intent"]),
                config=request.parameters
            )
            quote_response = await tool_coordinator.get_dex_quotes(quote_request)
            
            if quote_response.status != "SUCCESS" or not quote_response.quotes:
                return self._error_response(request_id, "TOOL_ERROR", "Failed to get quotes")
            
            # Validate best quote
            best_quote = quote_response.quotes[0]
            is_valid, error_msg = output_guardrail.validate_quote(best_quote.dict())
            if not is_valid:
                return self._error_response(request_id, "QUOTE_VALIDATION_FAILED", error_msg or "Quote validation failed")
            
            # ========== Step 5: L2 Policy Engine - Deterministic policy check ==========
            # L2 decision cannot be overridden by LLM
            policy_request = PolicyRequest(
                request_id=request_id,
                context={
                    "session_id": request.session_id,
                    "user_message": request.user_message,
                    "risk_metadata": metadata
                },
                swap_intent=SwapIntent(**parsed["intent"]),
                proposed_plan={
                    "selected_quote_index": 0,
                    "confidence": parsed.get("confidence")
                },
                quote_snapshot=quote_response.dict()
            )
            
            policy_response = await policy_engine.evaluate_policy(policy_request)
            
            # ========== Step 6: Policy decision handling ==========
            if policy_response.decision == "BLOCK":
                # Policy blocked, refuse with reason
                logger.warning(f"[L2] Policy blocked request: {policy_response.violations}")
                return self._blocked_response(request_id, policy_response, metadata)
            
            # Check if enforced_plan exists
            if not policy_response.enforced_plan:
                logger.error(f"[L2] Policy response missing enforced_plan")
                return self._error_response(request_id, "POLICY_ERROR", "Policy engine did not provide enforced plan")
            
            # ========== Step 7: Construct unsigned transaction plan (HITL pause point) ==========
            # Generate plan_id for tracking
            plan_id = f"plan_{uuid.uuid4().hex[:8]}"
            
            # Construct unsigned transaction from enforced_plan (privacy protection: no nonce)
            unsigned_tx = UnsignedTransaction(
                chain_id=parsed["intent"]["chain_id"],
                to=policy_response.enforced_plan["allowlisted_router"],
                data=policy_response.enforced_plan["final_calldata"],
                value=parsed["intent"]["sell_amount"],
                gas=best_quote.gas_estimate,
                nonce=None  # Privacy protection: Agent doesn't know user nonce
            )
            
            # Construct transaction summary (sanitized)
            summary = self._create_summary(parsed["intent"], best_quote)
            
            tx_plan = TxPlan(
                plan_id=plan_id,
                status="NEEDS_OWNER_SIGNATURE",  # HITL pause state
                summary=summary,
                quote_snapshot=self._sanitize_quote(best_quote.dict()),
                unsigned_transaction=unsigned_tx,
                policy_log=PolicyLog(
                    checked_at=policy_response.checked_at,
                    decision=policy_response.decision,
                    violations=policy_response.violations
                )
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
    
    def _create_summary(self, intent: Dict[str, Any], quote) -> str:
        """Create transaction summary (no sensitive information)"""
        sell_amount = self._format_amount(intent["sell_amount"])
        buy_amount = self._format_amount(quote.buy_amount)
        
        # Use token symbols instead of addresses
        sell_symbol = self._get_token_symbol(intent["sell_token"])
        buy_symbol = self._get_token_symbol(intent["buy_token"])
        
        return f"Swap {sell_amount} {sell_symbol} for ≈{buy_amount} {buy_symbol} via {quote.aggregator}"
    
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
