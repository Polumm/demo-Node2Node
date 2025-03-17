import os
import random
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

# Read from environment, e.g. "chat-service-1,chat-service-2"
REPLICAS = os.getenv("REPLICAS", "chat-service-1,chat-service-2").split(",")

# user_presence keeps track of which node each user is assigned to
user_presence: Dict[str, str] = {}

class PresenceResponse(BaseModel):
    user_id: str
    node_id: str

@app.get("/presence/{user_id}", response_model=PresenceResponse)
def get_user_presence(user_id: str):
    """
    If user_id not previously seen, assign a random node from REPLICAS.
    Otherwise, return the stored node.
    """
    if user_id not in user_presence:
        user_presence[user_id] = random.choice(REPLICAS)
    return PresenceResponse(user_id=user_id, node_id=user_presence[user_id])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
