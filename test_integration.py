#!/usr/bin/env python
"""
Test de Integración - Simulación de Estados de OneDrive

Este script simula escenarios reales manipulando OneDrive para verificar
que el monitor detecta correctamente cada estado y envía las notificaciones.

ESCENARIOS:
1. NOT_RUNNING - Mata el proceso OneDrive.exe
2. OK (recuperación) - Reinicia OneDrive
3. PAUSED - Pausa la sincronización via menú contextual/API
4. OK (recuperación) - Reanuda sincronización
5. AUTH_REQUIRED - (Manual) Requiere cerrar sesión en OneDrive

⚠️ ADVERTENCIA: Este script MANIPULA OneDrive real.
   - Cerrará el proceso OneDrive
   - Lo reiniciará
   - Pausará/Reanudará sincronización

Uso:
    python test_integration.py kill          # Mata OneDrive y espera detección
    python test_integration.py restart       # Reinicia OneDrive
    python test_integration.py pause         # Pausa sincronización
    python test_integration.py resume        # Reanuda sincronización
    python test_integration.py cycle         # Ciclo completo: kill → restart → pause → resume
    python test_integration.py monitor       # Solo monitorea el estado actual (no modifica nada)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix module path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.monitor.checker import OneDriveChecker
from src.shared.config import get_config

# Colores para terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str) -> None:
    """Imprime encabezado de sección."""
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}  {title}{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")


def print_status(status: str, detail: str, process_running: bool) -> None:
    """Imprime el estado actual con colores."""
    status_colors = {
        "OK": Colors.GREEN,
        "SYNCING": Colors.BLUE,
        "PAUSED": Colors.YELLOW,
        "AUTH_REQUIRED": Colors.RED,
        "ERROR": Colors.RED,
        "NOT_RUNNING": Colors.RED,
        "NOT_FOUND": Colors.YELLOW,
    }
    color = status_colors.get(status, Colors.YELLOW)
    process_icon = "✅" if process_running else "❌"
    
    print(f"  {color}{Colors.BOLD}Estado: {status}{Colors.END}")
    print(f"  Detalle: {detail}")
    print(f"  Proceso: {process_icon} {'Ejecutándose' if process_running else 'Detenido'}")


def print_step(step: int, total: int, message: str) -> None:
    """Imprime paso actual."""
    print(f"\n{Colors.YELLOW}[{step}/{total}] {message}{Colors.END}")


def print_success(message: str) -> None:
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str) -> None:
    """Imprime mensaje de error."""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_warning(message: str) -> None:
    """Imprime advertencia."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_info(message: str) -> None:
    """Imprime información."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")


def get_current_status() -> tuple:
    """Obtiene el estado actual de OneDrive usando el checker."""
    checker = OneDriveChecker()
    status, process_running, detail = checker.get_full_status()
    return status.value, detail, process_running


def read_status_file() -> dict:
    """Lee el archivo status.json del monitor."""
    status_path = Path("status.json")
    if status_path.exists():
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def wait_for_status(expected_status: str, timeout: int = 60, check_interval: int = 5) -> bool:
    """
    Espera hasta que el monitor detecte el estado esperado.
    
    Args:
        expected_status: Estado esperado (OK, NOT_RUNNING, etc.)
        timeout: Tiempo máximo de espera en segundos
        check_interval: Intervalo entre verificaciones
        
    Returns:
        True si se detectó el estado, False si timeout
    """
    print_info(f"Esperando estado '{expected_status}' (timeout: {timeout}s)...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout:
        status, detail, process = get_current_status()
        
        if status != last_status:
            print(f"  → Estado actual: {status} ({detail})")
            last_status = status
        
        if status == expected_status:
            print_success(f"Estado '{expected_status}' detectado correctamente")
            return True
        
        # Mostrar countdown
        remaining = int(timeout - (time.time() - start_time))
        print(f"  ⏳ Esperando... ({remaining}s restantes)", end="\r")
        
        time.sleep(check_interval)
    
    print()
    print_error(f"Timeout esperando estado '{expected_status}'")
    return False


def find_onedrive_exe() -> Path:
    """Encuentra la ruta del ejecutable de OneDrive."""
    paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/OneDrive/OneDrive.exe",
        Path("C:/Program Files/Microsoft OneDrive/OneDrive.exe"),
        Path("C:/Program Files (x86)/Microsoft OneDrive/OneDrive.exe"),
    ]
    
    for p in paths:
        if p.exists():
            return p
    
    return None


def kill_onedrive() -> bool:
    """Mata el proceso OneDrive.exe."""
    print_header("MATANDO PROCESO ONEDRIVE")
    
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "OneDrive.exe"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            print_success("Proceso OneDrive terminado")
            return True
        elif "no se encontró" in result.stderr.lower() or "not found" in result.stderr.lower():
            print_warning("OneDrive no estaba ejecutándose")
            return True
        else:
            print_error(f"Error al matar proceso: {result.stderr}")
            return False
            
    except Exception as e:
        print_error(f"Excepción: {e}")
        return False


def start_onedrive() -> bool:
    """Inicia OneDrive.exe."""
    print_header("INICIANDO ONEDRIVE")
    
    exe_path = find_onedrive_exe()
    if not exe_path:
        print_error("No se encontró OneDrive.exe")
        return False
    
    print_info(f"Ejecutable: {exe_path}")
    
    try:
        subprocess.Popen(
            [str(exe_path), "/background"],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        )
        print_success("OneDrive iniciado")
        return True
        
    except Exception as e:
        print_error(f"Error al iniciar: {e}")
        return False


def pause_onedrive() -> bool:
    """
    Pausa la sincronización de OneDrive.
    
    Nota: OneDrive no tiene API pública para pausar.
    Usamos PowerShell para simular click en el menú del sistema.
    """
    print_header("PAUSANDO SINCRONIZACIÓN")
    
    # Método 1: Crear archivo grande para forzar sync largo
    # Método 2: Usar AutoHotkey/PowerShell para click en tray
    # Método 3: Modificar registry (riesgoso)
    
    print_warning("La pausa de OneDrive requiere interacción manual o AutoHotkey")
    print_info("Opciones para pausar OneDrive:")
    print("  1. Click derecho en icono de OneDrive en bandeja del sistema")
    print("  2. Seleccionar 'Pausar sincronización'")
    print("  3. Elegir duración (2h, 8h, 24h)")
    print()
    
    # Intentar con PowerShell - simular keyboard shortcut
    # Esto es experimental y puede no funcionar en todos los sistemas
    try:
        # Alternativa: Matar y no reiniciar simula PAUSED para el monitor
        print_info("Simulando PAUSED mediante detención temporal...")
        
        input(f"{Colors.YELLOW}Presiona ENTER después de pausar OneDrive manualmente...{Colors.END}")
        return True
        
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def resume_onedrive() -> bool:
    """
    Reanuda la sincronización de OneDrive.
    """
    print_header("REANUDANDO SINCRONIZACIÓN")
    
    print_info("Opciones para reanudar OneDrive:")
    print("  1. Click derecho en icono de OneDrive en bandeja del sistema")
    print("  2. Seleccionar 'Reanudar sincronización'")
    print()
    
    # Si OneDrive no está corriendo, iniciarlo
    checker = OneDriveChecker()
    if not checker.check_process():
        print_info("OneDrive no está ejecutándose, iniciando...")
        return start_onedrive()
    
    input(f"{Colors.YELLOW}Presiona ENTER después de reanudar OneDrive manualmente...{Colors.END}")
    return True


def monitor_status(duration: int = 60) -> None:
    """
    Monitorea el estado de OneDrive sin modificar nada.
    
    Args:
        duration: Duración del monitoreo en segundos
    """
    print_header("MONITOREANDO ESTADO DE ONEDRIVE")
    print_info(f"Monitoreando por {duration} segundos (Ctrl+C para detener)")
    print()
    
    start_time = time.time()
    last_status = None
    status_changes = []
    
    try:
        while time.time() - start_time < duration:
            status, detail, process = get_current_status()
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if status != last_status:
                status_changes.append((timestamp, status, detail))
                print(f"\n{Colors.BOLD}[{timestamp}] Cambio de estado:{Colors.END}")
                print_status(status, detail, process)
                last_status = status
            else:
                print(f"  [{timestamp}] {status} - {detail}", end="\r")
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n\nMonitoreo detenido por usuario")
    
    # Resumen
    print_header("RESUMEN DE CAMBIOS")
    if status_changes:
        for ts, st, det in status_changes:
            color = Colors.GREEN if st == "OK" else Colors.YELLOW if st in ["SYNCING", "PAUSED"] else Colors.RED
            print(f"  {ts} → {color}{st}{Colors.END}: {det}")
    else:
        print_info("No hubo cambios de estado durante el monitoreo")


def test_kill_and_detect() -> bool:
    """
    Test: Mata OneDrive y verifica que el monitor detecte NOT_RUNNING.
    """
    print_header("TEST: KILL → NOT_RUNNING")
    
    # Paso 1: Verificar estado inicial
    print_step(1, 3, "Verificando estado inicial...")
    status, detail, process = get_current_status()
    print_status(status, detail, process)
    
    if not process:
        print_warning("OneDrive ya está detenido")
        return True
    
    # Paso 2: Matar proceso
    print_step(2, 3, "Matando proceso OneDrive...")
    if not kill_onedrive():
        return False
    
    time.sleep(2)
    
    # Paso 3: Esperar detección
    print_step(3, 3, "Esperando que el monitor detecte NOT_RUNNING...")
    return wait_for_status("NOT_RUNNING", timeout=30)


def test_restart_and_detect() -> bool:
    """
    Test: Reinicia OneDrive y verifica que vuelva a OK.
    """
    print_header("TEST: RESTART → OK")
    
    # Paso 1: Verificar que esté detenido
    print_step(1, 3, "Verificando estado actual...")
    status, detail, process = get_current_status()
    print_status(status, detail, process)
    
    # Paso 2: Iniciar OneDrive
    print_step(2, 3, "Iniciando OneDrive...")
    if not start_onedrive():
        return False
    
    time.sleep(5)  # Dar tiempo para que inicie
    
    # Paso 3: Esperar detección de OK o SYNCING
    print_step(3, 3, "Esperando que el monitor detecte OK/SYNCING...")
    
    # OK o SYNCING son estados válidos después de reiniciar
    start = time.time()
    timeout = 90  # OneDrive puede tardar en iniciar
    
    while time.time() - start < timeout:
        status, detail, process = get_current_status()
        if status in ["OK", "SYNCING"]:
            print_success(f"Estado '{status}' detectado correctamente")
            return True
        print(f"  → Estado: {status} ({detail})", end="\r")
        time.sleep(5)
    
    print()
    print_error("Timeout esperando recuperación")
    return False


def test_full_cycle() -> bool:
    """
    Test de ciclo completo:
    1. Kill → NOT_RUNNING
    2. Restart → OK
    3. (Opcional) Pause → PAUSED
    4. (Opcional) Resume → OK
    """
    print_header("🔄 TEST DE CICLO COMPLETO")
    print()
    print_warning("Este test manipulará OneDrive de la siguiente manera:")
    print("  1. Matará el proceso OneDrive (NOT_RUNNING)")
    print("  2. Reiniciará OneDrive (OK)")
    print("  3. [Manual] Pausar sincronización (PAUSED)")
    print("  4. [Manual] Reanudar sincronización (OK)")
    print()
    
    input(f"{Colors.YELLOW}Presiona ENTER para continuar o Ctrl+C para cancelar...{Colors.END}")
    
    results = []
    
    # Test 1: Kill
    print("\n" + "─" * 40)
    print(f"{Colors.BOLD}FASE 1: NOT_RUNNING{Colors.END}")
    print("─" * 40)
    success = test_kill_and_detect()
    results.append(("NOT_RUNNING", success))
    
    if not success:
        print_error("Fase 1 falló, abortando ciclo")
        return False
    
    print_info("Esperando 10 segundos antes de la siguiente fase...")
    time.sleep(10)
    
    # Test 2: Restart
    print("\n" + "─" * 40)
    print(f"{Colors.BOLD}FASE 2: RECUPERACIÓN (OK){Colors.END}")
    print("─" * 40)
    success = test_restart_and_detect()
    results.append(("RESTART→OK", success))
    
    if not success:
        print_error("Fase 2 falló")
    
    # Test 3: Pause (manual)
    print("\n" + "─" * 40)
    print(f"{Colors.BOLD}FASE 3: PAUSA (Manual){Colors.END}")
    print("─" * 40)
    
    do_pause = input(f"{Colors.YELLOW}¿Probar pausa manual? (s/n): {Colors.END}").lower().strip()
    if do_pause == 's':
        pause_onedrive()
        success = wait_for_status("PAUSED", timeout=60)
        results.append(("PAUSED", success))
        
        if success:
            # Test 4: Resume
            print("\n" + "─" * 40)
            print(f"{Colors.BOLD}FASE 4: REANUDAR{Colors.END}")
            print("─" * 40)
            resume_onedrive()
            success = wait_for_status("OK", timeout=90)
            results.append(("RESUME→OK", success))
    
    # Resumen final
    print_header("📊 RESUMEN DEL CICLO")
    all_passed = True
    for name, passed in results:
        if passed:
            print_success(f"{name}")
        else:
            print_error(f"{name}")
            all_passed = False
    
    return all_passed


def show_status_file() -> None:
    """Muestra el contenido del archivo status.json."""
    print_header("ARCHIVO STATUS.JSON")
    
    status = read_status_file()
    if status:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print_warning("Archivo status.json no encontrado o vacío")


def main():
    parser = argparse.ArgumentParser(
        description="Test de Integración - Simulación de Estados de OneDrive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python test_integration.py monitor      # Solo monitorear (no modifica nada)
  python test_integration.py kill         # Mata OneDrive
  python test_integration.py restart      # Reinicia OneDrive
  python test_integration.py cycle        # Ciclo completo de pruebas
  python test_integration.py status       # Ver archivo status.json

⚠️ ADVERTENCIA: Algunos comandos MODIFICAN el estado de OneDrive
        """
    )
    
    parser.add_argument(
        "action",
        choices=["kill", "restart", "pause", "resume", "cycle", "monitor", "status"],
        help="Acción a ejecutar"
    )
    
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Duración del monitoreo en segundos (para 'monitor')"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.CYAN}{'🧪' * 20}{Colors.END}")
    print(f"{Colors.BOLD}   TEST DE INTEGRACIÓN - ONEDRIVE MONITOR{Colors.END}")
    print(f"{Colors.CYAN}{'🧪' * 20}{Colors.END}")
    
    # Mostrar estado inicial
    print_header("ESTADO ACTUAL")
    status, detail, process = get_current_status()
    print_status(status, detail, process)
    
    success = True
    
    if args.action == "kill":
        success = test_kill_and_detect()
        
    elif args.action == "restart":
        success = test_restart_and_detect()
        
    elif args.action == "pause":
        success = pause_onedrive()
        if success:
            wait_for_status("PAUSED", timeout=60)
        
    elif args.action == "resume":
        success = resume_onedrive()
        if success:
            wait_for_status("OK", timeout=90)
        
    elif args.action == "cycle":
        success = test_full_cycle()
        
    elif args.action == "monitor":
        monitor_status(args.duration)
        
    elif args.action == "status":
        show_status_file()
    
    # Resultado final
    print()
    if args.action not in ["monitor", "status"]:
        print_header("RESULTADO FINAL")
        if success:
            print_success("Test completado exitosamente")
        else:
            print_error("Test falló")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
