import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import json

app = FastAPI()

# Mapping of node_id -> WebSocket connection.
connections: Dict[str, WebSocket] = {}

@app.websocket("/node")
async def node_ws(websocket: WebSocket):
    """
    Chat-service nodes connect here with a query parameter (e.g. ?node_id=chat-service-1).
    """
    node_id = websocket.query_params.get("node_id", "unknown")
    await websocket.accept()
    connections[node_id] = websocket
    print(f"Node {node_id} connected to node2node-service.")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            target_node = msg.get("target_node")
            payload = msg.get("message")
            print(f"Node2Node received message for {target_node}: {payload}")
            if target_node in connections:
                print(f"Forwarding message to {target_node}")
                await connections[target_node].send_text(json.dumps({
                    "source_node": node_id,
                    "message": payload
                }))
            else:
                print(f"ERROR: No connection for node {target_node}")
    except WebSocketDisconnect:
        print(f"Node {node_id} disconnected.")
        connections.pop(node_id, None)

@app.get("/")
def health():
    return {"status": "node2node-service OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
