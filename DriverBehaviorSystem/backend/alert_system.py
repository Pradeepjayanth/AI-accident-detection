import time
from twilio.rest import Client
import os

class AlertSystem:
    def __init__(self):
        self.cooldowns = {
            "Level 1": 0,
            "Level 2": 0,
            "Level 3": 0
        }
        self.cooldown_durations = {
            "Level 1": 5,   # 5 seconds
            "Level 2": 15,  # 15 seconds
            "Level 3": 60   # 60 seconds
        }
        
        # Twilio Setup (Optional/Environment variables)
        self.twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "your_account_sid")
        self.twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", "your_auth_token")
        self.twilio_from = os.environ.get("TWILIO_FROM_NUMBER", "+1234567890")
        self.twilio_to = os.environ.get("TWILIO_TO_NUMBER", "+0987654321")
        
        self.use_twilio = self.twilio_sid != "your_account_sid"
        if self.use_twilio:
            try:
                self.client = Client(self.twilio_sid, self.twilio_token)
            except Exception as e:
                self.use_twilio = False

    def can_trigger(self, level):
        current_time = time.time()
        if current_time - self.cooldowns[level] > self.cooldown_durations[level]:
            return True
        return False

    def trigger(self, level, message):
        self.cooldowns[level] = time.time()
        
        if level == "Level 3" and self.use_twilio:
            try:
                msg = self.client.messages.create(
                    body=f"URGENT: Driver Behavior Alert - {message}",
                    from_=self.twilio_from,
                    to=self.twilio_to
                )
                print(f"Twilio SMS sent: {msg.sid}")
            except Exception as e:
                print(f"Twilio error: {e}")

    def process(self, risk_data):
        level = risk_data.get("level", "Safe")
        score = risk_data.get("score", 0)
        reasons = risk_data.get("reason", "")
        
        alerts = []
        if level == "Warning":
            if self.can_trigger("Level 1"):
                self.trigger("Level 1", "Visual warning")
                alerts.append({"severity": "warning", "message": "Stay focused on the road.", "type": "visual"})
        elif level == "Critical":
            if self.can_trigger("Level 2"):
                self.trigger("Level 2", "Voice alert")
                alerts.append({"severity": "critical", "message": "WAKE UP!", "type": "voice"})
                
            if score > 85 and self.can_trigger("Level 3"):
                self.trigger("Level 3", reasons)
                alerts.append({"severity": "emergency", "message": f"SMS Alert Sent: {reasons}", "type": "sms"})
                
        return alerts
