import sqlite3
from datetime import datetime

from Library.Settings import STATUS, Settings


def main():
    conn = sqlite3.connect(Settings.DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(macs)")
        columns = {row[1] for row in cursor.fetchall()}
        if "last_updated" not in columns:
            cursor.execute("ALTER TABLE macs ADD COLUMN last_updated TEXT")
        cursor.execute(
            "UPDATE macs SET status = NULL, failed = 0, last_updated = ? WHERE status <> ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), STATUS.SUCCESS.value)
        )
        conn.commit()
        print(f"Reset completed. Updated {cursor.rowcount} MAC records.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
