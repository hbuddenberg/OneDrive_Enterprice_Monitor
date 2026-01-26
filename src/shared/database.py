def get_monthly_incident_count(year: int = None, month: int = None) -> int:
    """Devuelve el número de incidentes críticos en el mes actual."""
    from datetime import datetime
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month
    incident_states = ("NOT_RUNNING", "ERROR", "PAUSED", "AUTH_REQUIRED", "NOT_FOUND")
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    # Crear la tabla si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL,
        message TEXT,
        is_change BOOLEAN DEFAULT 0
    )
    ''')
    conn.commit()
    try:
        cursor.execute('''
            SELECT COUNT(*) FROM status_history
            WHERE status IN (?, ?, ?, ?, ?)
            AND strftime('%Y', timestamp) = ?
            AND strftime('%m', timestamp) = ?
        ''', (*incident_states, str(year), f'{month:02d}'))
        count = cursor.fetchone()[0]
    except Exception:
        count = 0
    conn.close()
    return count
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_NAME = "onedrive_monitor.db"

def get_db_path() -> str:
    # Use the root of the project ideally, or relative to this file
    # Assuming this run from root
    return DB_NAME

def init_db():
    """Initialize the database table."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL,
        message TEXT,
        is_change BOOLEAN DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

def log_status(status: str, message: str, is_change: bool = False):
    """Log a status entry to the database."""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO status_history (timestamp, status, message, is_change)
        VALUES (?, ?, ?, ?)
        ''', (datetime.now(), status, message, is_change))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def get_recent_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get the most recent N history entries."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, timestamp, status, message, is_change
    FROM status_history
    ORDER BY id DESC
    LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_chart_data(limit: int = 288) -> List[Dict[str, Any]]:
    """Get data for the chart (approx 24h at 5min intervals = 288 points).
    Order by timestamp ASC for the chart.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # We want chronological order for the chart
    cursor.execute('''
    SELECT timestamp, status, message
    FROM (
        SELECT timestamp, status, message
        FROM status_history
        ORDER BY id DESC
        LIMIT ?
    )
    ORDER BY timestamp ASC
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_outage_start_time() -> Optional[datetime]:
    """Calculate the start time of the current outage based on DB history.
    
    Returns:
        Datetime of the first non-OK status after the last OK status.
        If system has never been OK, returns the first recorded timestamp.
        Returns None if the system was recently OK (no outage found in DB terms).
    """
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        # 1. Find last OK timestamp
        cursor.execute("SELECT timestamp FROM status_history WHERE status = 'OK' ORDER BY id DESC LIMIT 1")
        last_ok_row = cursor.fetchone()
        
        last_ok_ts = None
        if last_ok_row:
             # SQLite stores as string usually if not parsed. Default adapter might return string.
             # We should ensure we handle parsing.
             # But let's assume standard ISO string or datetime if parsed.
             # Safety: Use the string in the next query directly?
             last_ok_ts = last_ok_row[0]

        if last_ok_ts:
            # 2. Find first bad record AFTER last OK
            cursor.execute("SELECT timestamp FROM status_history WHERE timestamp > ? ORDER BY id ASC LIMIT 1", (last_ok_ts,))
            first_bad_row = cursor.fetchone()
            if first_bad_row:
                 return _parse_db_datetime(first_bad_row[0])
            else:
                 # No bad records after OK? Then we are not aware of an outage in DB history yet.
                 return None
        else:
            # 3. No OK ever found. Return the very first record.
            cursor.execute("SELECT timestamp FROM status_history ORDER BY id ASC LIMIT 1")
            first_row = cursor.fetchone()
            if first_row:
                return _parse_db_datetime(first_row[0])
            return None
            
    except Exception as e:
        print(f"DB Error calculating outage start: {e}")
        return None
    finally:
        conn.close()

def _parse_db_datetime(ts_val: Any) -> datetime:
    """Helper to parse datetime from DB."""
    if isinstance(ts_val, datetime):
        return ts_val
    # SQLite default is "YYYY-MM-DD HH:MM:SS" or similar
    try:
        # Try specialized format with microseconds if present
        return datetime.fromisoformat(ts_val)
    except ValueError:
        try:
             # Common fallback
             return datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
             return datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S")
