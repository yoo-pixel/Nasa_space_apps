"""FastAPI entry point for the NASA Space Apps research backend scaffold."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.ml_router import registry_for_request, router as ml_router
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
FRONTEND_DIR = (Path(__file__).resolve().parents[2] / "frontend").resolve()
app.mount("/dashboard-assets", StaticFiles(directory=FRONTEND_DIR), name="dashboard-assets")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "NASA Space Apps Astronaut Health Research API",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/v1/health")
def health(request: Request) -> dict:
    registry = registry_for_request(request)
    forecast_models = ("heart", "nerve", "immune", "bone")
    loaded_forecasters = [name for name in forecast_models if registry["status"].get(name, {}).get("loaded")]
    return {
        "status": "ok",
        "readiness": "ready" if len(loaded_forecasters) == len(forecast_models) else "degraded" if loaded_forecasters else "unavailable",
        "forecast_ready": len(loaded_forecasters) == len(forecast_models),
        "service": "astronaut-health-research-api",
        "models_loaded": [name for name, info in registry["status"].items() if info["loaded"]],
        "models": registry["status"],
        "model_data_origin": registry["data_origin"],
        "clinical_use": False,
    }
