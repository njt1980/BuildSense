"""Main application module for BuildSense FastAPI API backend.

This module initializes the FastAPI app instance, configures the CORS middleware
to allow communication with the Next.js frontend, and registers core routing endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize the FastAPI application
app = FastAPI(
    title="BuildSense API",
    description="Agentic Intelligence Engine for Idea Suggestion, Evaluation, and SMB Workflow Optimization.",
    version="1.0.0",
)

# Configure Allowed Origins for CORS (Next.js default: http://localhost:3000)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# Register CORS Middleware to allow secure cross-origin UI requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint serving basic API status metadata.

    Arguments:
        None

    Returns:
        dict[str, str]: Welcome message and api status.
    """
    return {
        "message": "Welcome to BuildSense API Engine",
        "status": "online",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint to verify backend service liveness.

    Arguments:
        None

    Returns:
        dict[str, str]: A dictionary indicating that the backend service is "ok".
    """
    return {
        "status": "ok",
    }
