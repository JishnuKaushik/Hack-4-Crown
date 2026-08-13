import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  — ensures models are registered on Base.metadata
from app.routers import auth, dashboard, reports
from ai import embeddings as ai_embeddings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    if settings.ai_enabled:
        # Load the CLIP model once at startup (PROJECT_SPEC.md §7.4), not on
        # the first request. A failure here must not crash the app — the
        # AI degradation rule (CLAUDE.md §4) applies at boot too: submissions
        # still work via analyze_image()'s own fallback if the model never
        # loaded.
        try:
            ai_embeddings.warm_up()
        except Exception:
            logger.exception("AI model warm-up failed; falling back per-request")
    yield


app = FastAPI(title="CivicLens API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    db_status = "ok"
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}
