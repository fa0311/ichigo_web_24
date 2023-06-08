import socketio
from fastapi import FastAPI
import uvicorn

app_fastapi = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi')
app_socketio = socketio.ASGIApp(sio, other_asgi_app=app_fastapi, socketio_path="/ichigo_websocket")


@app_fastapi.get("/v1/speech/play")
async def play_request(class_id: int):
    """指定されたsidにemitするエンドポイント
    """
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
