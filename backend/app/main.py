"""Main FastAPI application."""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.routes import router

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Initialize database
db.init_db()

# Create FastAPI app
app = FastAPI(
    title="UGC Review Mining Agent API",
    description="API for analyzing product reviews from CSV files",
    version="1.0.0"
)

# CORS configuration
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "UGC Review Mining Agent API",
        "version": "1.0.0",
        "status": "running"
    }
