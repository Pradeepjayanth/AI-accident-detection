import cv2
import mediapipe as mp
import numpy as np
import math

class EyeTracker:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # Detailed Landmarks indices
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
    def _euclidean_distance(self, p1, p2):
        return math.dist([p1.x, p1.y], [p2.x, p2.y])

    def calculate_ear(self, landmarks, eye_indices):
        p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_indices]
        p2_p6 = self._euclidean_distance(p2, p6)
        p3_p5 = self._euclidean_distance(p3, p5)
        p1_p4 = self._euclidean_distance(p1, p4)
        if p1_p4 == 0: return 0
        return (p2_p6 + p3_p5) / (2.0 * p1_p4)

    def estimate_gaze(self, landmarks, ih, iw):
        left_eye_center = np.mean([[landmarks[i].x, landmarks[i].y] for i in self.LEFT_EYE], axis=0)
        right_eye_center = np.mean([[landmarks[i].x, landmarks[i].y] for i in self.RIGHT_EYE], axis=0)
        left_iris_center = np.mean([[landmarks[i].x, landmarks[i].y] for i in self.LEFT_IRIS], axis=0)
        right_iris_center = np.mean([[landmarks[i].x, landmarks[i].y] for i in self.RIGHT_IRIS], axis=0)
        
        # Horizontal / Vertical ratio offset
        gaze_ratio_x = ((left_iris_center[0] - left_eye_center[0]) + (right_iris_center[0] - right_eye_center[0])) / 2
        gaze_ratio_y = ((left_iris_center[1] - left_eye_center[1]) + (right_iris_center[1] - right_eye_center[1])) / 2
        
        threshold_x = 0.006 
        threshold_y = 0.008
        
        gaze_x = "Center"
        if gaze_ratio_x > threshold_x: gaze_x = "Right"
        elif gaze_ratio_x < -threshold_x: gaze_x = "Left"

        gaze_y = ""
        if gaze_ratio_y > threshold_y: gaze_y = "Down "
        elif gaze_ratio_y < -threshold_y: gaze_y = "Up "
        
        return f"{gaze_y}{gaze_x}".strip(), (gaze_ratio_x, gaze_ratio_y)

    def estimate_head_pose(self, landmarks, ih, iw):
        # 3D points
        face_3d = []
        face_2d = []
        for idx in [1, 33, 263, 61, 291, 199]:
            lm = landmarks[idx]
            x, y = int(lm.x * iw), int(lm.y * ih)
            face_2d.append([x, y])
            face_3d.append([x, y, lm.z])
        
        face_2d = np.array(face_2d, dtype=np.float64)
        face_3d = np.array(face_3d, dtype=np.float64)

        focal_length = 1 * iw
        cam_matrix = np.array([[focal_length, 0, iw / 2], [0, focal_length, ih / 2], [0, 0, 1]])
        dist_matrix = np.zeros((4, 1), dtype=np.float64)

        success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)
        rmat, jac = cv2.Rodrigues(rot_vec)
        angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

        pitch = angles[0] * 360
        yaw = angles[1] * 360
        roll = angles[2] * 360
        return pitch, yaw, roll

    def process(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        ih, iw, _ = frame.shape
        metrics = {
            "ear": 0.0,
            "gaze": "Center",
            "gaze_dev_x": 0.0,
            "gaze_dev_y": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0,
            "landmarks": []
        }
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            metrics["landmarks"] = [(int(pt.x * iw), int(pt.y * ih)) for pt in landmarks]
            
            left_ear = self.calculate_ear(landmarks, self.LEFT_EYE)
            right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE)
            metrics["ear"] = (left_ear + right_ear) / 2.0
            
            metrics["gaze"], (gx, gy) = self.estimate_gaze(landmarks, ih, iw)
            metrics["gaze_dev_x"] = gx
            metrics["gaze_dev_y"] = gy
            
            p, y, r = self.estimate_head_pose(landmarks, ih, iw)
            metrics["pitch"] = p
            metrics["yaw"] = y
            metrics["roll"] = r

        return metrics
