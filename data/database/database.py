
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "household_database.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS households (
            household_id INTEGER PRIMARY KEY,
            family_size INTEGER,
            monthly_income REAL,
            employment_status TEXT,
            housing_type TEXT,
            water_access TEXT,
            electricity_access TEXT,
            senior_count INTEGER,
            pwd_count INTEGER
        )
    """)

    conn.commit()
    conn.close()

def save_households(df):
    conn = get_connection()

    df.to_sql(
        "households",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()

def read_households():
    conn = get_connection()

    df = __import__("pandas").read_sql_query(
        "SELECT * FROM households",
        conn
    )

    conn.close()
    return df
