import pytest
from fastapi.testclient import TestClient
from app import app as presence_app  # Import the FastAPI app instance

client = TestClient(presence_app)

def test_update_and_get_presence():
    response = client.post("/presence", json={"user_id": "user1", "node_id": "chat-service-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert data["node_id"] == "chat-service-1"

    response = client.get("/presence/user1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user1"
    assert data["node_id"] == "chat-service-1"

def test_get_presence_not_found():
    response = client.get("/presence/nonexistent")
    assert response.status_code == 404
