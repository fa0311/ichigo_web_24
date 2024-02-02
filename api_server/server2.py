from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import threading
import uvicorn
import cv2


app = FastAPI()

lock = threading.Lock()
output_frame = None

def generate_frames():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n\r\n')

@app.get('/')
async def index():
    content = """
    <html>
        <body>
            <img src="/video_feed" alt="Detection Feed">
        </body>
    </html>
    """
    return content

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace;boundary=frame")
    
if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8002, log_level="warning")

