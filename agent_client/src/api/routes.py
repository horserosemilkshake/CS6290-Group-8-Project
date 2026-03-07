"""
API route definitions
"""
from fastapi import APIRouter, HTTPException
from ..utils.logger import logger
from ..models.schemas import PlanRequest, PlanResponse
from ..agents.l1_agent import l1_agent, get_defense_config, set_defense_config

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
    return {"status": "ok", "service": "ai-agent-api"}


@router.get("/defense-config")
async def get_config():
    """Return current defense configuration."""
    return {"defense_config": get_defense_config()}


@router.post("/defense-config")
async def update_config(body: dict):
    """Switch defense configuration at runtime (bare / l1 / l1l2)."""
    config = body.get("config", "l1l2")
    try:
        set_defense_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"defense_config": get_defense_config()}
