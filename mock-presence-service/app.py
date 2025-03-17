import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

# user_presence now relies solely on explicit registration.
user_presence: Dict[str, str] = {}

class PresenceResponse(BaseModel):
    user_id: str
    node_id: str

class PresenceUpdate(BaseModel):
    user_id: str
    node_id: str

@app.post("/presence", response_model=PresenceResponse)
def update_presence(presence_update: PresenceUpdate):
    """
    Registers (or updates) the user's presence.
    """
    user_presence[presence_update.user_id] = presence_update.node_id
    return PresenceResponse(user_id=presence_update.user_id, node_id=presence_update.node_id)

@app.get("/presence/{user_id}", response_model=PresenceResponse)
def get_presence(user_id: str):
    """
    Returns the current node for a given user.
    If the user has not been registered, returns a 404.
    """
    if user_id in user_presence:
        return PresenceResponse(user_id=user_id, node_id=user_presence[user_id])
    else:
        raise HTTPException(status_code=404, detail="User not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
