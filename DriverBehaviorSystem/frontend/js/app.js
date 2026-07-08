document.addEventListener('DOMContentLoaded', () => {
    // --- UI Elements ---
    const videoStream = document.getElementById('videoStream');
    const overlayInfo = document.getElementById('connectionOverlay');
    const statusIndicator = document.querySelector('.status-indicator');
    
    const valDriverState = document.getElementById('valDriverState');
    const valEyeStatus = document.getElementById('valEyeStatus');
    const valGaze = document.getElementById('valGaze');
    const valHead = document.getElementById('valHead');
    
    const aiReason = document.getElementById('aiReason');
    const alertList = document.getElementById('alertList');
    const riskBadge = document.getElementById('riskBadge');
    
    // --- Chart.js Setup ---
    const ctx = document.getElementById('riskChart').getContext('2d');
    const maxDataPoints = 30; // Max points in time series
    
    const riskChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(maxDataPoints).fill(''),
            datasets: [{
                label: 'Risk Score %',
                data: Array(maxDataPoints).fill(0),
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    display: false // Hide X axis labels for clean look
                }
            },
            plugins: {
                legend: { display: false }
            },
            animation: { duration: 0 } // Smooth real-time update
        }
    });

    function updateChart(riskScore) {
        const data = riskChart.data.datasets[0].data;
        data.push(riskScore);
        if (data.length > maxDataPoints) {
            data.shift();
        }
        
        // Change color based on risk
        let color = '#10b981'; // Green
        let bgColor = 'rgba(16, 185, 129, 0.1)';
        if (riskScore >= 60) {
            color = '#ef4444'; // Red
            bgColor = 'rgba(239, 68, 68, 0.1)';
        } else if (riskScore >= 30) {
            color = '#f59e0b'; // Yellow
            bgColor = 'rgba(245, 158, 11, 0.1)';
        }
        
        riskChart.data.datasets[0].borderColor = color;
        riskChart.data.datasets[0].backgroundColor = bgColor;
        riskChart.update();
    }

    function addAlert(alert) {
        const div = document.createElement('div');
        div.className = `alert-item ${alert.severity}`;
        const time = new Date().toLocaleTimeString();
        div.innerHTML = `<strong>[${time}]</strong> ${alert.message}`;
        alertList.prepend(div);
        
        // Keep list bounded
        if (alertList.children.length > 50) {
            alertList.removeChild(alertList.lastChild);
        }
        
        // Voice alert
        if (alert.severity === 'critical') {
            const utterance = new SpeechSynthesisUtterance(alert.message);
            window.speechSynthesis.speak(utterance);
        }
    }

    // --- WebSocket Connection ---
    const wsUrl = `ws://${window.location.host}/ws/stream`;
    // Fallback if not served by FastAPI
    const ws = new WebSocket(wsUrl.includes("null") ? "ws://localhost:8000/ws/stream" : wsUrl);

    ws.onopen = () => {
        overlayInfo.style.display = 'none';
        videoStream.style.display = 'block';
        statusIndicator.style.backgroundColor = '#10b981'; // Green
        statusIndicator.style.boxShadow = '0 0 8px #10b981';
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // 1. Update Video Frame
        if (data.frame) {
            videoStream.src = "data:image/jpeg;base64," + data.frame;
        }

        // 2. Update Metrics
        valDriverState.innerText = data.behavior?.state || 'Unknown';
        
        // Color code state
        valDriverState.style.color = '#f8fafc';
        if (data.behavior?.state === 'Drowsy') valDriverState.style.color = '#ef4444';
        if (data.behavior?.state === 'Distracted') valDriverState.style.color = '#f59e0b';

        // Eye status
        valEyeStatus.innerText = data.behavior?.eye_status || 'Unknown';
        if (data.behavior?.eye_status === 'Closed') {
            valEyeStatus.style.color = '#ef4444';
        } else {
            valEyeStatus.style.color = '#f8fafc';
        }

        valGaze.innerText = data.metrics?.gaze || 'Center';
        valHead.innerText = `${data.metrics?.pitch || 0}° / ${data.metrics?.yaw || 0}°`;

        // 3. Update Risk & AI Reason
        const risk = data.risk || {score: 0, level: 'Safe', reason: ''};
        
        aiReason.innerHTML = `<strong>Insights:</strong> ${risk.reason || 'Sufficient data not available.'}`;
        
        riskBadge.innerText = `${risk.level} - ${risk.score}%`;
        riskBadge.className = `risk-badge ${risk.level.toLowerCase()}`;
        
        // Chart
        updateChart(risk.score);
        
        // 4. Handle Alerts
        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => addAlert(alert));
        }
    };

    ws.onclose = () => {
        overlayInfo.style.display = 'flex';
        overlayInfo.innerText = "Connection Lost. Reconnecting...";
        videoStream.style.display = 'none';
        statusIndicator.style.backgroundColor = '#ef4444'; // Red
        statusIndicator.style.boxShadow = '0 0 8px #ef4444';
    };
});
