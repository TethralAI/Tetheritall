"""
Main FastAPI application for the Tethral Suggestion Engine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

from .api import router as suggestion_router
from .mobile_api import router as mobile_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Tethral Suggestion Engine",
    description="Intelligent device and service combination discovery and recommendation engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include routers
app.include_router(suggestion_router, prefix="/api/v1")
app.include_router(mobile_router, prefix="/api/v1/mobile")

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tethral-suggestion-engine"}

@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready", "service": "tethral-suggestion-engine"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Tethral Suggestion Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
