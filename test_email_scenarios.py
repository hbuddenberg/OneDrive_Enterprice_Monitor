#!/usr/bin/env python
"""
Test de escenarios de envío de correo electrónico.

Este script prueba los tres casos principales de notificación:
1. Al iniciar el monitor (estado actual)
2. Cuando ocurre un estado NO OK (AUTH_REQUIRED, ERROR, NOT_RUNNING, PAUSED)
3. Cuando se resuelve y vuelve a OK (notificación de resolución)

Uso:
    python test_email_scenarios.py startup      # Prueba email de inicio
    python test_email_scenarios.py error        # Prueba email de error (AUTH_REQUIRED)
    python test_email_scenarios.py resolution   # Prueba email de resolución
    python test_email_scenarios.py full         # Prueba ciclo completo (inicio -> error -> resolución)
    python test_email_scenarios.py all          # Ejecuta todas las pruebas individuales
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Fix module path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.shared.config import get_config
from src.shared.notifier import Notifier
from src.shared.schemas import OneDriveStatus


def print_header(title: str) -> None:
    """Imprime encabezado de sección."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(success: bool, message: str) -> None:
    """Imprime resultado de prueba."""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")


def get_notifier() -> Notifier:
    """Obtiene instancia de Notifier sin cooldown para pruebas."""
    notifier = Notifier()
    # Bypass cooldown para pruebas
    notifier._last_notification_time = None
    return notifier


def test_startup_notification() -> bool:
    """
    Prueba 1: Email al iniciar el monitor.
    
    Simula el envío de un email de estado inicial cuando el monitor arranca.
    Debería enviar el estado actual (puede ser OK o cualquier otro).
    """
    print_header("PRUEBA 1: Notificación de Inicio")
    
    config = get_config()
    notifier = get_notifier()
    
    # Simular estado inicial al arranque
    current_status = "OK"  # Estado típico al inicio
    account = config.target.email
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"  Cuenta: {account}")
    print(f"  Estado: {current_status}")
    print(f"  Hora: {timestamp}")
    print(f"  Enviando email de inicio...")
    
    subject = f"🚀 Monitor OneDrive Iniciado - {current_status}"
    message = f"""El Monitor OneDrive Empresarial ha iniciado.

Estado Actual: {current_status}
Cuenta Monitoreada: {account}
Hora de Inicio: {timestamp}

El sistema está activo y monitoreando la sincronización de OneDrive.
Recibirás notificaciones cuando ocurran cambios de estado importantes.

---
Monitor OneDrive Empresarial
"""
    
    try:
        success = notifier._send_email(subject, message)
        print_result(success, f"Email de inicio {'enviado correctamente' if success else 'FALLÓ'}")
        return success
    except Exception as e:
        print_result(False, f"Error al enviar: {e}")
        return False


def test_error_notification(status: str = "AUTH_REQUIRED") -> bool:
    """
    Prueba 2: Email cuando ocurre un estado NO OK.
    
    Simula la detección de un problema con OneDrive y el envío
    de la notificación de error correspondiente.
    """
    print_header(f"PRUEBA 2: Notificación de Error ({status})")
    
    config = get_config()
    notifier = get_notifier()
    
    account = config.target.email
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"  Cuenta: {account}")
    print(f"  Estado: {status}")
    print(f"  Hora: {timestamp}")
    print(f"  Enviando email de error...")
    
    # Usar el método del notifier para enviar notificación de error
    try:
        notifier.send_error_notification(
            status=status,
            outage_start_time=timestamp
        )
        print_result(True, "Email de error enviado correctamente")
        return True
    except Exception as e:
        print_result(False, f"Error al enviar: {e}")
        return False


def test_resolution_notification() -> bool:
    """
    Prueba 3: Email cuando se resuelve el problema (vuelve a OK).
    
    Simula que OneDrive volvió a funcionar correctamente después
    de un período de error.
    """
    print_header("PRUEBA 3: Notificación de Resolución")
    
    config = get_config()
    notifier = get_notifier()
    
    account = config.target.email
    # Simular que el problema duró 5 minutos
    outage_start = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    outage_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"  Cuenta: {account}")
    print(f"  Estado Anterior: AUTH_REQUIRED")
    print(f"  Estado Actual: OK")
    print(f"  Inicio del problema: {outage_start}")
    print(f"  Fin del problema: {outage_end}")
    print(f"  Duración: ~5 minutos")
    print(f"  Enviando email de resolución...")
    
    try:
        notifier.send_resolution_notification(
            outage_start_time=outage_start,
            outage_end_time=outage_end
        )
        print_result(True, "Email de resolución enviado correctamente")
        return True
    except Exception as e:
        print_result(False, f"Error al enviar: {e}")
        return False


