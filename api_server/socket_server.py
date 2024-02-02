import socketio
import uvicorn
from fastapi.responses import StreamingResponse

from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import threading
import cv2
import numpy as np

app_fastapi = FastAPI(debug=True)

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
        print("Received data.")
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
                else:
                    # 映像データがない場合は少し待つ（ここでは0.5秒）
                    time.sleep(0.5)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace;boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app=app_fastapi, host="0.0.0.0", port=8001, log_level="warning")
