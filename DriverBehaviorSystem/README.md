# Driver Behavior Intelligence System

A premium, production-ready AI solution that transforms a basic drowsiness detector into a comprehensive intelligent monitoring system.

## 🚀 Features

- **Advanced AI Pipeline**: YOLOv8 Face Detection + MediaPipe Face Mesh (EAR, Gaze tracking, Head Pose Estimation).
- **Temporal Stability**: Non-flickering predictions with a 30-frame rolling buffer and majority voting threshold (60%).
- **Dynamic Risk Score**: Smooth 0-100 risk rating classifying into Safe, Warning, and Critical thresholds.
- **Smart Alert System**: Multi-level alerts including integrated browser TTS warning and optional Twilio SMS fallbacks for critical micro-sleep.
- **Explainable AI Dashboard**: Complete dark-themed glassmorphism interface powered by FastAPI WebSockets, providing live camera overlays, Chart.js trending, and text-based reasoning for exact AI decisions.

## 📂 Architecture

- `/backend/` FastAPI application exposing live AI WebSocket streaming and backend services.
- `/frontend_next/` Dynamic Next.js dashboard intended for modern hosting platforms such as Vercel.
- `/frontend/` Legacy static HTML dashboard. For deployment, use `/frontend_next/` and do not rely on the static `/frontend/` folder.

## 🛠️ Environment Setup

1. Install requirements:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Check your Webcam connection. (OpenCV will use default camera index 0).

3. (Optional) Set Twilio credentials in your terminal for SMS alerts:
   ```bash
   set TWILIO_ACCOUNT_SID=your_sid
   set TWILIO_AUTH_TOKEN=your_token
   ```

## 🚗 Run the System Locally
### Backend
```bash
cd DriverBehaviorSystem/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 10000
```

### Frontend
```bash
cd DriverBehaviorSystem/frontend_next
npm install
npm run dev
```

Then open `http://localhost:3000` in your browser.

### Environment Variable
Create a `.env.local` file in `/frontend_next/` or configure your hosting platform variable:
```env
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

This enables the Next.js frontend to connect to the live FastAPI backend using WebSocket streaming.