def test_full_cycle() -> bool:
    """
    Prueba de ciclo completo: Inicio -> Error -> Resolución.
    
    Simula un ciclo completo de vida del monitor:
    1. El monitor inicia
    2. Se detecta un error
    3. El error se resuelve
    
    Incluye pequeñas pausas para simular el paso del tiempo.
    """
    print_header("PRUEBA COMPLETA: Ciclo Inicio → Error → Resolución")
    
    results = []
    
    # Paso 1: Inicio
    print("\n--- Paso 1/3: Inicio del Monitor ---")
    results.append(("Inicio", test_startup_notification()))
    
    print("\n⏳ Esperando 3 segundos (simulando operación normal)...")
    time.sleep(3)
    
    # Paso 2: Error
    print("\n--- Paso 2/3: Detección de Error ---")
    results.append(("Error", test_error_notification("AUTH_REQUIRED")))
    
    print("\n⏳ Esperando 3 segundos (simulando tiempo de error)...")
    time.sleep(3)
    
    # Paso 3: Resolución
    print("\n--- Paso 3/3: Resolución del Problema ---")
    results.append(("Resolución", test_resolution_notification()))
    
    # Resumen
    print_header("RESUMEN DEL CICLO COMPLETO")
    all_success = True
    for name, success in results:
        print_result(success, f"{name}")
        if not success:
            all_success = False
    
    return all_success


def test_all_error_states() -> bool:
    """
    Prueba todos los estados de error posibles.
    """
    print_header("PRUEBA: Todos los Estados de Error")
    
    error_states = ["AUTH_REQUIRED", "ERROR", "NOT_RUNNING", "PAUSED"]
    results = []
    
    for status in error_states:
        print(f"\n--- Probando {status} ---")
        success = test_error_notification(status)
        results.append((status, success))
        time.sleep(2)  # Pausa entre emails
    
    # Resumen
    print_header("RESUMEN DE ESTADOS DE ERROR")
    all_success = True
    for status, success in results:
        print_result(success, f"{status}")
        if not success:
            all_success = False
    
    return all_success


def show_config() -> None:
    """Muestra la configuración actual de notificaciones."""
    print_header("CONFIGURACIÓN ACTUAL")
    
    config = get_config()
    
    print(f"  Email Habilitado: {config.notifications.channels.email.enabled}")
    print(f"  Servidor SMTP: {config.notifications.channels.email.smtp_server}")
    print(f"  Puerto SMTP: {config.notifications.channels.email.smtp_port}")
    print(f"  Remitente: {config.notifications.channels.email.sender_email}")
    print(f"  Destinatario: {config.notifications.channels.email.to_email}")
    print(f"  Cuenta Monitoreada: {config.target.email}")
    print(f"  Cooldown: {config.notifications.cooldown_minutes} minutos")


def main():
    parser = argparse.ArgumentParser(
        description="Test de escenarios de envío de correo electrónico",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python test_email_scenarios.py startup      # Email de inicio
  python test_email_scenarios.py error        # Email de error (AUTH_REQUIRED)
  python test_email_scenarios.py resolution   # Email de resolución
  python test_email_scenarios.py full         # Ciclo completo
  python test_email_scenarios.py all_errors   # Todos los estados de error
  python test_email_scenarios.py config       # Ver configuración
        """
    )
    
    parser.add_argument(
        "test_type",
        choices=["startup", "error", "resolution", "full", "all_errors", "config"],
        help="Tipo de prueba a ejecutar"
    )
    
    parser.add_argument(
        "--status",
        default="AUTH_REQUIRED",
        choices=["AUTH_REQUIRED", "ERROR", "NOT_RUNNING", "PAUSED"],
        help="Estado de error a simular (solo para 'error')"
    )
    
    args = parser.parse_args()
    
    print("\n" + "🔔" * 20)
    print("   TEST DE NOTIFICACIONES POR EMAIL")
    print("🔔" * 20)
    
    show_config()
    
    success = True
    
    if args.test_type == "startup":
        success = test_startup_notification()
    
    elif args.test_type == "error":
        success = test_error_notification(args.status)
    
    elif args.test_type == "resolution":
        success = test_resolution_notification()
    
    elif args.test_type == "full":
        success = test_full_cycle()
    
    elif args.test_type == "all_errors":
        success = test_all_error_states()
    
    elif args.test_type == "config":
        pass  # Ya se mostró la config
    
    # Resultado final
    print_header("RESULTADO FINAL")
    if args.test_type != "config":
        print_result(success, "Todas las pruebas pasaron" if success else "Algunas pruebas fallaron")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
