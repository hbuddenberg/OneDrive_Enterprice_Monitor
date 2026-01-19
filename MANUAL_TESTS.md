# OneDrive Business Monitor - Manual Test Plan

## Objetivo
Pruebas sintéticas manuales para verificar todas las funcionalidades del Monitor de OneDrive Business.

---

## Pre-requisitos
1. Tener OneDrive Business conectado (`hansbuddenberg@tipartner.com`)
2. El monitor NO debe estar ejecutándose inicialmente
3. Tener dos terminales abiertas

---

## TC-01: Verificar Detección de Estado OK
**Objetivo**: Confirmar que el monitor detecta "Actualizado/Up to date"

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Asegurar que OneDrive está sincronizado (icono verde/azul claro) | Tooltip muestra "Actualizado" |
| 2 | Ejecutar: `uv run python -m src.monitor.main` | Monitor inicia sin errores |
| 3 | Esperar 5 segundos | Log muestra: `✅ Status: OK` |
| 4 | Revisar `status.json` | `"status": "OK"`, `"tooltip_text"` contiene "Actualizado" |
| 5 | Detener monitor con `Ctrl+C` | Monitor se detiene limpiamente |

---

## TC-02: Verificar Detección de Sincronización
**Objetivo**: Confirmar que detecta estado "Sincronizando"

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Copiar un archivo grande (>100MB) a la carpeta OneDrive | OneDrive empieza a sincronizar |
| 2 | Con el monitor corriendo, esperar siguiente ciclo (60s) | Log muestra: `🔄 Status: SYNCING` |
| 3 | Revisar `status.json` | `"status": "SYNCING"` |

---

## TC-03: Verificar Detección de Proceso No Corriendo
**Objetivo**: Confirmar que detecta cuando OneDrive.exe no está ejecutándose

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Cerrar OneDrive: Click derecho icono → "Cerrar OneDrive" | OneDrive se cierra |
| 2 | Iniciar monitor: `uv run python -m src.monitor.main` | Monitor inicia |
| 3 | Esperar 5 segundos | Log muestra: `💀 Status: NOT_RUNNING` |
| 4 | Revisar `status.json` | `"status": "NOT_RUNNING"`, `"process_running": false` |
| 5 | Reiniciar OneDrive desde menú inicio | Verificar que vuelve a estado OK |

---

## TC-04: Verificar Detección de Pausa
**Objetivo**: Confirmar que detecta estado "Pausado"

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Click derecho en icono OneDrive → "Pausar sincronización" → "2 horas" | Icono muestra pausa |
| 2 | Esperar siguiente ciclo del monitor | Log muestra: `⏸️ Status: PAUSED` |
| 3 | Revisar `status.json` | `"status": "PAUSED"` |
| 4 | Click derecho → "Reanudar sincronización" | Vuelve a OK |

---

## TC-05: Verificar Distinción Personal vs Business
**Objetivo**: Confirmar que ignora OneDrive Personal

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Verificar que OneDrive Personal también está visible en bandeja | Dos iconos OneDrive visibles |
| 2 | Ejecutar monitor | Monitor inicia |
| 3 | Revisar log | Debe mostrar "tipartner", NO "Personal" |
| 4 | Revisar `status.json` | `account_email` debe ser `hansbuddenberg@tipartner.com` |

---

## TC-06: Verificar Dashboard Web
**Objetivo**: Confirmar que el dashboard muestra información correcta

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | En terminal 1: `uv run python -m src.monitor.main` | Monitor corriendo |
| 2 | En terminal 2: `uv run python -m src.dashboard.main` | Dashboard en http://localhost:8000 |
| 3 | Abrir http://localhost:8000 en navegador | Página carga correctamente |
| 4 | Verificar tarjeta de estado | Verde con ✅ OK |
| 5 | Verificar detalles | Email, Folder, Process Running correcto |
| 6 | Esperar 30 segundos | Página se auto-refresca |

---

## TC-07: Verificar API JSON
**Objetivo**: Confirmar que el endpoint API funciona

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Con dashboard corriendo, abrir http://localhost:8000/api/status | JSON válido retornado |
| 2 | Verificar campos | Contiene: `status`, `timestamp`, `account_email`, `process_running` |

---

## TC-08: Simular Reautenticación Requerida (Avanzado)
**Objetivo**: Verificar detección de AUTH_REQUIRED

> [!WARNING]
> Este test requiere forzar la desconexión de la cuenta. Solo realizar si está dispuesto a reconectar.

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Abrir Administrador de Credenciales de Windows | Se abre el panel |
| 2 | Buscar credenciales de OneDrive/Microsoft y eliminarlas | Credenciales eliminadas |
| 3 | Reiniciar OneDrive | OneDrive pedirá iniciar sesión |
| 4 | Con monitor corriendo, verificar log | Log muestra: `🔐 Status: AUTH_REQUIRED` |
| 5 | Iniciar sesión nuevamente en OneDrive | Vuelve a estado OK |

---

## Matriz de Resultados

| Test | Resultado | Notas |
|------|-----------|-------|
| TC-01 OK Detection | ⬜ | |
| TC-02 Syncing | ⬜ | |
| TC-03 Not Running | ⬜ | |
| TC-04 Paused | ⬜ | |
| TC-05 Personal vs Business | ⬜ | |
| TC-06 Dashboard | ⬜ | |
| TC-07 API | ⬜ | |
| TC-08 Auth Required | ⬜ | |

**Leyenda**: ✅ Pasó | ❌ Falló | ⬜ No ejecutado
