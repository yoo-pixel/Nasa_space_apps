"""FastAPI entry point for the NASA Space Apps research backend scaffold."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.ml_router import router as ml_router
from ml.serving import load_model_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Missing or unreadable artifacts are reported in health/model-info and do
    # not prevent the rest of the API from starting.
    app.state.ml_registry = load_model_registry()
    yield


app = FastAPI(
    title="NASA Space Apps Astronaut Health Research API",
    description=(
        "Research prototype with synthetic-only ML demonstrations. Model output is not a medical estimate, "
        "diagnosis, treatment recommendation, or NASA-certified capability."
    ),
    version="0.2.0",
    lifespan=lifespan,
)
app.include_router(ml_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "NASA Space Apps Astronaut Health Research API", "docs": "/docs", "health": "/api/v1/health"}


@app.get("/api/v1/health")
def health(request: Request) -> dict:
    registry = request.app.state.ml_registry
    return {
        "status": "ok",
        "service": "astronaut-health-research-api",
        "models_loaded": [name for name, info in registry["status"].items() if info["loaded"]],
        "models": registry["status"],
        "model_data_origin": registry["data_origin"],
        "clinical_use": False,
    }
