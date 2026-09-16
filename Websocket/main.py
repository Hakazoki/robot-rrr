import asyncio
import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from orchestrator import run_game_round, vision_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("[MAIN] Démarrage du service de vision...")
    vision_service.start()
    yield
    # --- SHUTDOWN ---
    print("[MAIN] Arrêt du service de vision...")
    vision_service.stop()


app = FastAPI(lifespan=lifespan)


class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def get_index():
    return FileResponse("static/index.html")


# --- ROUTE DU FLUX VIDÉO DEV MODE (AJOUTÉE) ---
def gen_frames():
    while True:
        frame_bytes = vision_service.get_frame_bytes()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        gen_frames(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# --- WEBSOCKET DU JEU ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "START_ROUND":
                asyncio.create_task(run_game_round(manager))

    except WebSocketDisconnect:
        manager.disconnect(websocket)