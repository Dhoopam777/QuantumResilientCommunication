"""
Quantum-Resilient Communication System - Backend Entry Point

This is the main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Quantum-Resilient Communication System",
    description="Web-Based Secure Communication System Using Post-Quantum Cryptography and AI",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Quantum-Resilient Communication System API",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "api": "operational",
            "database": "pending",
            "ai": "pending",
            "crypto": "pending"
        }
    }


# Include routers will be added here as they are developed
# from backend.routers import auth, messaging, websocket
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(messaging.router, prefix="/api/messaging", tags=["messaging"])
# app.include_router(websocket.router, prefix="/api/ws", tags=["websocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )