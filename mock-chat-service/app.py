import os
import requests
import asyncio
import json
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from typing import Dict

connected_users: Dict[str, WebSocket] = {}
node2node_ws = None

NODE_ID = os.getenv("NODE_ID", "chat-service-0")
PRESENCE_SERVICE_URL = os.getenv("PRESENCE_SERVICE_URL", "http://mock-presence-service:8004")
# NODE2NODE_URL now points to the Nginx load balancer.
NODE2NODE_URL = os.getenv("NODE2NODE_URL", "ws://mock-node2node-lb:8080/node")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(
        node2node_loop()
    )  # Start background WebSocket handling
    yield  # Wait for app shutdown


app = FastAPI(
    lifespan=lifespan
)  # Use lifespan instead of `@app.on_event("startup")`


async def node2node_loop():
    """
    Maintain a persistent connection to node2node-service,
    automatically reconnecting on failures, and reading incoming messages for local delivery.
    """
    global node2node_ws
    while True:
        try:
            connect_url = f"{NODE2NODE_URL}?node_id={NODE_ID}"
            node2node_ws = await websockets.connect(connect_url)
            print(f"[{NODE_ID}] Connected to node2node-service at {connect_url}.")

            while True:
                raw_msg = await node2node_ws.recv()
                msg_data = json.loads(raw_msg)
                source_node = msg_data.get("source_node")
                payload = msg_data.get("message", {})
                recipient_id = payload.get("recipient_id")
                print(f"[{NODE_ID}] Received message from {source_node}: {payload}")

                # Deliver to local WebSocket if connected.
                if recipient_id in connected_users:
                    await connected_users[recipient_id].send_text(json.dumps({
                        "sender": payload.get("sender"),
                        "message": payload.get("message"),
                    }))
                    print(f"[{NODE_ID}] Delivered message to {recipient_id}")
                else:
                    print(f"[{NODE_ID}] User {recipient_id} not connected locally.")
        except Exception as e:
            print(f"[{NODE_ID}] Lost connection to node2node-service: {e}, retry in 5s...")
            await asyncio.sleep(5)

@app.websocket("/ws/user/{user_id}")
async def websocket_user(websocket: WebSocket, user_id: str):
    """
    Accepts a user's WebSocket connection, registers them locally, and
    updates their presence via the presence service.
    Then routes messages either locally or via node2node-service.
    """
    await websocket.accept()
    connected_users[user_id] = websocket
    print(f"[{NODE_ID}] User {user_id} connected.")

    # Register the user's presence on this node.
    try:
        resp = requests.post(
            f"{PRESENCE_SERVICE_URL}/presence",
            json={"user_id": user_id, "node_id": NODE_ID}
        )
        if resp.status_code == 200:
            print(f"[{NODE_ID}] Registered presence for user {user_id} on {NODE_ID}")
        else:
            print(f"[{NODE_ID}] Failed to register presence for user {user_id}: {resp.text}")
    except Exception as e:
        print(f"[{NODE_ID}] Exception during presence registration for {user_id}: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            recipient_id = message_data.get("recipient_id")
            message_body = message_data.get("message")

            # Look up recipient presence.
            resp = requests.get(f"{PRESENCE_SERVICE_URL}/presence/{recipient_id}")
            if resp.status_code != 200:
                print(f"[{NODE_ID}] Presence lookup failed for {recipient_id}: {resp.text}")
                continue

            presence = resp.json()
            recipient_node = presence.get("node_id")
            if not recipient_node:
                print(f"[{NODE_ID}] Received invalid presence data for {recipient_id}: {presence}")
                continue

            print(f"[{NODE_ID}] Presence says {recipient_id} is on {recipient_node}")

            if recipient_node == NODE_ID:
                # Deliver directly if the recipient is on this node.
                if recipient_id in connected_users:
                    await connected_users[recipient_id].send_text(json.dumps({
                        "sender": user_id,
                        "message": message_body,
                    }))
                else:
                    print(f"[{NODE_ID}] Recipient {recipient_id} not connected locally.")
            else:
                # Forward the message via node2node-service.
                if node2node_ws is not None:
                    msg_to_send = json.dumps({
                        "target_node": recipient_node,
                        "message": {
                            "recipient_id": recipient_id,
                            "sender": user_id,
                            "message": message_body
                        },
                    })
                    print(f"[{NODE_ID}] Forwarding via node2node-service: {msg_to_send}")
                    await node2node_ws.send(msg_to_send)
                else:
                    print(f"[{NODE_ID}] ERROR: node2node_ws is None; cannot forward.")
    except Exception as e:
        print(f"[{NODE_ID}] Exception in websocket_user: {e}")
    finally:
        connected_users.pop(user_id, None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
