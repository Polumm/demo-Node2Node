import pytest
from fastapi.testclient import TestClient
import json
from app import app as node2node_app  # Import the FastAPI app instance

client = TestClient(node2node_app)

def test_node_to_node_forwarding():
    with client.websocket_connect("/node?node_id=node1") as ws1:
        with client.websocket_connect("/node?node_id=node2") as ws2:
            message = {
                "target_node": "node2",
                "message": {
                    "recipient_id": "user2",
                    "sender": "user1",
                    "message": "Hello"
                }
            }
            ws1.send_text(json.dumps(message))
            data = ws2.receive_text()
            forwarded = json.loads(data)
            assert forwarded["source_node"] == "node1"
            assert forwarded["message"]["message"] == "Hello"
