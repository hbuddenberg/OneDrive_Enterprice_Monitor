# Checklist de Verificación - OneDrive Business Monitor

**Cuenta Objetivo**: `hansbuddenberg@tipartner.com` (Cuenta Empresa)
**Versión del Monitor**: v1.1 (Con Detección Activa)

Este documento permite validar que el sistema funciona correctamente y cumple con el requisito de monitorear **solo** la cuenta de empresa, detectando estados complejos como "Pausado" incluso cuando Windows reporta erróneamente "Actualizado".

---

## 1. Verificación de Entorno y Alcance

- [ ] **Solo Cuenta Empresa**: El monitor ignora la cuenta Personal (si existe).
    - Verificar que el log inicie con `Target: OneDrive - tipartner`.
    - Verificar que `status.json` muestre `account_email: hansbuddenberg@tipartner.com`.

- [ ] **Proceso de Monitor**: El script corre sin errores.
    - Ejecutar: `uv run python -m src.monitor.main`
    - No debe haber errores de permisos o librerías faltantes.

---

## 2. Pruebas de Detección (Core)

### Prueba A: Estado Normal (OK)
- [ ] **Acción**: Asegurar que OneDrive está corriendo y sincronizado (icono sin errores).
- [ ] **Resultado**:
    - Log muestra: `✅ Status: OK`
    - Dashboard muestra tarjeta Verde.
    - `status.json` muestra `"status": "OK"`.

### Prueba B: Detección de "Pausado" (Test Crítico)
Esta prueba validad la nueva lógica de "Latido" (Active Check).

- [ ] **Acción 1**: Pausar OneDrive manualmente (Click derecho -> Pausar).
- [ ] **Acción 2**: Esperar **90 segundos** (Ciclo 1: detecta log antiguo, escribe archivo oculto; Ciclo 2: detecta inactividad).
- [ ] **Resultado**:
    - El log debe cambiar de `✅ OK` a `⏸️ PAUSED`.
    - Mensaje en log: `Active Check Override: PAUSED (Log Stalled...)`.
    - Dashboard cambia a tarjeta Amarilla/Naranja.

### Prueba C: Recuperación (Resume)
- [ ] **Acción**: Reanudar la sincronización en OneDrive.
- [ ] **Resultado**:
    - En el siguiente ciclo (< 60s), el estado vuelve a `✅ OK`.

### Prueba D: Proceso No Ejecutándose
- [ ] **Acción**: Cerrar completamente OneDrive (`Taskkill` o Salir desde el icono).
- [ ] **Resultado**:
    - Log muestra inmediatamente `💀 Status: NOT_RUNNING`.
    - Dashboard muestra tarjeta Roja.

---

## 3. Verificación de Dashboard

- [ ] **Acceso Web**: El dashboard abre en `http://localhost:8000`.
- [ ] **Auto-Refresco**: La página actualiza el estado sin recargar (esperar 30s).
- [ ] **Datos Precisos**: Muestra la ruta de carpeta correcta (`...OneDrive - tipartner`).

---

## Resultados Finales

| Prueba | Estado | Observaciones |
|--------|--------|---------------|
| 1. Alcance | [ ] | |
| 2A. Normal | [ ] | |
| 2B. Pausado | [ ] | |
| 2C. Recuperación | [ ] | |
| 2D. Proceso Off | [ ] | |
| 3. Dashboard | [ ] | |

> **Nota**: Si la prueba 2B falla, verificar que el archivo `.monitor_canary` se esté creando en la carpeta raíz de OneDrive.
