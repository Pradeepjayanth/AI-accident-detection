class RiskEngine:
    def __init__(self):
        pass

    def compute_risk(self, behavior_data, metrics):
        if not metrics or behavior_data["state"] == "Unknown":
            return {"score": 0, "level": "Safe", "reason": "No face detected"}

        score = 0
        state = behavior_data.get("state", "Focused")
        duration = behavior_data.get("duration", 0)
        
        ear = metrics.get("ear", 0.3)
        yaw = abs(metrics.get("yaw", 0))
        pitch = abs(metrics.get("pitch", 0))
        
        # Base score from state and duration
        if state == "Drowsy":
            score += 50
            score += min(duration * 10, 40) # Add up to 40 for sustained drowsiness
        elif state == "Distracted":
            score += 30
            score += min(duration * 5, 30) # Add up to 30 for sustained distraction
        else:
            score += max(0, 5 - duration)
            
        # Additional scoring based on instantaneous severity
        if ear < 0.2:
            score += 10
        if yaw > 30 or pitch > 30:
            score += 15
            
        score = min(max(int(score), 0), 100)
        
        level = "Safe"
        if score >= 60:
            level = "Critical"
        elif score >= 30:
            level = "Warning"
            
        # Explainable AI Text
        reasons = []
        if state == "Drowsy": reasons.append(f"Eyes closed for {duration:.1f}s")
        if state == "Distracted": reasons.append(f"Looking away for {duration:.1f}s")
        if yaw > 20: reasons.append(f"Head turned sideways ({yaw:.0f} deg)")
        if pitch > 20: reasons.append(f"Head pitched ({pitch:.0f} deg)")
        
        # Micro sleep pattern
        if score > 80 and state == "Drowsy":
            reasons.append("Micro-sleep detected!")
            
        if not reasons:
            reasons.append("Driver is focused")
            
        return {
            "score": score,
            "level": level,
            "reason": " | ".join(reasons)
        }
