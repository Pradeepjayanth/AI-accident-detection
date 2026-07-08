import asyncio
import cv2
import base64
import json
import uvicorn
import torch
import numpy as np
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Security Patch for PyTorch >= 2.4 (prevents weight loading error)
original_load = torch.load
def patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from detection import FaceDetector
from eye_tracking import EyeTracker
from behavior_engine import BehaviorEngine
from risk_engine import RiskEngine
from alert_system import AlertSystem

app = FastAPI(title="Driver Behavior Intelligence System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate Modules
face_detector = FaceDetector()
eye_tracker = EyeTracker()
behavior_engine = BehaviorEngine()
risk_engine = RiskEngine()
alert_system = AlertSystem()

# Optional legacy static frontend mount (use /frontend_next for modern deploys)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Driver Behavior Intelligence API is running. Use /ws/stream for live stream access."
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Driver Behavior Intelligence Backend"}

class FramePayload(BaseModel):
    image: str

@app.post("/analyze")
async def analyze_frame(payload: FramePayload):
    try:
        image_data = payload.image
        if image_data.startswith("data:image"):
            image_data = image_data.split(",", 1)[1]

        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Invalid image data")

        frame = cv2.resize(frame, (640, 480))
        face_boxes = face_detector.detect(frame)
        metrics = eye_tracker.process(frame)
        behavior_data = behavior_engine.process(metrics)
        risk_data = risk_engine.compute_risk(behavior_data, metrics)
        alerts = alert_system.process(risk_data)
        display_frame = _draw_overlay(frame.copy(), face_boxes, metrics, behavior_data, risk_data)

        _, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "frame": frame_base64,
            "metrics": {
                "ear": round(metrics.get('ear', 0), 3),
                "gaze": metrics.get('gaze', 'Center'),
                "pitch": round(metrics.get('pitch', 0), 1),
                "yaw": round(metrics.get('yaw', 0), 1)
            },
            "behavior": behavior_data,
            "risk": risk_data,
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def _draw_overlay(frame, face_boxes, metrics, behavior_data, risk_data):
    # Draw face box
    for (x1, y1, x2, y2, conf) in face_boxes:
        color = (0, 255, 0)
        if risk_data["level"] == "Warning": color = (0, 165, 255)
        elif risk_data["level"] == "Critical": color = (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, "Driver", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Draw Landmarks
    if metrics and "landmarks" in metrics:
        for pt in metrics["landmarks"]:
            cv2.circle(frame, pt, 1, (255, 255, 0), -1)

    # Info overlay
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
    
    status_text = f"State: {behavior_data['state']} | Risk: {risk_data['score']}% ({risk_data['level']})"
    text_color = (0, 255, 0)
    if risk_data["level"] == "Warning": text_color = (0, 255, 255)
    elif risk_data["level"] == "Critical": text_color = (0, 0, 255)
    
    cv2.putText(frame, status_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
    return frame


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    cap = cv2.VideoCapture(0)
    # Target FPS ~ 15-20 for processing to balance load
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.1)
                continue
                
            frame = cv2.resize(frame, (640, 480))
            
            # Sub-module processing
            face_boxes = face_detector.detect(frame)
            metrics = eye_tracker.process(frame)
            behavior_data = behavior_engine.process(metrics)
            risk_data = risk_engine.compute_risk(behavior_data, metrics)
            alerts = alert_system.process(risk_data)
            
            # Combine UI
            display_frame = _draw_overlay(frame.copy(), face_boxes, metrics, behavior_data, risk_data)
            
            # Encode frame
            _, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "frame": frame_base64,
                "metrics": {
                    "ear": round(metrics.get('ear', 0), 3),
                    "gaze": metrics.get('gaze', 'Center'),
                    "pitch": round(metrics.get('pitch', 0), 1),
                    "yaw": round(metrics.get('yaw', 0), 1)
                },
                "behavior": behavior_data,
                "risk": risk_data,
                "alerts": alerts
            }
            
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.03) # Yield loop

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in stream: {e}")
    finally:
        cap.release()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
