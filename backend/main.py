"""
Quantum-Resilient Communication System - Backend Entry Point

This is the main FastAPI application entry point.
"""

from core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Web-Based Secure Communication System Using Post-Quantum Cryptography and AI",
    version=settings.API_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with project information."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.API_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy"
    }


@app.get("/debug/connections")
async def debug_connections():
    """Debug endpoint to check connection manager state."""
    from managers.connection_manager import connection_manager
    active = []
    for ws, info in connection_manager.active_connections.items():
        active.append({
            "ws_id": str(id(ws)),
            "user": info.username,
            "authenticated": info.authenticated,
            "subscribed": [str(c) for c in info.subscribed_conversations],
        })
    subs = {}
    for conv_id, ws_set in connection_manager.conversation_subscriptions.items():
        subs[str(conv_id)] = [str(id(ws)) for ws in ws_set]
    return {
        "active_connections": active,
        "conversation_subscriptions": subs,
    }


# Include routers
from routers.auth import router as auth_router

app.include_router(auth_router)

from routers.conversation import router as conversation_router

app.include_router(conversation_router)

from routers.message import router as message_router

app.include_router(message_router)

from routers.attachment import router as attachment_router

app.include_router(attachment_router)

from routers.websocket import router as websocket_router

app.include_router(websocket_router)

from routers.conversation_request import router as conversation_request_router
from routers.conversation_request import users_router

app.include_router(conversation_request_router)
app.include_router(users_router)

from routers.group import router as group_router

app.include_router(group_router)

from routers.crypto import router as crypto_router

app.include_router(crypto_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )