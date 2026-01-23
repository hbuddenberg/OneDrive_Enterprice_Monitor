# 🧪 CHECKLIST DE PRUEBAS INTEGRALES
## OneDrive Business Monitor - Pre-Producción

**Fecha**: ____________  
**Tester**: ____________  
**Versión**: 1.2.0

---

## 📋 PREPARACIÓN

### Pre-requisitos
- [ ] OneDrive for Business instalado y configurado
- [ ] Cuenta `hansbuddenberg@tipartner.com` activa
- [ ] Acceso a bandeja de email para verificar notificaciones
- [ ] `config.yaml` configurado correctamente

### Iniciar Servicios

**Terminal 1 - Dashboard:**
```powershell
cd D:\Desarrollos\OneDrive_Enterprice_Monitor
uv run python -m src.dashboard.main
```
- [ ] Dashboard accesible en http://localhost:8000

**Terminal 2 - Monitor:**
```powershell
cd D:\Desarrollos\OneDrive_Enterprice_Monitor
uv run python -m src.monitor.main
```
- [ ] Monitor iniciado sin errores

---

## 🔬 FASE 1: VERIFICACIÓN DEL DASHBOARD (5 min)

| # | Test | Resultado | Notas |
|---|------|-----------|-------|
| D1 | Dashboard carga en http://localhost:8000 | [ ] OK / [ ] FAIL | |
| D2 | Muestra cuenta correcta (hansbuddenberg@tipartner.com) | [ ] OK / [ ] FAIL | |
| D3 | Muestra estado actual del OneDrive | [ ] OK / [ ] FAIL | |
| D4 | Auto-refresh funciona (esperar 30s) | [ ] OK / [ ] FAIL | |
| D5 | API `/api/status` responde JSON válido | [ ] OK / [ ] FAIL | |

---

## 🔬 FASE 2: PRUEBA DE INICIO (5 min)

### Test M0: Notificación de Inicio

**Estado esperado**: OneDrive funcionando normalmente (OK)

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | Monitor ya iniciado en Fase 1 | Log muestra "Obteniendo estado inicial..." |
| 2 | Esperar ~35 segundos | Log muestra "STARTUP: Sent OK notification..." |
| 3 | Revisar email | [ ] Recibido `ok.html` con "🚀 MONITOR INICIADO" |

**Resultado M0**: [ ] PASS / [ ] FAIL

**Captura del email recibido**: ____________

---

## 🔬 FASE 3: PRUEBAS DE ESTADOS (40 min)

### Test M1: Estado NOT_RUNNING

⚠️ **ACCIÓN MANUAL REQUERIDA**

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | **🔴 CERRAR OneDrive**: Click derecho icono bandeja → "Cerrar OneDrive" | OneDrive cerrado |
| 2 | Esperar ~35 segundos | Log: "Status: NOT_RUNNING" |
| 3 | Esperar notificación | Log: "ALERT: Sent notification for NOT_RUNNING..." |
| 4 | Revisar email | [ ] Recibido `not_running.html` |
| 5 | Dashboard muestra NOT_RUNNING | [ ] OK |

**Resultado M1**: [ ] PASS / [ ] FAIL

---

### Test M2: Estado RESOLVED (desde NOT_RUNNING)

⚠️ **ACCIÓN MANUAL REQUERIDA**

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | **🟢 ABRIR OneDrive**: Win+S → buscar "OneDrive" → Abrir | OneDrive inicia |
| 2 | Esperar sincronización (~30s) | Log: "Status: OK" |
| 3 | Verificar notificación inmediata | Log: "RESOLUTION: Sent resolution notification..." |
| 4 | Revisar email | [ ] Recibido `resolved.html` con duración |
| 5 | Dashboard muestra OK | [ ] OK |

**Resultado M2**: [ ] PASS / [ ] FAIL

**Duración mostrada en email**: ____________

---

### Test M3: Estado PAUSED

⚠️ **ACCIÓN MANUAL REQUERIDA**

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | **🟡 PAUSAR OneDrive**: Click derecho icono → "Pausar sincronización" → "2 horas" | OneDrive pausado |
| 2 | Esperar ~90 segundos (Active Check) | Log: "Active Check Override: PAUSED" |
| 3 | Esperar notificación | Log: "ALERT: Sent notification for PAUSED..." |
| 4 | Revisar email | [ ] Recibido `paused.html` |
| 5 | Dashboard muestra PAUSED | [ ] OK |

**Resultado M3**: [ ] PASS / [ ] FAIL

---

### Test M4: Estado RESOLVED (desde PAUSED)

⚠️ **ACCIÓN MANUAL REQUERIDA**

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | **🟢 REANUDAR OneDrive**: Click derecho icono → "Reanudar sincronización" | OneDrive reanuda |
| 2 | Esperar ~30 segundos | Log: "Status: OK" |
| 3 | Verificar notificación | Log: "RESOLUTION: Sent resolution notification..." |
| 4 | Revisar email | [ ] Recibido `resolved.html` |
| 5 | Dashboard muestra OK | [ ] OK |

**Resultado M4**: [ ] PASS / [ ] FAIL

---

### Test M5: Estado SYNCING

