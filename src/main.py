"""OneDrive Business Monitor - Combined Entry Point.

Runs both the Monitor and Dashboard concurrently using asyncio.

Usage:
    uv run onedrive_business           # Run both monitor and dashboard
    uv run onedrive_business monitor   # Run only the monitor
    uv run onedrive_business dashboard # Run only the dashboard (with reload)
"""

import argparse
import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Fix module search path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Force UTF-8 for stdout/stderr on Windows
if os.name == "nt":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


async def run_monitor_async() -> None:
    """Run the monitor in a thread to not block the event loop."""
    from src.monitor.main import run_monitor
    import asyncio
    logger.info("🔍 Starting OneDrive Monitor...")
    try:
        # Pasar shutdown_event al monitor para cierre limpio
        loop = asyncio.get_running_loop()
        shutdown_event = getattr(loop, "_shutdown_event", None)
        await asyncio.to_thread(run_monitor, shutdown_event)
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        raise


async def run_dashboard_async(host: str = "0.0.0.0", port: int = 2048) -> None:
    """Run the FastAPI dashboard with uvicorn."""
    import uvicorn
    from src.dashboard.main import app
    
    logger.info(f"📊 Starting Dashboard on http://{host}:{port}")
    
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise


async def main() -> None:
    """Run both monitor and dashboard concurrently."""
    logger.info("=" * 60)
    logger.info("OneDrive Business Monitor - Starting All Services")
    logger.info("=" * 60)
    
    # Handle graceful shutdown
    shutdown_event = asyncio.Event()
    # Guardar shutdown_event en el loop para acceso desde run_monitor_async
    loop = asyncio.get_running_loop()
    loop._shutdown_event = shutdown_event
    
    def signal_handler():
        logger.info("\n⚠️ Shutdown signal received, stopping services...")
        shutdown_event.set()
    
    # Register signal handlers (Unix-style, works on Windows too via asyncio)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            signal.signal(sig, lambda s, f: signal_handler())
    
    try:
        # Run both services concurrently
        await asyncio.gather(
            run_monitor_async(),
            run_dashboard_async(),
            return_exceptions=True,
        )
    except asyncio.CancelledError:
        logger.info("Services cancelled")
    except Exception as e:
        logger.error(f"Error running services: {e}")
        raise
    finally:
        logger.info("Deteniendo procesos hijos de Python levantados por el monitor...")
        try:
            import psutil
            parent = psutil.Process()
            children = parent.children(recursive=True)
            for child in children:
                if child.name().lower().startswith("python"):
                    logger.info(f"Terminando proceso hijo Python PID={child.pid}")
                    child.terminate()
            gone, alive = psutil.wait_procs(children, timeout=5)
            for p in alive:
                logger.info(f"Forzando kill a proceso hijo Python PID={p.pid}")
                p.kill()
        except Exception as e:
            logger.warning(f"No se pudo terminar todos los procesos hijos: {e}")
        logger.info("✅ All services stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        from src.main_clean import clean_monitor_data
        clean_monitor_data()
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        sys.exit(1)


def cli() -> None:
    """CLI entry point for the package.
    
    Usage:
        uv run onedrive_monitor           # Run both monitor and dashboard
        uv run onedrive_monitor monitor   # Run only the monitor
        uv run onedrive_monitor dashboard # Run only the dashboard (with reload)
    """
    parser = argparse.ArgumentParser(
        prog="onedrive_monitor",
        description="OneDrive Business Monitor - Monitor and Dashboard",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["monitor", "dashboard", "clean"],
        default=None,
        help="Component to run: 'monitor', 'dashboard', 'clean', or omit for both",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=2048,
        help="Port for the dashboard (default: 2048)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for the dashboard (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload for dashboard",
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == "monitor":
            # Run only monitor
            logger.info("=" * 60)
            logger.info("OneDrive Business Monitor - Monitor Only")
            logger.info("=" * 60)
            from src.monitor.main import run_monitor
            run_monitor()

        elif args.command == "dashboard":
            # Run only dashboard with reload by default
            logger.info("=" * 60)
            logger.info(f"OneDrive Business Monitor - Dashboard Only")
            logger.info(f"URL: http://{args.host}:{args.port}")
            logger.info("=" * 60)
            import uvicorn
            uvicorn.run(
                "src.dashboard.main:app",
                host=args.host,
                port=args.port,
                reload=not args.no_reload,
                log_level="info",
            )

        elif args.command == "clean":
            from src.main_clean import clean_monitor_data
            clean_monitor_data()
            logger.info("Limpieza completada.")

        else:
            # Run both (default)
            asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
