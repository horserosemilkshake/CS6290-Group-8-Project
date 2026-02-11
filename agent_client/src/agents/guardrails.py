"""
L1 Guardrails: Input preprocessing and output validation
L1 is the first line of defense, operating entirely outside the agent's reasoning
"""
import re
from typing import Tuple, Optional, Dict, Any, List
from ..utils.logger import logger
from ..config.settings import settings


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
    
    def extract_key_info(self, user_message: str) -> Dict[str, Any]:
        """Extract key information from user message (simple version)"""
        info = {
            "raw_message": user_message,
            "contains_amount": bool(re.search(r'\d+\.?\d*', user_message)),
            "tokens_mentioned": [],
            "is_trusted": True  # Default trusted, can adjust based on source
        }
        
        # Extract token symbols
        common_tokens = ["ETH", "USDT", "USDC", "BTC", "DAI", "WETH"]
        for token in common_tokens:
            if token.upper() in user_message.upper():
                info["tokens_mentioned"].append(token)
        
        return info


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
        # Basic field check
        required = ["router_address", "buy_amount", "transaction_calldata_preview", "slippage_bps"]
        if not all(k in quote for k in required):
            return False, "Quote missing required fields"
        
        # Hard slippage check (L1 level fast-fail)
        slippage_bps = quote.get("slippage_bps", 0)
        if slippage_bps > settings.MAX_SLIPPAGE_BPS:
            logger.warning(f"[L1] Quote slippage {slippage_bps} exceeds limit {settings.MAX_SLIPPAGE_BPS}")
            return False, f"Slippage {slippage_bps} exceeds hard limit {settings.MAX_SLIPPAGE_BPS}"
        
        return True, None
    
    def mark_untrusted_content(self, content: str, source: str) -> Dict[str, Any]:
        """
        Mark untrusted content (for indirect injection protection)
        Returns a content wrapper with marking
        """
        return {
            "content": content,
            "source": source,
            "trusted": False,
            "requires_spotlight": True  # Needs to be highlighted in logs
        }


# Global instances
input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()
