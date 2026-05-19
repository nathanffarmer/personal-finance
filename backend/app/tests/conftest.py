import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings, get_settings
from backend.app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(app_password="")


@pytest.fixture
def app(settings):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
