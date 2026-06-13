"""FastAPI app entry for SuperPmAgent-web."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth as auth_routes
from app.routes import chat as chat_routes
from app.routes import config as config_routes
from app.routes import goal as goal_routes
from app.routes import knowledge as knowledge_routes
from app.routes import setup as setup_routes
from app.services import goal_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.goal_runner = goal_runner
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


@app.get("/")
def root() -> dict:
    return {"name": "SuperPmAgent-web", "version": "0.1.0", "status": "ok"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
