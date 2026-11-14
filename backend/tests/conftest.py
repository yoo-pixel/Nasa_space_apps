import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.router import api_router
from app.db.base import Base
from app.db.dependencies import get_db
from app.models import Astronaut, MetricBaseline, Mission


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        mission = Mission(name="Test mission", status="active", destination="LEO", description="test")
        db.add(mission)
        db.flush()
        astronaut = Astronaut(mission_id=mission.id, full_name="Test Astronaut", callsign="TEST", role="Pilot", monitoring_status="stable")
        db.add(astronaut)
        db.flush()
        db.add(MetricBaseline(
            astronaut_id=astronaut.id, metric="heart_rate", unit="bpm", median=60,
            lower_bound=45, upper_bound=75, sample_count=24, method="test baseline",
        ))
        db.commit()
        astronaut_id = str(astronaut.id)
        mission_id = str(mission.id)

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.astronaut_id = astronaut_id
        test_client.mission_id = mission_id
        test_client.test_db_factory = TestingSession
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
