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
      smtp_port: 587
      sender_email: "monitor@gmail.com"
      sender_password: "app-password"
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
```

Acceder a: http://localhost:8000

### Ejecutar Ambos

```bash
# Terminal 1 - Monitor
uv run python -m src.monitor.main

# Terminal 2 - Dashboard
uv run python -m src.dashboard.main
```

## 📊 Estados Detectados

| Estado | Emoji | Descripción | Notificación |
|--------|-------|-------------|--------------|
| OK | ✅ | Sincronizado | Solo al inicio |
| SYNCING | 🔄 | Sincronizando | Sí |
| PAUSED | ⏸️ | Pausado por usuario | Sí |
| ERROR | ❌ | Error de sincronización | Sí + Auto-fix |
| AUTH_REQUIRED | 🔐 | Re-autenticación necesaria | Sí (Crítico) |
| NOT_RUNNING | 💀 | OneDrive no ejecutándose | Sí + Auto-fix |
| NOT_FOUND | 🔍 | Cuenta no encontrada | Sí |
| UNKNOWN | ❓ | Estado desconocido | Sí |
| RESOLVED | 🎉 | Problema resuelto | Sí |

## 📧 Plantillas de Email

Las plantillas HTML están en `src/shared/templates/`:

- `ok.html` - Estado normal / Monitor iniciado
- `error.html` - Error de sincronización
- `auth_required.html` - Autenticación requerida
- `not_running.html` - OneDrive no ejecutándose
- `paused.html` - Sincronización pausada
- `syncing.html` - Sincronización en progreso
- `not_found.html` - Cuenta no encontrada
- `unknown.html` - Estado desconocido
- `resolved.html` - Problema resuelto

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
