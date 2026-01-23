#!/usr/bin/env python
"""
Test completo de los 9 templates de email.

Envía un email de prueba por cada template HTML para verificar
que todos se renderizan correctamente.

Uso:
    python test_all_templates.py           # Envía los 9 emails
    python test_all_templates.py --preview # Solo muestra preview sin enviar
    python test_all_templates.py --single auth_required  # Envía solo uno
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
from src.shared.templates import (
    render_status_notification,
    render_resolution_notification,
    STATUS_TEMPLATES,
)


# Datos de prueba para cada template
TEST_DATA = {
    "AUTH_REQUIRED": {
        "emoji": "🔐",
        "description": "Autenticación Requerida",
        "message": "OneDrive requiere que inicie sesión nuevamente para continuar sincronizando.",
    },
    "ERROR": {
        "emoji": "❌",
        "description": "Error de Sincronización",
        "message": "Se detectó un error durante la sincronización. Error: Conexión perdida con el servidor.",
    },
    "NOT_RUNNING": {
        "emoji": "💀",
        "description": "OneDrive No Ejecutándose",
        "message": "El proceso OneDrive.exe no está ejecutándose en el sistema.",
    },
    "PAUSED": {
        "emoji": "⏸️",
        "description": "Sincronización Pausada",
        "message": "La sincronización de OneDrive está pausada. Los archivos no se están sincronizando.",
    },
    "SYNCING": {
        "emoji": "🔄",
        "description": "Sincronizando",
        "message": "Sincronizando 47 archivos... Subiendo: Documento.docx (2.3 MB)",
    },
    "OK": {
        "emoji": "✅",
        "description": "Todo Sincronizado",
        "message": "Todos los archivos están sincronizados y actualizados.",
    },
    "NOT_FOUND": {
        "emoji": "🔍",
        "description": "Cuenta No Encontrada",
        "message": "No se encontró el icono de OneDrive para la cuenta configurada en la bandeja del sistema.",
    },
    "UNKNOWN": {
        "emoji": "❓",
        "description": "Estado Desconocido",
        "message": "No se pudo determinar el estado actual de OneDrive.",
    },
    "RESOLVED": {
        "emoji": "✅",
        "description": "Problema Resuelto",
        "message": "El problema anterior ha sido resuelto. OneDrive está funcionando normalmente.",
    },
}


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_status(emoji: str, status: str, message: str) -> None:
    print(f"  {emoji} {status}: {message}")


def send_template_email(status: str, notifier: Notifier, config) -> bool:
    """Envía un email de prueba para un status específico."""
    data = TEST_DATA.get(status)
    if not data:
        print(f"  ❌ Status '{status}' no encontrado en TEST_DATA")
        return False
    
    account = config.target.email
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n  📧 Enviando: {data['emoji']} {status}")
    print(f"     Descripción: {data['description']}")
    
    try:
        if status == "RESOLVED":
            # Template especial de resolución
            outage_start = (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            outage_end = timestamp
            
            email_html = render_resolution_notification(
                account=account,
                outage_start=outage_start,
                outage_end=outage_end,
                duration="15m 0s"
            )
            subject = f"[Monitor OneDrive] ✅ RESUELTO - Problema Resuelto"
        else:
            # Templates normales de status
            email_html = render_status_notification(
                status=status,
                account=account,
                timestamp=timestamp,
                message=data["message"]
            )
            subject = f"[Monitor OneDrive] {data['emoji']} TEST: {status} - {data['description']}"
        
        # Enviar email con HTML
        success = notifier._send_email(subject, email_html, is_html=True)
        
        if success:
            print(f"     ✅ Enviado correctamente")
        else:
            print(f"     ❌ Error al enviar")
        
        return success
        
    except Exception as e:
        print(f"     ❌ Excepción: {e}")
        return False


def preview_template(status: str, config) -> None:
    """Muestra un preview del template sin enviar."""
    data = TEST_DATA.get(status)
    if not data:
        print(f"  ❌ Status '{status}' no encontrado")
        return
    
    account = config.target.email
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n  {data['emoji']} {status}")
    print(f"     Template: {STATUS_TEMPLATES.get(status, 'N/A')}")
    print(f"     Descripción: {data['description']}")
    print(f"     Mensaje: {data['message'][:50]}...")


def main():
    parser = argparse.ArgumentParser(
        description="Test completo de los 9 templates de email",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Solo mostrar preview sin enviar emails"
    )
    
    parser.add_argument(
        "--single", "-s",
        type=str,
        choices=list(TEST_DATA.keys()),
        help="Enviar solo un template específico"
    )
    
    parser.add_argument(
        "--delay", "-d",
        type=int,
        default=3,
        help="Segundos de espera entre emails (default: 3)"
    )
    
    args = parser.parse_args()
    
    config = get_config()
    notifier = Notifier()
    notifier._last_notification_time = None  # Bypass cooldown
    
    print_header("🧪 TEST COMPLETO DE TEMPLATES DE EMAIL")
    print(f"\n  Destinatario: {config.notifications.channels.email.to_email}")
    print(f"  Cuenta monitoreada: {config.target.email}")
    print(f"  Total templates: {len(TEST_DATA)}")
    
    if args.preview:
        print_header("PREVIEW DE TEMPLATES (sin enviar)")
        for status in TEST_DATA.keys():
            preview_template(status, config)
        print(f"\n  ℹ️  Use sin --preview para enviar los emails")
        return
    
    # Determinar qué templates enviar
    if args.single:
        templates_to_send = [args.single]
    else:
        templates_to_send = list(TEST_DATA.keys())
    
    print_header(f"ENVIANDO {len(templates_to_send)} EMAILS DE PRUEBA")
    
    results = []
    for i, status in enumerate(templates_to_send, 1):
        print(f"\n  [{i}/{len(templates_to_send)}] Procesando {status}...")
        success = send_template_email(status, notifier, config)
        results.append((status, success))
        
        # Esperar entre emails (excepto el último)
        if i < len(templates_to_send):
            print(f"     ⏳ Esperando {args.delay}s...")
            time.sleep(args.delay)
    
    # Resumen
    print_header("📊 RESUMEN DE RESULTADOS")
    
    passed = sum(1 for _, s in results if s)
    failed = len(results) - passed
    
    for status, success in results:
        data = TEST_DATA[status]
        icon = "✅" if success else "❌"
        print(f"  {icon} {data['emoji']} {status}: {data['description']}")
    
    print(f"\n  Total: {passed}/{len(results)} enviados correctamente")
    
    if failed > 0:
        print(f"  ⚠️  {failed} emails fallaron")
        sys.exit(1)
    else:
        print(f"  🎉 ¡Todos los emails enviados correctamente!")
        sys.exit(0)


if __name__ == "__main__":
    main()
