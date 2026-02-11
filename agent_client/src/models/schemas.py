"""
Data model definitions - All request and response structures
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Owner -> Agent API ============
class PlanRequest(BaseModel):
    """User request for a transaction plan"""
    request_id: str = Field(..., description="Unique request ID")
    user_message: str = Field(..., description="User input in natural language")
    session_id: str = Field(..., description="Session ID")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ============ Agent -> Owner Response ============
class UnsignedTransaction(BaseModel):
    """Unsigned transaction data"""
    chain_id: int
    to: str
    data: str
    value: str
    gas: str
    nonce: Optional[int] = None


class PolicyLog(BaseModel):
    """Policy check log"""
    checked_at: str
    decision: str  # "ALLOW" or "BLOCK"
    violations: List[Dict[str, Any]] = Field(default_factory=list)


class TxPlan(BaseModel):
    """Transaction plan"""
    plan_id: str
    status: str
    summary: str
    quote_snapshot: Optional[Dict[str, Any]] = None
    unsigned_transaction: Optional[UnsignedTransaction] = None
    policy_log: Optional[PolicyLog] = None


class PlanResponse(BaseModel):
    """Successful response"""
    request_id: str
    status: str  # "NEEDS_OWNER_SIGNATURE", "BLOCKED_BY_POLICY", etc.
    tx_plan: Optional[TxPlan] = None
    error: Optional[Dict[str, Any]] = None


# ============ Agent -> Quote Tool ============
class SwapIntent(BaseModel):
    """Structured swap intent"""
    chain_id: int
    sell_token: str
    buy_token: str
    sell_amount: str  # String in wei unit


class QuoteRequest(BaseModel):
    """Quote request"""
    request_id: str
    intent: SwapIntent
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Quote(BaseModel):
    """Single quote"""
    aggregator: str
    router_address: str
    buy_amount: str
    price_impact_bps: int
    slippage_bps: int
    fee_bps: int
    gas_estimate: str
    gas_price_wei: str
    transaction_calldata_preview: str
    valid_to: int


class QuoteResponse(BaseModel):
    """Quote response"""
    request_id: str
    status: str
    quotes: List[Quote] = Field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None


# ============ Agent -> Policy Engine ============
class PolicyRequest(BaseModel):
    """Policy evaluation request"""
    request_id: str
    context: Dict[str, Any]
    swap_intent: SwapIntent
    proposed_plan: Dict[str, Any]
    quote_snapshot: Dict[str, Any]
    policy_overrides: List[Any] = Field(default_factory=list)


class PolicyResponse(BaseModel):
    """Policy evaluation response"""
    request_id: str
    decision: str  # "ALLOW" or "BLOCK"
    checked_at: str
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    enforced_plan: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None


# ============ LLM Internal Models ============
class LLMPlanOutput(BaseModel):
    """Structured plan output from LLM"""
    intent: SwapIntent
    reasoning: str
    selected_quote_index: int = 0
    additional_note: Optional[str] = None
