import sqlite3
from datetime import datetime

DB_FILE = "history.db"

def init_db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            concentration REAL NOT NULL,
            matched_sample TEXT,
            confidence REAL,
            distance REAL,
            rgb_r REAL, rgb_g REAL, rgb_b REAL,
            hsv_h REAL, hsv_s REAL, hsv_v REAL,
            image_filename TEXT
        )
    """)
    con.commit(); con.close()

def save_measurement(result, image_filename):
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        INSERT INTO measurements
        (timestamp, concentration, matched_sample, confidence, distance,
         rgb_r, rgb_g, rgb_b, hsv_h, hsv_s, hsv_v, image_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        result["concentration"],
        result["matched_sample"],
        result["confidence_percent"],
        result["distance"],
        *result["measured_rgb"],
        *result["measured_hsv"],
        image_filename,
    ))
    con.commit(); con.close()

def get_measurements(start_date=None, end_date=None):
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    q = "SELECT * FROM measurements WHERE 1=1"
    params = []
    if start_date:
        q += " AND timestamp >= ?"; params.append(start_date)
    if end_date:
        q += " AND timestamp <= ?"; params.append(end_date)
    q += " ORDER BY timestamp ASC"
    rows = con.execute(q, params).fetchall()
    con.close()
    return [dict(r) for r in rows]
