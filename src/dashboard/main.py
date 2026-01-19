"""OneDrive Business Monitor Dashboard - FastAPI Application."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.shared.config import get_config

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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>OneDrive Monitor - {current_status}</title>
    <script src="https://cdn.tailwindcss.com"></script>
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

        <div class="max-w-2xl mx-auto">
            <!-- Status Card -->
            <div class="{bg_class} rounded-xl p-8 shadow-2xl mb-6 {'pulse' if current_status in ['SYNCING', 'AUTH_REQUIRED'] else ''}">
                <div class="text-center">
                    <span class="text-6xl mb-4 block">{emoji}</span>
                    <h2 class="text-4xl font-bold mb-2">{current_status}</h2>
                    <p class="text-xl opacity-90">{status.get('message', status_text)}</p>
                </div>
            </div>

            <!-- Details Card -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📊 Details</h3>
                <dl class="space-y-3">
                    <div class="flex justify-between">
                        <dt class="text-gray-400">Account</dt>
                        <dd class="font-mono">{status.get('account_email', 'N/A')}</dd>
                    </div>
                    <div class="flex justify-between">
                        <dt class="text-gray-400">Folder</dt>
                        <dd class="font-mono text-sm truncate max-w-xs" title="{status.get('account_folder', 'N/A')}">{status.get('account_folder', 'N/A')}</dd>
                    </div>
                    <div class="flex justify-between">
                        <dt class="text-gray-400">Process Running</dt>
                        <dd>{'✅ Yes' if status.get('process_running') else '❌ No'}</dd>
                    </div>
                    <div class="flex justify-between">
                        <dt class="text-gray-400">Last Update</dt>
                        <dd class="font-mono">{formatted_time}</dd>
                    </div>
                    <div class="flex justify-between">
                        <dt class="text-gray-400">Tooltip</dt>
                        <dd class="text-sm truncate max-w-xs" title="{status.get('tooltip_text', 'N/A')}">{status.get('tooltip_text', 'N/A') or 'N/A'}</dd>
                    </div>
                </dl>
            </div>

            <!-- Footer -->
            <footer class="text-center mt-8 text-gray-500 text-sm">
                <p>Auto-refresh: 30 seconds | <a href="/api/status" class="underline hover:text-white">JSON API</a></p>
            </footer>
        </div>
    </div>
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
