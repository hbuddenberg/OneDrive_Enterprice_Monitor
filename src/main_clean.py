import os
from pathlib import Path

def clean_monitor_data():
    """Elimina la base de datos y el archivo de estado actual del monitor."""
    db_path = Path("onedrive_monitor.db")
    status_path = Path("status.json")
    removed = []
    for path in [db_path, status_path]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    print("Archivos eliminados:", removed if removed else "Nada que limpiar.")

if __name__ == "__main__":
    clean_monitor_data()
