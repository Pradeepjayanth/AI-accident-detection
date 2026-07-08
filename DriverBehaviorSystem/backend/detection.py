import cv2
from ultralytics import YOLO
import numpy as np
class FaceDetector:#this project about driver face detection
    def __init__(self, model_path="yolov8n-face.pt"):
        # Attempt to load a YOLO model - user mentioned they want YOLOv8 for face detection
        # Falls back to standard yolov8n if the specific face model is missing.
        try:
            self.model = YOLO(model_path)
            self.is_face_model = ("face" in model_path.lower())
        except:
            self.model = YOLO("yolov8n.pt") 
            self.is_face_model = False

    def detect(self, frame):
        results = self.model.predict(frame, verbose=False, imgsz=320, conf=0.4)
        boxes = []
        for r in results:#
            for box in r.boxes:
                if not self.is_face_model and int(box.cls[0]) != 0:
                    continue # Only keep person class if not specifically a face model
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                boxes.append((x1, y1, x2, y2, conf))
        return boxes
