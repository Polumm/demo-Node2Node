import os
import requests
import asyncio
import json

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict

connected_users: Dict[str, WebSocket] = {}
node2node_ws = None

NODE_ID = os.getenv("NODE_ID", "chat-service-0")
PRESENCE_SERVICE_URL = os.getenv("PRESENCE_SERVICE_URL", "http://presence-service:8004")
NODE2NODE_URL = os.getenv("NODE2NODE_URL", "ws://node2node-service:8080/node")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Spawn a background task to maintain connection to node2node-service
    asyncio.create_task(node2node_loop())

async def node2node_loop():
    """
    Keep a persistent connection to node2node-service, automatically reconnecting
    on failures, and read incoming messages for local delivery.
    """
    global node2node_ws
    while True:
        try:
            # Pass the node ID as a query parameter, e.g. ?node_id=chat-service-1
            connect_url = f"{NODE2NODE_URL}?node_id={NODE_ID}"
            node2node_ws = await websockets.connect(connect_url)
            print(f"[{NODE_ID}] Connected to node2node-service at {connect_url}.")

            # Continuously read incoming node2node messages
            while True:
                raw_msg = await node2node_ws.recv()  # from websockets library
                msg_data = json.loads(raw_msg)
                source_node = msg_data.get("source_node")
                payload = msg_data.get("message", {})
                recipient_id = payload.get("recipient_id")

                print(f"[{NODE_ID}] Received message from {source_node}: {payload}")

                # Deliver to local WebSocket if that user is connected
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
    Accepts user’s WebSocket connection, registers them,
    and either delivers messages locally or forwards them via node2node-service.
    """
    await websocket.accept()
    connected_users[user_id] = websocket
    print(f"[{NODE_ID}] User {user_id} connected.")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            recipient_id = message_data.get("recipient_id")
            message_body = message_data.get("message")

            # Query presence to find which node the recipient is on
            resp = requests.get(f"{PRESENCE_SERVICE_URL}/presence/{recipient_id}")
            presence = resp.json()  # e.g. {"user_id": "user456", "node_id": "chat-service-2"}
            recipient_node = presence["node_id"]
            print(f"[{NODE_ID}] presence says {recipient_id} is on {recipient_node}")

            # If recipient is on the same node, deliver directly
            if recipient_node == NODE_ID:
                if recipient_id in connected_users:
                    await connected_users[recipient_id].send_text(json.dumps({
                        "sender": user_id,
                        "message": message_body,
                    }))
                else:
                    print(f"[{NODE_ID}] Recipient {recipient_id} not connected locally.")
            else:
                # Forward message to node2node-service for the correct node
                if node2node_ws is not None:
                    msg_to_send = json.dumps({
                        "target_node": recipient_node,
                        "message": {
                            "recipient_id": recipient_id,
                            "sender": user_id,
                            "message": message_body
                        },
                    })
                    print(f"[{NODE_ID}] Forwarding to node2node-service: {msg_to_send}")
                    await node2node_ws.send(msg_to_send)  # must use send(), not send_text()
                else:
                    print(f"[{NODE_ID}] ERROR: node2node_ws is None; cannot forward.")

    except WebSocketDisconnect:
        print(f"[{NODE_ID}] User {user_id} disconnected.")
    finally:
        connected_users.pop(user_id, None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
