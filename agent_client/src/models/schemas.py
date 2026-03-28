"""
Data model definitions - All request and response structures
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic import ConfigDict
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


# ============ Agent Internal & Tool Schemas ============

class TxData(BaseModel):
    """Represents the raw transaction data from a quote."""
    to: str
    data: str
    value: str
    model_config = ConfigDict(extra="ignore")


class QuoteResponse(BaseModel):
    """Represents a single quote from a DEX aggregator."""
    to_token_amount: str
    gas_price_gwei: str
    estimated_gas: str
    tx: TxData
    model_config = ConfigDict(extra="ignore")


class ToolResponse(BaseModel):
    """Aggregated response from all tools."""
    market_snapshot: Dict[str, float]
    quote: QuoteResponse
    model_config = ConfigDict(extra="ignore")


# ============ Agent -> Quote Tool ============

class SwapIntent(BaseModel):
    """Structured swap intent, parsed from user input by the LLM."""
    # Fields must match the JSON output structure defined in the LLM's system prompt.
    chain_id: int = Field(..., description="The chain ID for the transaction, e.g., 1 for Ethereum Mainnet.")
    sell_token: str = Field(..., description="Symbol of the token to sell (e.g., WETH).")
    buy_token: str = Field(..., description="Symbol of the token to buy (e.g., USDC).")
    sell_amount: str = Field(..., description="The amount of sell_token to swap, in its smallest unit (e.g., wei).")
    user_address: Optional[str] = Field(None, description="The user's wallet address.")


class TxPlan(BaseModel):
    """Transaction plan"""
    plan_id: str
    request_id: str
    status: str  # e.g., "NEEDS_OWNER_SIGNATURE", "REJECTED", "ERROR"
    summary: str
    intent: SwapIntent
    quote: QuoteResponse
    policy_decision: str  # "ALLOW" or "BLOCK"
    unsigned_tx: UnsignedTransaction
    failure_reason: Optional[str] = None


class PlanResponse(BaseModel):
    """Successful response"""
    request_id: str
    status: str  # "NEEDS_OWNER_SIGNATURE", "BLOCKED_BY_POLICY", etc.
    tx_plan: Optional[TxPlan] = None
    error: Optional[Dict[str, Any]] = None


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
