"""
API route definitions
"""
from fastapi import APIRouter, HTTPException
from ..utils.logger import logger
from ..models.schemas import PlanRequest, PlanResponse
from ..agents.l1_agent import l1_agent

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
        # Call L1 Agent for processing
        response = await l1_agent.process_request(request)
        return response
    
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "ai-agent-api"}
