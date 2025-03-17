import pytest
from fastapi.testclient import TestClient
import json
import time
import app as chat_module  # Import the module, not just the FastAPI instance

client = TestClient(chat_module.app)

# A simple fake response class to simulate requests responses.
class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data

# Fake GET that returns a local presence.
def fake_get_local(url):
    # Extract the user_id from the URL, e.g. ".../presence/userB"
    user_id = url.rstrip("/").split("/")[-1]
    return FakeResponse(200, {"user_id": user_id, "node_id": chat_module.NODE_ID})

# Fake GET that simulates that the recipient is on a different node.
def fake_get_cross(url):
    user_id = url.rstrip("/").split("/")[-1]
    return FakeResponse(200, {"user_id": user_id, "node_id": "chat-service-2"})

# Fake POST that always returns a successful registration.
def fake_post(url, json):
    return FakeResponse(200, json)

def test_local_message_delivery(monkeypatch):
    # Patch GET and POST in the chat_module so that registration and lookup always succeed locally.
    monkeypatch.setattr(chat_module.requests, "get", fake_get_local)
    monkeypatch.setattr(chat_module.requests, "post", fake_post)

    with client.websocket_connect("/ws/user/userA") as ws_a:
        with client.websocket_connect("/ws/user/userB") as ws_b:
            message = {"recipient_id": "userB", "message": "Hello, UserB!"}
            ws_a.send_text(json.dumps(message))
            data = ws_b.receive_text()
            received = json.loads(data)
            assert received["sender"] == "userA"
            assert received["message"] == "Hello, UserB!"

def test_cross_node_forwarding(monkeypatch):
    # Patch GET and POST in the chat_module so that the recipient appears to be on a different node.
    monkeypatch.setattr(chat_module.requests, "get", fake_get_cross)
    monkeypatch.setattr(chat_module.requests, "post", fake_post)

    forwarded_messages = []
    class FakeWS:
        async def send(self, message):
            forwarded_messages.append(message)
    # Inject the fake node2node websocket connection.
    chat_module.node2node_ws = FakeWS()

    with client.websocket_connect("/ws/user/userA") as ws_a:
        message = {"recipient_id": "userB", "message": "Hello from A to B cross-node"}
        ws_a.send_text(json.dumps(message))
        time.sleep(0.1)  # Give time for the async operation
        assert len(forwarded_messages) == 1
        forwarded = json.loads(forwarded_messages[0])
        assert forwarded["target_node"] == "chat-service-2"
        assert forwarded["message"]["sender"] == "userA"
