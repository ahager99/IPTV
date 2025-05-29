import sqlite3
from Library import Settings

class IPTVDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(Settings.Settings.db_path)
        self.create_tables()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS macs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER,
                mac TEXT,
                expiration DATE,
                status TEXT,
                error TEXT,
                adult BOOLEAN,
                german BOOLEAN,
                FOREIGN KEY(url_id) REFERENCES urls(id),
                UNIQUE(url_id, mac)
            )
        """)
        self.conn.commit()


    def get_url_id(self, url):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM urls WHERE url = ?", (url,))
        result = cursor.fetchone()
        return result[0] if result else None
    

    def get_mac_id(self, url, mac):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE urls.url = ? AND macs.mac = ?
        """, (url, mac))
        result = cursor.fetchone()
        return result[0] if result else None
    

    # Update the status and error of a MAC by its ID
    def update_mac_status(self, mac_id, status, error=None, german=None, adult=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE macs
            SET status = ?, error = ?, german = ?, adult = ?
            WHERE id = ?
        """, (status, error, german, adult, mac_id))
        self.conn.commit()

    # Get all MACs for a given URL order by expiration date descending
    def get_all_macs_by_url(self, url):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id, macs.mac, macs.expiration, macs.status, macs.error, macs.adult, macs.german
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE urls.url = ?
            ORDER BY macs.expiration DESC
        """, (url,))
        return cursor.fetchall()
    
    def get_all_not_failed_macs_by_url(self, url):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id, macs.mac, macs.expiration, macs.status, macs.error, macs.adult, macs.german
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE (macs.status is null or macs.status IN ('SUCCESS', 'SKIPPED', 'ERROR'))
              AND urls.url = ?
            ORDER BY macs.expiration DESC
        """, (url,))
        return cursor.fetchall()


    # get all urls where is not MAC with status = 'SUCCESS'
    def get_urls_without_working_mac(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT urls.url
            FROM urls
            LEFT JOIN macs ON urls.id = macs.url_id AND macs.status = 'SUCCESS'
            WHERE macs.id IS NULL
        """)
        return [row[0] for row in cursor.fetchall()]

    # Get for each URL the newest MAC with status = 1
    def get_newest_working_mac_by_url(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT urls.url, macs.mac, macs.expiration, macs.german, macs.adult
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE macs.id IN (
                SELECT MAX(id)
                FROM macs
                WHERE macs.status = 'SUCCESS'
                GROUP BY url_id
            )
        """)
        return cursor.fetchall()

    
    
    # Get all URLs in the database
    def get_all_urls(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT url FROM urls")
        return [row[0] for row in cursor.fetchall()]


    def insert_url(self, url):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO urls (url) VALUES (?)", (url,))
        self.conn.commit()
        return self.get_url_id(url)


    def insert_mac(self, url, mac, expiration, status, error, german=None, adult=None):
        url_id = self.get_url_id(url)
        if url_id is None:
            # If the URL does not exist, insert it
            url_id = self.insert_url(url)
        self.conn.execute(
            "INSERT INTO macs (url_id, mac, expiration, status, error, german, adult) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url_id, mac, expiration, status, error, german, adult)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()