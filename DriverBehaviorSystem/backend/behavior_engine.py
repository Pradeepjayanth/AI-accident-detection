import collections
import time

class BehaviorEngine:
    def __init__(self, buffer_size=30, threshold_ratio=0.60):
        self.buffer_size = buffer_size
        self.threshold_ratio = threshold_ratio
        
        self.raw_states = collections.deque(maxlen=buffer_size)
        self.ear_buffer = collections.deque(maxlen=buffer_size)
        
        self.EAR_THRESHOLD = 0.20 # Closed eye threshold
        self.YAW_THRESHOLD = 20.0
        self.PITCH_THRESHOLD = 20.0
        
        # Tracking duration
        self.state_start_time = time.time()
        self.current_state = "Focused"

    def determine_raw_state(self, metrics):
        if not metrics or metrics.get("ear") == 0:
            return "Unknown"
        
        ear = metrics.get("ear", 0.0)
        gaze = metrics.get("gaze", "Center")
        pitch = metrics.get("pitch", 0.0)
        yaw = metrics.get("yaw", 0.0)
        
        self.ear_buffer.append(ear)
        
        if ear < self.EAR_THRESHOLD:
            return "Drowsy"
        
        if abs(yaw) > self.YAW_THRESHOLD or abs(pitch) > self.PITCH_THRESHOLD or gaze != "Center":
            return "Distracted"
        
        return "Focused"

    def process(self, metrics):
        raw_state = self.determine_raw_state(metrics)
        if raw_state != "Unknown":
            self.raw_states.append(raw_state)
            
        if len(self.raw_states) == 0:
            return {
                "state": "Unknown",
            "immediate_state": raw_state,
                "eye_status": "Unknown",
                "raw_state": raw_state
            }

        # Temporal stability analysis
        count_drowsy = self.raw_states.count("Drowsy")
        count_distracted = self.raw_states.count("Distracted")
        total = len(self.raw_states)
        
        new_state = "Focused"
        if count_drowsy / total > self.threshold_ratio:
            new_state = "Drowsy"
        elif count_distracted / total > self.threshold_ratio:
            new_state = "Distracted"
            
        if new_state != self.current_state:
            self.current_state = new_state
            self.state_start_time = time.time()
            
        duration = time.time() - self.state_start_time
        
        # Basic blink rate estimation
        blinks = sum(1 for e in self.ear_buffer if e < self.EAR_THRESHOLD)
        eye_status = "Closed" if (metrics and metrics.get("ear", 1.0) < self.EAR_THRESHOLD) else "Open"
        
        return {
            "state": self.current_state,
            "immediate_state": raw_state,
            "duration": duration,
            "blink_rate": blinks, # raw blink frames in buffer
            "eye_status": eye_status,
            "raw_state": raw_state
        }
