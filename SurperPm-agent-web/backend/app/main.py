"""FastAPI app entry for SuperPmAgent-web."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from app.routes import auth as auth_routes
from app.routes import chat as chat_routes
from app.routes import config as config_routes
from app.routes import goal as goal_routes
from app.routes import knowledge as knowledge_routes
from app.routes import secrets as secrets_routes
from app.routes import setup as setup_routes
from app.routes import discussions as discussions_routes
from app.routes import goals as goals_routes
from app.routes import workspaces as workspace_routes
from app.routes import ws as ws_routes
from app.services import goal_runner
from app.services.event_bus import bus
from app.ws import hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    app.state.goal_runner = goal_runner
    app.state.hub = hub
    app.state.bus = bus
    yield


app = FastAPI(
    title="SuperPmAgent-web",
    version="0.1.0",
    description="SuperPmAgent养护室 — 配置 + 澄清 + Goal 控制台",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(setup_routes.router, prefix="/api/setup", tags=["setup"])
app.include_router(config_routes.router, prefix="/api/config", tags=["config"])
app.include_router(knowledge_routes.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(goal_routes.router, prefix="/api/goal", tags=["goal"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["chat"])
app.include_router(workspace_routes.router, prefix="/api/workspaces", tags=["workspaces"])
app.include_router(goals_routes.router, prefix="/api/workspaces/{workspace_id}/goals", tags=["goals"])
app.include_router(discussions_routes.router, prefix="/api/workspaces/{workspace_id}/discussions", tags=["discussions"])
app.include_router(secrets_routes.router, prefix="/api/workspaces/{workspace_id}/secrets", tags=["secrets"])
app.include_router(ws_routes.router)


@app.get("/")
def root() -> dict:
    return {"name": "SuperPmAgent-web", "version": "0.1.0", "status": "ok"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
