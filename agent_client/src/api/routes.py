"""API route definitions."""
from fastapi import APIRouter, HTTPException
from ..utils.logger import logger
from ..models.schemas import PlanRequest, PlanResponse, WalletDecisionRequest, WalletHandoff
from ..agents.l1_agent import l1_agent, get_defense_config, set_defense_config
from ..tools.tool_coordinator import get_tool_runtime_status
from ..wallet.bridge import wallet_bridge

router = APIRouter()


@router.post("/agent/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """
    API endpoint for creating transaction plans
    
    POST /v0/agent/plan
    
    Processing flow:
    1. Receive user's natural language transaction request
    2. Call L1 Agent for processing
    3. Return transaction plan or error information
    """
    logger.info(f"API received request: {request.request_id}")
    
    try:
        response = await l1_agent.process_request(request)
        return response
    
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "ai-agent-api",
        "defense_config": get_defense_config(),
        "tool_runtime": get_tool_runtime_status(),
        "wallet_bridge": wallet_bridge.get_runtime_status(),
    }


@router.get("/defense-config")
async def get_config():
    """Return current defense configuration."""
    return {"defense_config": get_defense_config()}


@router.post("/defense-config")
async def update_config(body: dict):
    """Switch defense configuration at runtime (bare / l1 / l1l2 / l1l2l3)."""
    config = body.get("config", "l1l2")
    try:
        set_defense_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"defense_config": get_defense_config()}


@router.get("/wallet/handoffs/{handoff_id}", response_model=WalletHandoff)
async def get_wallet_handoff(handoff_id: str):
    """Fetch signer-boundary handoff state for a pending unsigned plan."""
    handoff = wallet_bridge.get_handoff(handoff_id)
    if handoff is None:
        raise HTTPException(status_code=404, detail=f"Wallet handoff {handoff_id} not found")
    return handoff


@router.post("/wallet/handoffs/{handoff_id}/decision", response_model=WalletHandoff)
async def decide_wallet_handoff(handoff_id: str, request: WalletDecisionRequest):
    """Record explicit owner action for a pending handoff without broadcasting."""
    try:
        handoff = wallet_bridge.record_decision(handoff_id, request.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if handoff is None:
        raise HTTPException(status_code=404, detail=f"Wallet handoff {handoff_id} not found")
    return handoff
