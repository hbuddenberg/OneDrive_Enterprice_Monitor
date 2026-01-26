from src.shared.notifier import get_notification_action
# Ejemplo de uso en dashboard: función para decidir si mostrar banner especial o log de transición
def should_show_notification(prev, curr, is_first_run):
    notify, tipo = get_notification_action(prev, curr, is_first_run)
    return notify, tipo
"""OneDrive Business Monitor Dashboard - Aplicación FastAPI."""

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
    title="Monitor OneDrive Empresarial - Dashboard",
    description="Monitor del estado de sincronización de OneDrive para Empresas",
    version="1.0.0",
)


def get_status() -> dict[str, Any]:
    """Lee el estado actual desde status.json."""
    config = get_config()
    status_path = Path(config.monitor.status_file)

    if not status_path.exists():
        return {
            "status": "UNKNOWN",
            "message": "Archivo de estado no encontrado. ¿Está ejecutándose el monitor?",
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
        logger.error(f"Error al leer archivo de estado: {e}")
        return {
            "status": "ERROR",
            "message": f"Error al leer archivo de estado: {e}",
            "timestamp": datetime.now().isoformat(),
            "account_email": config.target.email,
            "account_folder": config.target.folder,
            "process_running": False,
            "tooltip_text": None,
        }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    """Obtiene el estado actual de OneDrive como JSON."""
    return get_status()

@app.get("/api/history")
async def api_history():
    """Obtiene el historial reciente de estados."""
    try:
        return get_recent_history(limit=50)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chart-data")
async def api_chart():
    """Obtiene los datos para el gráfico de estados."""
    try:
        return get_chart_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Renderiza la página HTML del dashboard."""
    status = get_status()
    config = get_config()

    # Estilos específicos por estado
    status_styles = {
        "OK": ("bg-green-500", "✅", "Todos los archivos sincronizados"),
        "SYNCING": ("bg-blue-500", "🔄", "Sincronizando archivos..."),
        "PAUSED": ("bg-yellow-500", "⏸️", "Sincronización pausada"),
        "AUTH_REQUIRED": ("bg-red-600", "🔐", "¡Autenticación requerida!"),
        "ERROR": ("bg-red-500", "❌", "Error de sincronización"),
        "NOT_RUNNING": ("bg-gray-500", "💀", "OneDrive no está ejecutándose"),
        "NOT_FOUND": ("bg-orange-500", "🔍", "Cuenta no encontrada"),
        "UNKNOWN": ("bg-gray-400", "❓", "Estado desconocido"),
    }

    current_status = status.get("status", "UNKNOWN")
    bg_class, emoji, status_text = status_styles.get(
        current_status, ("bg-gray-400", "❓", "Desconocido")
    )

    # Formatear timestamp
    timestamp = status.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        formatted_time = timestamp

    # Formatear No Sincronizado Desde
    not_sync_raw = status.get("out_of_sync_since")
    not_sync_display = ""
    if not_sync_raw and current_status != "OK":
        try:
            # Viene como string desde JSON
            if isinstance(not_sync_raw, str):
                 ns_dt = datetime.fromisoformat(not_sync_raw.replace("Z", "+00:00"))
            else:
                 ns_dt = not_sync_raw # Básicamente no debería pasar con JSON
            not_sync_display = ns_dt.strftime("%H:%M:%S")
        except Exception:
            not_sync_display = str(not_sync_raw)

    from src.shared.database import get_monthly_incident_count
    incident_count = get_monthly_incident_count()
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Auto-refresh de la página cada 60s como respaldo, pero JS actualizará los datos -->
    <meta http-equiv="refresh" content="60"> 
    <title>Monitor OneDrive - {current_status}</title>
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
            <h1 class="text-3xl font-bold mb-2">🌐 Monitor OneDrive Empresarial</h1>
            <p class="text-gray-400">Monitoreando: {config.target.email}</p>
        </header>

        <div class="max-w-4xl mx-auto space-y-6">
            <!-- Tarjeta de Estado -->
            <div class="{bg_class} rounded-xl p-8 shadow-2xl {'pulse' if current_status in ['SYNCING', 'AUTH_REQUIRED'] else ''}">
                <div class="text-center">
                    <span class="text-6xl mb-4 block">{emoji}</span>
                    <h2 class="text-4xl font-bold mb-2">{current_status}</h2>
                    <p class="text-xl opacity-90">{status.get('message', status_text)}</p>
                </div>
            </div>

            <!-- Tarjeta de Detalles -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📊 Detalles</h3>
                <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <dt class="text-gray-400 text-sm">Cuenta</dt>
                        <dd class="font-mono text-sm">{status.get('account_email', 'N/A')}</dd>
                    </div>
                    <div>
                        <dt class="text-gray-400 text-sm">Última Actualización</dt>
                        <dd class="font-mono text-sm">{formatted_time}</dd>
                    </div>
                    
                    {'<div class="md:col-span-2 bg-red-900/30 p-2 rounded border border-red-500/30"><dt class="text-red-400 text-xs uppercase font-bold">⚠️ Sin Sincronizar Desde</dt><dd class="font-mono text-xl text-red-300">' + not_sync_display + '</dd></div>' if not_sync_display else ''}

                    <div class="md:col-span-2">
                        <dt class="text-gray-400 text-sm">Carpeta</dt>
                        <dd class="font-mono text-sm truncate" title="{status.get('account_folder', 'N/A')}">{status.get('account_folder', 'N/A')}</dd>
                    </div>
                </dl>
            </div>


            <!-- Gráfico de Actividad -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📈 Actividad</h3>
                <div class="relative h-64 w-full">
                    <canvas id="activityChart"></canvas>
                </div>
            </div>

            <!-- Bloque de Caídas Mensuales -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl flex flex-col items-center">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2 text-red-400">Caídas este mes</h3>
                <div class="text-5xl font-bold text-red-300">{incident_count}</div>
            </div>

            <!-- Tabla de Historial -->
            <div class="bg-gray-800 rounded-xl p-6 shadow-xl">
                <h3 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">📜 Historial Reciente</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm text-left text-gray-400">
                        <thead class="text-xs uppercase bg-gray-700 text-gray-400">
                            <tr>
                                <th class="px-3 py-2">Hora</th>
                                <th class="px-3 py-2">Estado</th>
                                <th class="px-3 py-2">Mensaje</th>
                            </tr>
                        </thead>
                        <tbody id="historyTableBody">
                            <!-- JS lo poblará -->
                            <tr><td colspan="3" class="text-center py-4">Cargando...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Footer -->
            <footer class="text-center mt-8 text-gray-500 text-sm">
                <p>Los datos se actualizan cada 30s | <a href="/api/status" class="underline hover:text-white">API JSON</a></p>
            </footer>
        </div>
    </div>

    <script>
        // Puntuación de Estados para el Gráfico
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
                            label: 'Puntuación de Salud',
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
                                        if(value === 0.5) return 'PAUSADO';
                                        if(value === 0) return 'ERROR';
                                        return '';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }} catch(e) {{ console.error("Error al cargar gráfico", e); }}
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
            }} catch(e) {{ console.error("Error al cargar historial", e); }}
        }}

        // Inicializar
        loadChart();
        loadHistory();
        
        // Refrescar tabla periódicamente
        setInterval(loadHistory, 30000);
    </script>
</body>
</html>"""

    return HTMLResponse(content=html)


def run_dashboard() -> None:
    """Ejecuta el servidor del dashboard."""
    import uvicorn

    config = get_config()
    logger.info(f"Iniciando dashboard en http://{config.dashboard.host}:{config.dashboard.port}")
    uvicorn.run(
        "src.dashboard.main:app",
        host=config.dashboard.host,
        port=config.dashboard.port,
        reload=False,
    )


if __name__ == "__main__":
    run_dashboard()
