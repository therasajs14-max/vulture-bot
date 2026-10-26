"""Vulture Bot - Main FastAPI Application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.session import init_db, close_db
from app.api import auth, conversations, chat, files, datasets, email, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    await init_db()
    yield
    # Shutdown: clean up DB connections
    await close_db()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Multi-Purpose AI Assistant with File Intelligence and Admin-Approved Email Automation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(files.router)
app.include_router(datasets.router)
app.include_router(email.router)
app.include_router(system.router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )
