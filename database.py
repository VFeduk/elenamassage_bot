import sqlite3
from datetime import datetime, timedelta

def init_db():
    with sqlite3.connect("appointments.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                service TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                utm_source TEXT DEFAULT 'organic',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON appointments(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON appointments(date)")

def add_appointment(user_id, name, service, date, time, utm_source):
    with sqlite3.connect("appointments.db") as conn:
        conn.execute("""
            INSERT INTO appointments (user_id, name, service, date, time, utm_source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, service, date, time, utm_source))

def get_appointments_by_date(target_date):
    with sqlite3.connect("appointments.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT service, time FROM appointments WHERE date=?", (target_date,))
        return cur.fetchall()

def get_all_appointments():
    with sqlite3.connect("appointments.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, service, date, time FROM appointments")
        return cur.fetchall()

def get_stats():
    with sqlite3.connect("appointments.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT utm_source, COUNT(*) FROM appointments GROUP BY utm_source")
        return cur.fetchall()

def clear_old_appointments():
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect("appointments.db") as conn:
        conn.execute("DELETE FROM appointments WHERE date < ?", (today,))
