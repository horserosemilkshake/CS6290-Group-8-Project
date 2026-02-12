"""
Main CLI Entry Point - Accept JSON input, dispatch to agent, return JSON output

Implements stateless CLI interface per specification.
Input: JSON from stdin  
Output: JSON to stdout (results), JSON lines to stderr (audit logs)
"""

import json
import sys
import asyncio
from typing import Dict, Any, Optional
from src.models.swap_quote import SwapQuote
from src.validation.quote_validator import validate_quote
from src.validation.threat_filters import detect_threats
from src.logging import get_logger


def read_json_from_stdin() -> Optional[Dict[str, Any]]:
    """Read JSON object from stdin"""
    try:
        line = sys.stdin.readline()
        return json.loads(line)
    except json.JSONDecodeError:
        return None
    except EOFError:
        return None


def write_json_to_stdout(data: Dict[str, Any]) -> None:
    """Write JSON object to stdout"""
    print(json.dumps(data), file=sys.stdout)


async def handle_validate_quote(quote_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle quote validation action
    
    Args:
        quote_data: Quote data from request
        
    Returns:
        dict: Validation result
    """
    logger = get_logger()
    
    try:
        # Create SwapQuote object
        from decimal import Decimal
        quote = SwapQuote(
            source=quote_data.get('source', 'user'),
            from_token=quote_data.get('from_token', ''),
            to_token=quote_data.get('to_token', ''),
            from_amount=Decimal(str(quote_data.get('from_amount', '0'))),
            to_amount=Decimal(str(quote_data.get('to_amount', '0'))),
            slippage_tolerance=Decimal(str(quote_data.get('slippage_tolerance', '0'))),
            market_confidence=float(quote_data.get('market_confidence', 0)),
            price_impact=Decimal(str(quote_data.get('price_impact', '0'))),
            execution_fees=Decimal(str(quote_data.get('execution_fees', '0'))),
            quote_expiry=quote_data.get('quote_expiry', ''),
        )
        
        # L1 Pre-filter: Detect threats
        approved_tokens = [
            "0xfFf9976782d46CC05630D92EE39253E4423ACFB9",  # WETH
            "0xd5c6C8169A95bA8Af4D1ee8B47EaF3e2Ce68A4b2",  # USDC
        ]
        
        threats = detect_threats(quote, approved_tokens)
        if threats:
            threat = threats[0]
            logger.log_threat_detection(
                threat_id=threat.threat_id,
                threat_code=threat.threat_code,
                threat_type=threat.threat_type,
                detected_field=threat.detected_field,
                rejection_reason=threat.rejection_reason,
                severity=threat.severity,
                detection_layer="L1_PRE_FILTER",
            )
            return {
                "status": "rejected",
                "quote_id": quote.quote_id,
                "rejection_code": threat.threat_code,
                "rejection_reason": threat.rejection_reason,
            }
        
        # L2 Validation gates
        policy_config = {
            'max_slippage': 10.0,
            'min_confidence': 0.8,
        }
        
        is_valid, rejection_code = validate_quote(quote, policy_config, approved_tokens)
        
        if not is_valid:
            logger.log_quote_validation(
                quote_id=quote.quote_id,
                status="rejected",
                gates_passed=0,
                gates_failed=1,
                rejection_code=rejection_code,
                threat_detected=False,
            )
            return {
                "status": "rejected",
                "quote_id": quote.quote_id,
                "rejection_code": rejection_code,
                "gates_passed": 0,
            }
        
        # Quote passed validation
        logger.log_quote_validation(
            quote_id=quote.quote_id,
            status="accepted",
            gates_passed=6,
            gates_failed=0,
            threat_detected=False,
        )
        
        return {
            "status": "accepted",
            "quote_id": quote.quote_id,
            "gates_passed": 6,
            "gates_failed": 0,
            "message": "Quote passed all deterministic security gates",
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "error_code": "VALIDATION_ERROR",
        }


async def main() -> None:
    """Main CLI entry point"""
    logger = get_logger()
    
    # Read request from stdin
    request = read_json_from_stdin()
    
    if not request:
        error_response = {
            "status": "error",
            "error_code": "INVALID_JSON",
            "error_message": "Failed to parse JSON from stdin"
        }
        write_json_to_stdout(error_response)
        return
    
    # Dispatch to handler based on action
    action = request.get('action', 'validate_quote')
    
    if action == 'validate_quote':
        quote_data = request.get('quote', {})
        response = await handle_validate_quote(quote_data)
    elif action == 'generate_plan':
        # TODO: Implement plan generation
        response = {
            "status": "error",
            "error_code": "NOT_IMPLEMENTED",
            "error_message": "Plan generation not yet implemented"
        }
    else:
        response = {
            "status": "error",
            "error_code": "UNKNOWN_ACTION",
            "error_message": f"Unknown action: {action}"
        }
    
    # Return response
    write_json_to_stdout(response)


if __name__ == "__main__":
    asyncio.run(main())
