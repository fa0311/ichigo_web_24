import socketio
from fastapi import FastAPI
import uvicorn
import cv2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
app_fastapi = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi')
app_socketio = socketio.ASGIApp(sio, other_asgi_app=app_fastapi, socketio_path="/ichigo_websocket")

from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import threading
import cv2
import numpy as np

app_fastapi.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 最後に受け取った画像を保持するための変数
latest_frame = None
frame_lock = threading.Lock()

@app_fastapi.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global latest_frame
    await websocket.accept()
    while True:
        data = await websocket.receive_bytes()
        with frame_lock:
            latest_frame = data

@app_fastapi.get("/image")
async def read_img():
    return templates.TemplateResponse("index.html", {"request": None})

@app_fastapi.get("/video_feed")
async def video_feed():
    global latest_frame

    def gen():
        while True:
            with frame_lock:
                if latest_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n\r\n')
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace;boundary=frame")



@app_fastapi.get("/v1/speech/play")
async def play_request(class_id: int):
    sio.start_background_task(
        sio.emit,
        "play_request", {"class_id": class_id})
    return {"result": "OK", "class_id": class_id}

@sio.event
async def connect(sid, environ):
    print('connect ', sid)

@sio.event
async def disconnect(sid):
    print('disconnect ', sid)

if __name__ == "__main__":
    uvicorn.run(app=app_socketio, host="0.0.0.0", port=8000, log_level="warning")
