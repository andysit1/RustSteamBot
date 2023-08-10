from fastapi import FastAPI, WebSocket, WebSocketDisconnect

#This file will deal with data dealing between websockets ie keeping track of rooms, making rooms, and alerting
#other players games are ready for them to play

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        if websocket in self.active_connections:
            await websocket.send_text(message)

    async def send_personal_json_room(self, message: str, websocket: WebSocket):
        if message:
            await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

    async def broadcastJSON(self, message:str):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

