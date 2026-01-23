# 📖 Documentación Técnica - OneDrive Business Monitor

## Índice

1. [Arquitectura del Sistema](#arquitectura-del-sistema)
2. [Flujo de Detección de Estados](#flujo-de-detección-de-estados)
3. [Sistema de Notificaciones](#sistema-de-notificaciones)
4. [Auto-Remediación](#auto-remediación)
5. [Dashboard Web](#dashboard-web)
6. [Base de Datos](#base-de-datos)
7. [Configuración Avanzada](#configuración-avanzada)

---

## Arquitectura del Sistema

### Componentes Principales

#### 1. Monitor (`src/monitor/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `main.py` | Loop principal, coordinación de componentes |
| `checker.py` | Detección de estado de OneDrive |
| `remediator.py` | Auto-remediación y lógica de notificaciones |
| `alerter.py` | Sistema legacy de alertas (deprecated) |

#### 2. Dashboard (`src/dashboard/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `main.py` | FastAPI server, endpoints REST, HTML dashboard |

#### 3. Shared (`src/shared/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `config.py` | Carga y validación de config.yaml |
| `database.py` | SQLite: init, log_status, queries |
| `notifier.py` | Envío de emails, Teams, Slack |
| `schemas.py` | Modelos Pydantic (OneDriveStatus, StatusReport) |
| `templates.py` | Carga y renderizado de templates HTML |
| `templates/` | 9 archivos HTML para emails |

---

## Flujo de Detección de Estados

### Métodos de Detección en `checker.py`

```
┌─────────────────────────────────────────────────────────────┐
│                    get_full_status()                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. check_process()                                          │
│     └─ ¿OneDrive.exe corriendo? → NOT_RUNNING si no         │
│                                                              │
│  2. verify_registry_account()                                │
│     └─ ¿Cuenta en registro? → NOT_FOUND si no               │
│                                                              │
│  3. _get_shell_status_ps() [PowerShell]                      │
│     └─ Obtiene atributos de archivo via Shell.Application   │
│     └─ Column 305: "Disponible", "Sincronizando", etc.      │
│                                                              │
│  4. _check_sync_log()                                        │
│     └─ Lee SyncDiagnostics.log                              │
│     └─ Busca: "Not Authenticated" → AUTH_REQUIRED           │
│     └─ Busca: "Paused" → PAUSED                             │
│     └─ Busca: "Error" → ERROR                               │
│                                                              │
│  5. Active Check (canary file)                               │
│     └─ Escribe archivo, verifica sincronización             │
│     └─ Timeout → PAUSED (Windows miente a veces)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Estados Posibles (`schemas.py`)

```python
class OneDriveStatus(str, Enum):
    OK = "OK"                    # Sincronizado
    SYNCING = "SYNCING"          # Sincronizando
    PAUSED = "PAUSED"            # Pausado
    AUTH_REQUIRED = "AUTH_REQUIRED"  # Re-autenticación
    ERROR = "ERROR"              # Error de sync
    NOT_RUNNING = "NOT_RUNNING"  # Proceso no corre
    NOT_FOUND = "NOT_FOUND"      # Cuenta no encontrada
    UNKNOWN = "UNKNOWN"          # Desconocido
```

---

## Sistema de Notificaciones

### Arquitectura de Notificaciones

```
┌─────────────────────────────────────────────────────────────┐
│                    Remediator.act()                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Cambio de Estado Detectado                                  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Esperar          │  REQUIRED_PERSISTENCE = 30s            │
│  │ Persistencia     │  (Evita falsos positivos)              │
│  └──────────────────┘                                        │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Determinar       │                                        │
│  │ Tipo de Email    │                                        │
│  └──────────────────┘                                        │
│         │                                                    │
│    ┌────┴────┬────────────┐                                  │
│    ▼         ▼            ▼                                  │
│  is_first  Estado=OK   Estado!=OK                            │
│  + OK?     + había      cualquiera                           │
│    │       incidente?      │                                 │
│    ▼         ▼             ▼                                 │
│  ok.html  resolved.html  {status}.html                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Decisión

```
Monitor Inicia
    │
    ▼
Estado Actual = ?
    │
    ├─ OK → Esperar 30s persistencia → ok.html ("Monitor Iniciado")
    │
    └─ NO OK → Esperar 30s persistencia → {estado}.html
    
Durante Ejecución:
    │
    ├─ Cambio a OK + había incidente → resolved.html (inmediato)
    │
    ├─ Cambio a OK + NO había incidente → No enviar
    │
    └─ Cambio a ERROR/PAUSED/etc → Esperar 30s → {estado}.html
```

### Notifier (`notifier.py`)

```python
class Notifier:
    def send_status_notification(status, timestamp, message)
        # Renderiza template HTML y envía por canales habilitados
    
    def send_resolution_notification(outage_start, outage_end)
        # Envía resolved.html con duración calculada
    
    def notify(subject, message, level, email_html)
        # Método base que distribuye a canales
    
    def _send_email(subject, body, is_html)
    def _send_teams(subject, message, level)
    def _send_slack(subject, message, level)
```

### Templates HTML (`src/shared/templates/`)

| Template | Uso |
|----------|-----|
| `ok.html` | Monitor iniciado con estado OK |
| `syncing.html` | Sincronización en progreso |
| `paused.html` | Sincronización pausada |
| `error.html` | Error de sincronización |
| `auth_required.html` | Requiere re-autenticación |
| `not_running.html` | OneDrive no está ejecutándose |
| `not_found.html` | Cuenta no encontrada |
| `unknown.html` | Estado desconocido |
| `resolved.html` | Problema resuelto (con duración) |

### Variables de Template

```html
{status}        - Estado actual (OK, ERROR, etc.)
{account}       - Email de la cuenta
{timestamp}     - Cuándo ocurrió el evento
{message}       - Mensaje adicional
{generated_at}  - Cuándo se generó el email
{outage_start}  - Inicio de interrupción (resolved.html)
{outage_end}    - Fin de interrupción (resolved.html)
{duration}      - Duración de interrupción (resolved.html)
```

---

## Auto-Remediación

### Lógica de Remediación (`remediator.py`)

```python
class RemediationAction:
    COOLDOWN_SECONDS = 60        # Entre intentos
    MAX_RESTARTS_PER_HOUR = 3    # Límite de reinicios
    REQUIRED_PERSISTENCE = 30    # Segundos antes de actuar
```

### Estados que Activan Remediación

| Estado | Acción |
|--------|--------|
| NOT_RUNNING | Reiniciar OneDrive.exe |
| AUTH_REQUIRED | Reiniciar (abre ventana de login) |
| PAUSED | Reiniciar (intenta reanudar) |
| ERROR | Notificar (no auto-fix confiable) |

### Flujo de Remediación

```
Estado Crítico Persistente (30s)
         │
         ▼
   ¿En cooldown?
    ├─ SÍ → Esperar
    └─ NO → ¿Límite de reinicios alcanzado?
              ├─ SÍ → Notificar "Intervención Manual Requerida"
              └─ NO → Reiniciar OneDrive
                        │
                        ▼
                  Esperar 120s
                        │
                        ▼
                  ¿Sigue malo?
                   ├─ SÍ → Notificar "Remediación Fallida"
                   └─ NO → Notificar "Resuelto"
```

---

## Dashboard Web

### Tecnología

- **FastAPI** - Framework web
- **Jinja2** - Templates HTML
- **Auto-refresh** - JavaScript cada 30s
- **Responsive** - CSS Flexbox/Grid

### Endpoints

| Endpoint | Método | Respuesta |
|----------|--------|-----------|
| `/` | GET | HTML Dashboard |
| `/api/status` | GET | JSON con estado actual |
| `/api/history` | GET | JSON con últimos 50 registros |
| `/health` | GET | `{"status": "healthy"}` |

### Datos del Dashboard

```json
{
  "timestamp": "2026-01-23T08:30:00",
  "account_email": "user@company.com",
  "account_folder": "C:\\Users\\...\\OneDrive - Company",
  "status": "OK",
  "status_detail": "Up to date",
  "process_running": true,
  "message": "Todos los archivos sincronizados",
  "out_of_sync_since": null
}
```

---

## Base de Datos

### Esquema SQLite (`monitor.db`)

```sql
CREATE TABLE status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    message TEXT,
    is_change BOOLEAN DEFAULT 0
);

CREATE INDEX idx_timestamp ON status_history(timestamp);
CREATE INDEX idx_status ON status_history(status);
```

### Funciones (`database.py`)

```python
init_db()                    # Crear tablas si no existen
log_status(status, msg, is_change)  # Insertar registro
get_outage_start_time()      # Obtener inicio de último problema
get_history(limit=50)        # Últimos N registros
```

---

## Configuración Avanzada

### Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `ONEDRIVE_MONITOR_CONFIG` | Ruta alternativa a config.yaml |

### Configuración Completa

```yaml
target:
  email: "user@company.com"
  folder: "C:\\Users\\user\\OneDrive - Company"

monitor:
  check_interval_seconds: 15       # Frecuencia de verificación
  status_file: "./status.json"     # Archivo de estado
  active_check_enabled: true       # Verificación activa (canary)
  active_check_interval_seconds: 30
  active_check_timeout_seconds: 20
  log_path: "...\\SyncDiagnostics.log"
  canary_file: ".monitor_canary"

notifications:
  enabled: true
  cooldown_minutes: 60             # Evitar spam
  failed_remediation_delay_seconds: 120
  channels:
    email:
      enabled: true
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      sender_email: "monitor@gmail.com"
      sender_password: "app-password"
      to_email: "admin@company.com"
      cc_email: ""
      bcc_email: ""
    teams:
      enabled: false
      webhook_url: "https://..."
    slack:
      enabled: false
      webhook_url: "https://..."

dashboard:
  host: "0.0.0.0"
  port: 8000
```

---

## Troubleshooting

### Problema: No detecta estado PAUSED

**Causa**: Windows a veces reporta "Up to date" aunque esté pausado.

**Solución**: El Active Check (canary file) detecta esto después de ~90s.

### Problema: Emails no llegan

**Verificar**:
1. `notifications.enabled: true`
2. Credenciales SMTP correctas
3. App Password si es Gmail
4. Puerto 587 abierto

### Problema: AUTH_REQUIRED no se detecta

**Causa**: Requiere leer SyncDiagnostics.log

**Verificar**: 
- `log_path` correcto en config.yaml
- Permisos de lectura en la carpeta de logs

---

## Changelog

### v1.2.0 (2026-01-23)
- ✅ Notificaciones HTML con 9 templates
- ✅ Separadores visuales homogéneos
- ✅ Compatibilidad Outlook Desktop
- ✅ Lógica de persistencia mejorada
- ✅ Diferenciación OK inicial vs RESOLVED

### v1.1.0
- ✅ Active Check con canary file
- ✅ Auto-remediación con reinicio

### v1.0.0
- ✅ Detección básica de estados
- ✅ Dashboard web
- ✅ Notificaciones por email
