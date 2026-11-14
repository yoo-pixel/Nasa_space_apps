from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401
from app.seed import seed_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield

app = FastAPI(title="AstroGuard API", description="Astronaut health monitoring research prototype. Statistical findings require human review.", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"name": "AstroGuard API", "docs": "/docs", "health": "/api/v1/health"}
