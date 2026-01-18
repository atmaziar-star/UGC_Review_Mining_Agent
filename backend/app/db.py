"""Database setup and connection management."""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DATABASE_PATH = Path("reviews.db")


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    cursor = conn.cursor()

    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            total_reviews INTEGER DEFAULT 0
        )
    """)
    
    # Add filename column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN filename TEXT")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass

    # Reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            review_id TEXT,
            reviewer_name TEXT,
            review_title TEXT,
            review_content TEXT,
            rating INTEGER,
            review_date DATE,
            review_badge TEXT,
            product_url TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    # Job results table (stores analysis JSON)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_results (
            job_id TEXT PRIMARY KEY,
            results_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    # Database initialized successfully