⚠️ **ACCIÓN MANUAL REQUERIDA**

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | **📁 COPIAR ARCHIVO GRANDE** (~100MB) a carpeta OneDrive | Archivo copiándose |
| 2 | Observar estado | Log: "Status: SYNCING" |
| 3 | Si persiste 30s | Log: "ALERT: Sent notification for SYNCING..." |
| 4 | Revisar email (si aplica) | [ ] Recibido `syncing.html` |
| 5 | Dashboard muestra SYNCING | [ ] OK |

**Nota**: SYNCING es transitorio, puede no persistir 30s para notificar.

**Resultado M5**: [ ] PASS / [ ] FAIL / [ ] N/A (muy rápido)

---

### Test M6: Estado NOT_FOUND

**SIN ACCIÓN MANUAL** - Se simula vía config

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | Detener monitor (Ctrl+C) | Monitor detenido |
| 2 | Editar `config.yaml`: cambiar email a `fake@test.com` | Config modificado |
| 3 | Reiniciar monitor | Log: "Status: NOT_FOUND" |
| 4 | Esperar ~35 segundos | Log: "ALERT: Sent notification for NOT_FOUND..." |
| 5 | Revisar email | [ ] Recibido `not_found.html` |
| 6 | **RESTAURAR** email correcto en config.yaml | Config restaurado |
| 7 | Reiniciar monitor | Log: "Status: OK" |

**Resultado M6**: [ ] PASS / [ ] FAIL

---

## 🔬 FASE 4: PRUEBA AUTH_REQUIRED (15 min)

### Test M7: Estado AUTH_REQUIRED

⚠️ **ACCIÓN MANUAL CRÍTICA - CAMBIO DE CONTRASEÑA**

| Paso | Acción | Responsable | Verificar |
|------|--------|-------------|-----------|
| 1 | Confirmar monitor corriendo y estado OK | Agente | Log: "Status: OK" |
| 2 | **🔴 PAUSA** - Preparar para cambio de contraseña | Agente | Te aviso |
| 3 | **🔐 CAMBIAR CONTRASEÑA** en https://portal.office.com | **TÚ** | Contraseña cambiada |
| 4 | Esperar que OneDrive detecte (~1-5 min) | Ambos | Icono muestra advertencia |
| 5 | Monitor detecta AUTH_REQUIRED | Agente | Log: "Status: AUTH_REQUIRED" |
| 6 | Esperar notificación | Agente | Log: "ALERT: Sent notification for AUTH_REQUIRED..." |
| 7 | Revisar email | **TÚ** | [ ] Recibido `auth_required.html` |
| 8 | **🔐 RE-AUTENTICAR** OneDrive con nueva contraseña | **TÚ** | Login completado |
| 9 | Esperar sincronización | Ambos | Log: "Status: OK" |
| 10 | Verificar RESOLVED | Agente | Log: "RESOLUTION: Sent resolution..." |
| 11 | Revisar email | **TÚ** | [ ] Recibido `resolved.html` |

**Resultado M7**: [ ] PASS / [ ] FAIL

---

## 🔬 FASE 5: PRUEBA ERROR (Opcional)

### Test M8: Estado ERROR

⚠️ **ACCIÓN MANUAL REQUERIDA** - Difícil de simular

Opciones para forzar ERROR:
1. Crear archivo con nombre inválido (caracteres especiales)
2. Llenar disco duro temporalmente
3. Bloquear archivo abierto por otra app

| Paso | Acción | Verificar |
|------|--------|-----------|
| 1 | Crear condición de error | Error visible en OneDrive |
| 2 | Esperar detección | Log: "Status: ERROR" |
| 3 | Esperar notificación | Log: "ALERT: Sent notification for ERROR..." |
| 4 | Revisar email | [ ] Recibido `error.html` |
| 5 | Resolver error | Log: "Status: OK" |
| 6 | Revisar resolved | [ ] Recibido `resolved.html` |

**Resultado M8**: [ ] PASS / [ ] FAIL / [ ] SKIPPED

---

## 📊 RESUMEN DE RESULTADOS

| Test | Estado Probado | Resultado | Email Recibido |
|------|----------------|-----------|----------------|
| M0 | OK (Inicio) | [ ] | ok.html |
| M1 | NOT_RUNNING | [ ] | not_running.html |
| M2 | RESOLVED | [ ] | resolved.html |
| M3 | PAUSED | [ ] | paused.html |
| M4 | RESOLVED | [ ] | resolved.html |
| M5 | SYNCING | [ ] | syncing.html |
| M6 | NOT_FOUND | [ ] | not_found.html |
| M7 | AUTH_REQUIRED | [ ] | auth_required.html |
| M8 | ERROR | [ ] | error.html |

### Dashboard
| Test | Resultado |
|------|-----------|
| D1-D5 | [ ] PASS / [ ] FAIL |

---

## 📝 NOTAS Y OBSERVACIONES

```
_____________________________________________
_____________________________________________
_____________________________________________
_____________________________________________
_____________________________________________
```

---

## ✅ APROBACIÓN

- [ ] **APROBADO PARA PRODUCCIÓN**
- [ ] **REQUIERE CORRECCIONES** (ver notas)

**Firma**: ____________  
**Fecha**: ____________
