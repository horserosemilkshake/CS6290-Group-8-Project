"""
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config.settings import settings
from .api.routes import router
from .utils.logger import logger


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="AI Agent API",
        version=settings.API_VERSION,
        description="Adversarially-Robust Cryptocurrency Swap Agent"
    )
    
    # CORS middleware (development environment)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    app.include_router(router, prefix=f"/{settings.API_VERSION}")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("AI Agent API starting up...")
        logger.info(f"API Version: {settings.API_VERSION}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("AI Agent API shutting down...")
    
    return app


app = create_app()


if __name__ == "__main__":
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True  # Hot reload in development mode
    )
