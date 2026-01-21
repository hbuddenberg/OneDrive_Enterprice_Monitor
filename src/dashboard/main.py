"""OneDrive Business Monitor Dashboard - FastAPI Application."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse

from src.shared.config import get_config
from src.shared.database import get_recent_history, get_chart_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OneDrive Business Monitor Dashboard",
    description="Monitor OneDrive for Business sync status",
    version="1.0.0",
)


def get_status() -> dict[str, Any]:
    """Read current status from status.json."""
    config = get_config()
    status_path = Path(config.monitor.status_file)

    if not status_path.exists():
        return {
            "status": "UNKNOWN",
            "message": "Status file not found. Is the monitor running?",
            "timestamp": datetime.now().isoformat(),
            "account_email": config.target.email,
            "account_folder": config.target.folder,
            "process_running": False,
            "tooltip_text": None,
        }

    try:
        with open(status_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading status file: {e}")
        return {
            "status": "ERROR",
            "message": f"Error reading status file: {e}",
            "timestamp": datetime.now().isoformat(),
            "account_email": config.target.email,
            "account_folder": config.target.folder,
            "process_running": False,
            "tooltip_text": None,
        }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    """Get current OneDrive status as JSON."""
    return get_status()

@app.get("/api/history")
async def api_history():
    """Get recent status history."""
    try:
        return get_recent_history(limit=50)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chart-data")
async def api_chart():
    """Get data for the status chart."""
    try:
        return get_chart_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the dashboard HTML page."""
    status = get_status()
    config = get_config()

    # Status-specific styling
    status_styles = {
        "OK": ("bg-green-500", "✅", "All files synchronized"),
        "SYNCING": ("bg-blue-500", "🔄", "Syncing files..."),
        "PAUSED": ("bg-yellow-500", "⏸️", "Sync paused"),
        "AUTH_REQUIRED": ("bg-red-600", "🔐", "Authentication required!"),
        "ERROR": ("bg-red-500", "❌", "Sync error"),
        "NOT_RUNNING": ("bg-gray-500", "💀", "OneDrive not running"),
        "NOT_FOUND": ("bg-orange-500", "🔍", "Account not found"),
        "UNKNOWN": ("bg-gray-400", "❓", "Status unknown"),
    }

    current_status = status.get("status", "UNKNOWN")
    bg_class, emoji, status_text = status_styles.get(
        current_status, ("bg-gray-400", "❓", "Unknown")
    )

    # Format timestamp
    timestamp = status.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        formatted_time = timestamp

    # Format Not Synced Since
    not_sync_raw = status.get("out_of_sync_since")
    not_sync_display = ""
    if not_sync_raw and current_status != "OK":
        try:
            # It comes as string from JSON
            if isinstance(not_sync_raw, str):
                 ns_dt = datetime.fromisoformat(not_sync_raw.replace("Z", "+00:00"))
            else:
                 ns_dt = not_sync_raw # Should basically not happen with JSON
            not_sync_display = ns_dt.strftime("%H:%M:%S")
        except Exception:
            not_sync_display = str(not_sync_raw)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Auto-refresh page every 60s as backup, but JS will update data -->
    <meta http-equiv="refresh" content="60"> 
    <title>OneDrive Monitor - {current_status}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .pulse {{
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
    </style>
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <header class="text-center mb-8">
            <h1 class="text-3xl font-bold mb-2">🌐 OneDrive Business Monitor</h1>
            <p class="text-gray-400">Monitoring: {config.target.email}</p>
        </header>

        <div class="max-w-4xl mx-auto space-y-6">
            <!-- Status Card -->
            <div class="{bg_class} rounded-xl p-8 shadow-2xl {'pulse' if current_status in ['SYNCING', 'AUTH_REQUIRED'] else ''}">
                <div class="text-center">
                    <span class="text-6xl mb-4 block">{emoji}</span>
                    <h2 class="text-4xl font-bold mb-2">{current_status}</h2>
                    <p class="text-xl opacity-90">{status.get('message', status_text)}</p>
                </div>
            </div>

            <!-- Details Card -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📊 Details</h3>
                <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <dt class="text-gray-400 text-sm">Account</dt>
                        <dd class="font-mono text-sm">{status.get('account_email', 'N/A')}</dd>
                    </div>
                    <div>
                        <dt class="text-gray-400 text-sm">Last Update</dt>
                        <dd class="font-mono text-sm">{formatted_time}</dd>
                    </div>
                    
                    {'<div class="md:col-span-2 bg-red-900/30 p-2 rounded border border-red-500/30"><dt class="text-red-400 text-xs uppercase font-bold">⚠️ Not Synced Since</dt><dd class="font-mono text-xl text-red-300">' + not_sync_display + '</dd></div>' if not_sync_display else ''}

                    <div class="md:col-span-2">
                        <dt class="text-gray-400 text-sm">Folder</dt>
                        <dd class="font-mono text-sm truncate" title="{status.get('account_folder', 'N/A')}">{status.get('account_folder', 'N/A')}</dd>
                    </div>
                </dl>
            </div>

            <!-- Activity Chart -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📈 Activity</h3>
                <div class="relative h-64 w-full">
                    <canvas id="activityChart"></canvas>
                </div>
            </div>

            <!-- History Table -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📜 Recent History</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm text-left text-gray-400">
                        <thead class="text-xs uppercase bg-gray-700 text-gray-400">
                            <tr>
                                <th class="px-3 py-2">Time</th>
                                <th class="px-3 py-2">Status</th>
                                <th class="px-3 py-2">Message</th>
                            </tr>
                        </thead>
                        <tbody id="historyTableBody">
                            <!-- JS will populate -->
                            <tr><td colspan="3" class="text-center py-4">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Footer -->
            <footer class="text-center mt-8 text-gray-500 text-sm">
                <p>Data auto-refreshes every 30s | <a href="/api/status" class="underline hover:text-white">JSON API</a></p>
            </footer>
        </div>
    </div>

    <script>
        // Status Scoring for Chart
        const STATUS_SCORES = {{
            'OK': 1, 'SYNCING': 0.8, 'PAUSED': 0.5, 
            'AUTH_REQUIRED': 0.2, 'NOT_RUNNING': 0, 'ERROR': 0, 'UNKNOWN': -0.1
        }};
        
        async function loadChart() {{
            try {{
                const res = await fetch('/api/chart-data');
                const data = await res.json();
                
                const ctx = document.getElementById('activityChart').getContext('2d');
                const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
                const points = data.map(d => STATUS_SCORES[d.status] || 0);
                
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Health Score',
                            data: points,
                            borderColor: '#3b82f6',
                            tension: 0.1,
                            fill: true,
                            backgroundColor: 'rgba(59, 130, 246, 0.1)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                min: 0, max: 1.1,
                                ticks: {{
                                    callback: function(value) {{
                                        if(value === 1) return 'OK';
                                        if(value === 0.5) return 'PAUSED';
                                        if(value === 0) return 'ERROR';
                                        return '';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }} catch(e) {{ console.error("Chart load error", e); }}
        }}

        async function loadHistory() {{
            try {{
                const res = await fetch('/api/history');
                const data = await res.json();
                const tbody = document.getElementById('historyTableBody');
                tbody.innerHTML = '';
                
                data.forEach(row => {{
                    const tr = document.createElement('tr');
                    tr.className = 'border-b border-gray-700 hover:bg-gray-700';
                    const date = new Date(row.timestamp).toLocaleString();
                    
                    let statusColor = 'text-white';
                    if(row.status === 'OK') statusColor = 'text-green-400';
                    if(row.status === 'AUTH_REQUIRED' || row.status === 'ERROR' || row.status === 'NOT_RUNNING') statusColor = 'text-red-400';
                    if(row.status === 'PAUSED') statusColor = 'text-yellow-400';

                    tr.innerHTML = `
                        <td class="px-3 py-2 font-mono whitespace-nowrap">${{date}}</td>
                        <td class="px-3 py-2 font-bold ${{statusColor}}">${{row.status}}</td>
                        <td class="px-3 py-2 truncate max-w-xs" title="${{row.message}}">${{row.message || ''}}</td>
                    `;
                    tbody.appendChild(tr);
                }});
            }} catch(e) {{ console.error("History load error", e); }}
        }}

        // Init
        loadChart();
        loadHistory();
        
        // Refresh Table periodically
        setInterval(loadHistory, 30000);
    </script>
</body>
</html>"""

    return HTMLResponse(content=html)


def run_dashboard() -> None:
    """Run the dashboard server."""
    import uvicorn

    config = get_config()
    logger.info(f"Starting dashboard on http://{config.dashboard.host}:{config.dashboard.port}")
    uvicorn.run(
        "src.dashboard.main:app",
        host=config.dashboard.host,
        port=config.dashboard.port,
        reload=False,
    )


if __name__ == "__main__":
    run_dashboard()
