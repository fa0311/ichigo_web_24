import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app_fastapi = FastAPI()

sio = socketio.AsyncServer(async_mode='asgi', logger=False, engineio_logger=False, cors_allowed_origins="*")
app_socketio = socketio.ASGIApp(sio, other_asgi_app=app_fastapi, socketio_path="/ichigo_websocket")

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


@sio.event
async def final_answer(sid, data):
    '''最終結果配信'''
    sio.start_background_task(
        sio.emit,
        "final_answer", data)


@sio.event
async def change_parameters(sid, data):
    '''パラメータ更新時'''
    sio.start_background_task(
        sio.emit,
        "change_parameters", data)


@sio.event
async def weight_correction(sid, data):
    '''重量センサ補正データ'''
    sio.start_background_task(
        sio.emit,
        "weight_correction", data)

@sio.event
async def system_cmd(sid, data):
    '''システムコマンド配信'''
    sio.start_background_task(
        sio.emit,
        "system_cmd", data)

if __name__ == "__main__":
    uvicorn.run(app=app_socketio, host="0.0.0.0", port=8000, log_level="warning")
