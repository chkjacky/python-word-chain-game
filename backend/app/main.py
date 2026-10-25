from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import game, stats
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Word Chain Game",
    description="AI Game",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(game.router)
app.include_router(stats.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def _mask(secret: str) -> str | None:
    if not secret:
        return None
    if len(secret) <= 11:
        return "***"
    return f"{secret[:7]}...{secret[-4:]}"


@app.get("/debug/config")
async def debug_config():
    return {
        "OPENAI_API_KEY_set": bool(settings.OPENAI_API_KEY),
        "OPENAI_API_KEY_preview": _mask(settings.OPENAI_API_KEY),
        "OPENAI_MODEL": settings.OPENAI_MODEL,
        "DATABASE_URL": settings.DATABASE_URL,
        "TRACE_LOG_PATH": settings.TRACE_LOG_PATH,
        "MAX_LLM_RETRIES": settings.MAX_LLM_RETRIES,
        "MAX_NO_S_RETRIES": settings.MAX_NO_S_RETRIES,
    }
