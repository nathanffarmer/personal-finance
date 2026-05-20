def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_unauthenticated_even_with_password(monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app.config import Settings, get_settings
    from backend.app.main import create_app

    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(app_password="secret")
    client = TestClient(application)
    response = client.get("/api/health")
    assert response.status_code == 200
