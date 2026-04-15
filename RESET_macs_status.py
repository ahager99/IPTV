import sqlite3

from Library.Settings import STATUS, Settings


def main():
    conn = sqlite3.connect(Settings.DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE macs SET status = NULL, failed = 0 WHERE status <> ?", (STATUS.SUCCESS.value,))
        conn.commit()
        print(f"Reset completed. Updated {cursor.rowcount} MAC records.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
