# 🔄 OneDrive Business Monitor

Sistema de monitoreo empresarial para OneDrive for Business que detecta estados de sincronización, envía notificaciones por múltiples canales y proporciona un dashboard web en tiempo real.

## 📋 Características

- ✅ **Detección de 8 estados** de OneDrive: OK, SYNCING, PAUSED, ERROR, AUTH_REQUIRED, NOT_RUNNING, NOT_FOUND, UNKNOWN
- 📧 **Notificaciones HTML** elegantes por Email, Teams y Slack
- 🔄 **Auto-remediación** con reinicio automático de OneDrive
- 📊 **Dashboard web** responsive con auto-refresh
- 💾 **Base de datos SQLite** para histórico de estados
- 🔔 **Sistema de persistencia** para evitar falsos positivos

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    OneDrive Business Monitor                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │ Checker  │───▶│Remediator│───▶│      Notifier        │  │
│  │          │    │          │    │  ┌────┬─────┬─────┐  │  │
│  │ - Process│    │ - Auto   │    │  │Email│Teams│Slack│  │  │
│  │ - Files  │    │   Restart│    │  └────┴─────┴─────┘  │  │
│  │ - Attrib │    │ - Alerts │    │                      │  │
│  └──────────┘    └──────────┘    └──────────────────────┘  │
│        │                                                     │
│        ▼                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │status.json│◀──│ Database │◀──│      Dashboard       │  │
│  │          │    │ (SQLite) │    │    (FastAPI/Web)     │  │
│  └──────────┘    └──────────┘    └──────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Instalación

### Prerrequisitos

- Python 3.11+
- Windows 10/11 con OneDrive for Business instalado
- [UV](https://github.com/astral-sh/uv) (gestor de paquetes)

### Pasos

```bash
# Clonar repositorio
git clone https://github.com/hbuddenberg/OneDrive_Business_Monitor.git
cd OneDrive_Business_Monitor

# Instalar dependencias con UV
uv sync

# Copiar y configurar
cp config.yaml.example config.yaml
# Editar config.yaml con tus datos
```

## ⚙️ Configuración

Edita `config.yaml`:

```yaml
# Cuenta a monitorear
target:
  email: "tu.email@empresa.com"
  folder: "C:\\Users\\TuUsuario\\OneDrive - Empresa"

# Intervalo de verificación
monitor:
  check_interval_seconds: 15
  status_file: "./status.json"

# Notificaciones por Email
notifications:
  enabled: true
  cooldown_minutes: 60
  channels:
    email:
      enabled: true
      smtp_server: "smtp.gmail.com"
      to_email: "admin@empresa.com"
```

## 🎯 Uso

### Iniciar Monitor

```bash
uv run python -m src.monitor.main
```

### Iniciar Dashboard

```bash
uv run python -m src.dashboard.main

  ## Instalación y uso plug-and-play (con UV local en el venv)

  1. Crea y activa un entorno virtual:
    ```sh
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/macOS:
    source .venv/bin/activate
    ```

  2. Instala el proyecto y dependencias (esto instalará también uv localmente):
    ```sh
    pip install .
    # o usando uv si ya lo tienes global:
    uv pip install .
    ```

  3. Ahora puedes usar el comando `uv` directamente dentro del venv:
    ```sh
    uv pip install -r requirements.txt
    uv pip sync
    uv pip list
    # O ejecutar scripts con uv run ...
    uv run python -m src.main monitor
    ```

  4. Los scripts de ejecución (`run_monitor.bat` y `run_monitor.sh`) detectan automáticamente si hay un uv local en el venv y lo usan para mayor velocidad. Si no está, usan python/pip normalmente.

  5. También puedes seguir usando pip/python directamente si lo prefieres:
    ```sh
    python -m src.main monitor
    python -m src.main dashboard
    python -m src.main clean
    ```

  ---

  ## Ejecución multiplataforma

  Los scripts `run_monitor.bat` (Windows) y `run_monitor.sh` (Linux/macOS) permiten ejecutar el monitor, dashboard o limpieza con un solo comando. Detectan y usan uv local si está disponible, o python si no.

  Ejemplo:

  - Windows:
    ```bat
    run_monitor.bat monitor
    run_monitor.bat dashboard
    run_monitor.bat clean
    ```
  - Linux/macOS:
    ```sh
    ./run_monitor.sh monitor
    ./run_monitor.sh dashboard
    ./run_monitor.sh clean
    ```

  ---
## 🔧 API del Dashboard

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/api/status` | GET | Estado actual (JSON) |
| `/api/history` | GET | Últimos 50 registros |
| `/health` | GET | Health check |

## 📁 Estructura del Proyecto

```
OneDrive_Business_Monitor/
├── src/
│   ├── monitor/
│   │   ├── main.py        # Entry point del monitor
│   │   ├── checker.py     # Detección de estados
│   │   ├── alerter.py     # Sistema de alertas legacy
│   │   └── remediator.py  # Auto-remediación y notificaciones
│   ├── dashboard/
│   │   └── main.py        # FastAPI Dashboard
│   └── shared/
│       ├── config.py      # Configuración
│       ├── database.py    # SQLite
│       ├── notifier.py    # Sistema de notificaciones
│       ├── schemas.py     # Modelos Pydantic
│       ├── templates.py   # Cargador de templates
│       └── templates/     # HTML templates
├── config.yaml            # Configuración
├── status.json            # Estado actual
├── monitor.db             # Base de datos SQLite
├── pyproject.toml         # Dependencias
└── README.md
```

## 🧪 Pruebas

```bash
# Probar envío de emails (todos los templates)
uv run python test_all_templates.py --delay 3

# Probar un template específico
uv run python test_all_templates.py --single OK

# Pruebas de integración
uv run python test_integration.py
```

## 📝 Licencia

MIT License - Ver [LICENSE](LICENSE)

## 👤 Autor

Hans Buddenberg - [@hbuddenberg](https://github.com/hbuddenberg)

---

## 🚦 Plug & Play (Multiplataforma, sin uv)

1. **Crea el entorno virtual:**
   ```
   python -m venv .venv
   ```
2. **Activa el entorno virtual:**
   - **Windows:**
     ```
     .venv\Scripts\activate
     ```
   - **Linux/Mac:**
     ```
     source .venv/bin/activate
     ```
3. **Instala dependencias:**
   ```
   pip install -r requirements.txt
   ```
4. **Ejecuta el monitor, dashboard o limpieza:**
   - **Windows:**
     - Haz doble clic en `run_monitor.bat` o ejecuta:
       ```
       run_monitor.bat monitor
       run_monitor.bat dashboard
       run_monitor.bat clean
       ```
   - **Linux/Mac:**
     ```
     ./run_monitor.sh monitor
     ./run_monitor.sh dashboard
     ./run_monitor.sh clean
     ```

---

## Comandos útiles (manual)

- **Solo monitor:**
  ```
  python -m src.main monitor
  ```
- **Solo dashboard:**
  ```
  python -m src.main dashboard
  ```
- **Limpiar base de datos y estado:**
  ```
  python -m src.main clean
  ```

---

¡Listo para usar en cualquier máquina con Python instalado! No necesitas instalar nada globalmente ni usar uv.
