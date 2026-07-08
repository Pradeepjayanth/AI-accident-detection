"use client";

import React, { useEffect, useRef, useState } from 'react';
import Chart, { ChartConfiguration } from 'chart.js/auto';

interface Alert {
  severity: 'info' | 'warning' | 'critical' | 'emergency';
  message: string;
  time: string;
}

export default function Home() {
  const [driverState, setDriverState] = useState('Focused');
  const [eyeStatus, setEyeStatus] = useState('Open');
  const [gaze, setGaze] = useState('Center');
  const [headPose, setHeadPose] = useState('0° / 0°');
  const [riskScore, setRiskScore] = useState(0);
  const [riskLevel, setRiskLevel] = useState('Safe');
  const [reason, setReason] = useState('Analyzing driver state...');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isClient, setIsClient] = useState(false);

  const videoRef = useRef<HTMLImageElement>(null);
  const hiddenVideoRef = useRef<HTMLVideoElement>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const intervalIdRef = useRef<any>(null);
  
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraStatus, setCameraStatus] = useState('Waiting for camera permission...');
  const maxPoints = 30;

  // Handle Hydration
  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;

    // Initialize Chart
    if (chartRef.current) {
      const ctx = chartRef.current.getContext('2d');
      if (ctx) {
        const config: ChartConfiguration = {
          type: 'line',
          data: {
            labels: Array(maxPoints).fill(''),
            datasets: [{
              label: 'Risk Score %',
              data: Array(maxPoints).fill(0),
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: { min: 0, max: 100, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#94a3b8' } },
              x: { display: false }
            },
            plugins: { legend: { display: false } },
            animation: { duration: 0 }
          }
        };
        chartInstance.current = new Chart(ctx, config);
      }
    }

    startCamera();

    return () => {
      if (intervalIdRef.current) clearInterval(intervalIdRef.current);
      if (hiddenVideoRef.current && hiddenVideoRef.current.srcObject) {
        const streams = (hiddenVideoRef.current.srcObject as MediaStream);
        streams.getTracks().forEach((track) => track.stop());
      }
      if (chartInstance.current) chartInstance.current.destroy();
    };
  }, [isClient]);

  const startCamera = async () => {
    const videoElement = hiddenVideoRef.current;
    const captureCanvas = captureCanvasRef.current;
    let isSending = false;
    const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000').replace(/\/$/, '');

    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError('Camera API not supported by this browser.');
      setCameraStatus('Camera unsupported');
      return;
    }

    try {
      setCameraStatus('Requesting camera access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false,
      });

      if (!videoElement) return;
      videoElement.srcObject = stream;
      videoElement.autoplay = true;
      videoElement.muted = true;
      videoElement.playsInline = true;
      videoElement.onloadedmetadata = () => videoElement.play();
      
      setCameraError(null);
      setCameraStatus('Camera connected');
      setIsConnected(true);

      intervalIdRef.current = setInterval(async () => {
        if (isSending || !captureCanvas || !videoElement || videoElement.readyState < 2) return;
        const ctx = captureCanvas.getContext('2d');
        if (!ctx) return;

        ctx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
        const imageData = captureCanvas.toDataURL('image/jpeg', 0.7);
        isSending = true;

        try {
          const response = await fetch(`${backendUrl}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData }),
          });

          if (!response.ok) {
            setIsConnected(false);
            const errorText = await response.text();
            throw new Error(errorText || 'Backend error');
          }

          const data = await response.json();
          if (data.frame && videoRef.current) {
            videoRef.current.src = `data:image/jpeg;base64,${data.frame}`;
          }

          const instantState = data.behavior?.raw_state && data.behavior?.raw_state !== 'Unknown'
            ? data.behavior.raw_state
            : data.behavior?.state || 'Unknown';

          setDriverState(instantState);
          setEyeStatus(data.behavior?.eye_status || 'Unknown');
          setGaze(data.metrics?.gaze || 'Center');
          setHeadPose(`${data.metrics?.pitch || 0}° / ${data.metrics?.yaw || 0}°`);
          setRiskScore(data.risk?.score || 0);
          setRiskLevel(data.risk?.level || 'Safe');
          setReason(data.risk?.reason || 'Sufficient data not available.');

          if (chartInstance.current) {
            const chartData = chartInstance.current.data.datasets[0].data;
            chartData.push(data.risk?.score || 0);
            if (chartData.length > maxPoints) chartData.shift();

            const score = data.risk?.score || 0;
            let color = '#10b981';
            let bgColor = 'rgba(16, 185, 129, 0.1)';
            if (score >= 60) { color = '#ef4444'; bgColor = 'rgba(239, 68, 68, 0.1)'; }
            else if (score >= 30) { color = '#f59e0b'; bgColor = 'rgba(245, 158, 11, 0.1)'; }

            chartInstance.current.data.datasets[0].borderColor = color;
            chartInstance.current.data.datasets[0].backgroundColor = bgColor;
            chartInstance.current.update();
          }

          if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach((alert: any) => {
              const newAlert: Alert = {
                severity: alert.severity,
                message: alert.message,
                time: new Date().toLocaleTimeString()
              };
              setAlerts(prev => [newAlert, ...prev].slice(0, 20));

              if (alert.severity === 'critical' || alert.severity === 'emergency') {
                if ('speechSynthesis' in window) {
                  const utterance = new SpeechSynthesisUtterance(alert.message);
                  window.speechSynthesis.speak(utterance);
                }
              }
            });
          }
          setIsConnected(true);
        } catch (error: any) {
          console.error("Backend error:", error);
          setIsConnected(false);
        } finally {
          isSending = false;
        }
      }, 300);
    } catch (error: any) {
      console.error("Camera error:", error);
      setCameraError(error?.message || 'Camera access denied.');
      setCameraStatus('Camera error');
      setIsConnected(false);
    }
  };

  if (!isClient) return <div className="bg-[#020617] min-h-screen" />;

  return (
    <div className="max-w-[1600px] mx-auto p-5 flex flex-col gap-5">
      <header className="glass-panel flex justify-between items-center px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="pulse-dot"></div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Driver Behavior Intelligence
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <span className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          {isConnected ? 'System Active' : 'System Offline (Reconnect to Backend)'}
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-5">
        <section className="glass-panel p-5 flex flex-col gap-4">
          <div className="flex justify-between items-center">
             <h2 className="text-xl font-semibold">Live Monitor</h2>
          </div>
          <div className="relative w-full aspect-[4/3] bg-black rounded-xl overflow-hidden border border-white/10 group">
             <img ref={videoRef} src="" alt="Live detection feed" className={`w-full h-full object-cover ${isConnected ? 'block' : 'hidden'}`} />
             <video ref={hiddenVideoRef} className="hidden" playsInline muted />
             <canvas ref={captureCanvasRef} width={640} height={480} className="hidden" />
             {!isConnected && (
               <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50 text-slate-400 text-lg text-center p-4 gap-2">
                 <span>{cameraStatus}</span>
                 {cameraError && <span className="text-sm text-red-400">{cameraError}</span>}
                 <button
                   onClick={() => startCamera()}
                   className="mt-3 inline-flex rounded-lg border border-white/20 bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
                 >
                   Retry Connection
                 </button>
               </div>
             )}
          </div>
          <div className="bg-black/20 p-4 rounded-xl border-l-4 border-blue-500">
             <h3 className="text-base font-semibold mb-2 flex items-center gap-2">
               Explainable AI <span className="bg-blue-500 text-white px-2 py-0.5 rounded text-[10px] uppercase font-bold">Live</span>
             </h3>
             <p className="text-slate-400 text-sm leading-relaxed">{reason}</p>
          </div>
        </section>

        <section className="flex flex-col gap-5">
          <div className="grid grid-cols-2 gap-4">
            <MetricCard label="Driver State" value={driverState} color={getStateColor(driverState)} />
            <MetricCard label="Eye Status" value={eyeStatus} color={eyeStatus === 'Closed' ? 'text-red-500' : 'text-white'} />
            <MetricCard label="Gaze Direction" value={gaze} />
            <MetricCard label="Head Pose (P/Y)" value={headPose} />
          </div>

          <div className="glass-panel p-5">
            <div className="flex justify-between items-center mb-4">
               <h2 className="text-xl font-semibold">Risk Trend</h2>
               <div className={`risk-badge ${riskLevel.toLowerCase()}`}>{riskLevel} - {riskScore}%</div>
            </div>
            <div className="h-[250px] w-full">
               <canvas ref={chartRef}></canvas>
            </div>
          </div>

          <div className="glass-panel p-5">
            <h2 className="text-xl font-semibold mb-4">System Alerts</h2>
            <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto pr-2">
               {alerts.length === 0 ? (
                 <div className="alert-item !border-blue-500">System standby. Monitoring for behavior...</div>
               ) : (
                 alerts.map((alert, i) => (
                   <div key={i} className={`alert-item ${getAlertBorder(alert.severity)}`}>
                     <strong className="mr-2">[{alert.time}]</strong> {alert.message}
                   </div>
                 ))
               )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function MetricCard({ label, value, color = 'text-white' }: { label: string, value: string, color?: string }) {
  return (
    <div className="glass-panel p-4 flex flex-col gap-2">
      <span className="text-[10px] text-slate-400 uppercase tracking-wider">{label}</span>
      <span className={`text-xl font-bold ${color}`}>{value}</span>
    </div>
  );
}

function getStateColor(state: string) {
  if (state === 'Drowsy') return 'text-red-500';
  if (state === 'Distracted') return 'text-yellow-500';
  return 'text-white';
}

function getAlertBorder(severity: string) {
  if (severity === 'warning') return '!border-yellow-500';
  if (severity === 'critical') return '!border-red-500';
  if (severity === 'emergency') return '!border-red-700 bg-red-900/10';
  return '!border-blue-500';
}
