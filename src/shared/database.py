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
