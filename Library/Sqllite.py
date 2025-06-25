import sqlite3
from collections import namedtuple

from Library.Settings import STATUS, Settings



class IPTV_Database:

    def __namedtuple_factory(self, cursor, row):
        fields = [col[0] for col in cursor.description]
        Row = namedtuple('Row', fields)
        return Row(*row)


    def __init__(self):
        self.conn = sqlite3.connect(Settings.DB_PATH)
        self.conn.row_factory = self.__namedtuple_factory
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
                failed INTEGER DEFAULT 0,
                FOREIGN KEY(url_id) REFERENCES urls(id),
                UNIQUE(url_id, mac)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_id INTEGER,
                stream_id INTEGER,
                name TEXT,
                logo TEXT,
                german BOOLEAN,
                adult BOOLEAN, 
                austrian BOOLEAN,
                FOREIGN KEY(mac_id) REFERENCES macs(id),
                FOREIGN KEY(stream_id) REFERENCES streams(id),
                UNIQUE(mac_id, name)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS streams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                failed INTEGER DEFAULT 0,
                UNIQUE(url)
            )
        """)
        self.conn.commit()


    def get_clean_url(self, url):
        # Ensure no trailing slash
        if url.endswith('/'):
            url = url[:-1]
        return url


    def get_url_id(self, url):

        url = self.get_clean_url(url)

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM urls WHERE url = ?", (url,))
        result = cursor.fetchone()
        return result[0] if result else None
    

    def get_mac_id(self, url, mac):

        url = self.get_clean_url(url)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE urls.url = ? AND macs.mac = ?
        """, (url, mac))
        result = cursor.fetchone()
        return result[0] if result else None
    

    # get failed attempts for a MAC
    def get_failed_attempts(self, mac_id):
        if mac_id is not None:
            cursor = self.conn.cursor()
            cursor.execute("SELECT failed FROM macs WHERE id = ?", (mac_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        return 0


    # Update the status and error of a MAC by its ID
    def update_mac_status(self, mac_id, status, error=None, german=None, adult=None):

        failed = 0
        if status != STATUS.SUCCESS and status != STATUS.SKIPPED:
            failed = self.get_failed_attempts(mac_id) + 1
        
        status_value = status.value if status is not None else None

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE macs
            SET status = ?, error = ?, german = ?, adult = ?, failed = ?
            WHERE id = ?
        """, (status_value, error, german, adult, failed, mac_id, ))
        self.conn.commit()

    # Get all MACs for a given URL order by expiration date descending
    def get_all_macs_by_url(self, url):

        url = self.get_clean_url(url)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id, macs.mac, macs.expiration, macs.status, macs.error, macs.adult, macs.german
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE urls.url = ?
            ORDER BY macs.expiration DESC
        """, (url,))
        return cursor.fetchall()
    

    def get_all_other_macs_by_url(self, url, mac_id):

        url = self.get_clean_url(url)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id, macs.mac, macs.expiration, macs.status, macs.error, macs.adult, macs.german
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE urls.url = ?
            AND macs.failed < ?
            AND macs.id != ?
            ORDER BY macs.expiration DESC
        """, (url, Settings.MAX_FAILED_STATUS_ATTEMPTS, mac_id))
        return cursor.fetchall()
    
    
    def get_all_not_success_macs_by_url(self, url):

        url = self.get_clean_url(url)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT macs.id, macs.mac, macs.expiration, macs.status, macs.error, macs.adult, macs.german
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE urls.url = ?
            AND macs.failed < ?
            AND macs.status != ?
            ORDER BY macs.expiration DESC
        """, (url, Settings.MAX_FAILED_STATUS_ATTEMPTS, STATUS.SUCCESS.value))
        return cursor.fetchall()


    # get all urls where is not MAC with status = 'SUCCESS'
    def get_urls_without_working_mac(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT urls.url
            FROM urls
            LEFT JOIN macs ON urls.id = macs.url_id AND macs.status = ?
            WHERE macs.id IS NULL
        """, (STATUS.SUCCESS.value,))
        return [row[0] for row in cursor.fetchall()]


    def get_newest_working_mac_for_url(self, url):
        cursor = self.conn.cursor()
        # Status constants

        cursor.execute("""
            SELECT macs.id
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE macs.id IN (
            SELECT MAX(id)
            FROM macs
            WHERE macs.status = ?
            GROUP BY url_id
            )
            AND urls.url = ?
        """, (STATUS.SUCCESS.value, url))

        result = cursor.fetchone()
        if result:
            return result[0]

        return None


    # get mac by id
    def get_mac_by_id(self, mac_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT macs.id, macs.mac, macs.expiration, macs.status, macs.error, macs.adult, macs.german FROM macs WHERE id = ?", (mac_id,))
        return cursor.fetchone()

    # Get for each URL the newest MAC with status = 1
    def get_url_and_newest_working_mac(self):
        cursor = self.conn.cursor()
        # Status constants

        cursor.execute(f"""
            SELECT urls.url, macs.mac, macs.expiration, macs.german, macs.adult
            FROM macs
            JOIN urls ON macs.url_id = urls.id
            WHERE macs.id IN (
            SELECT MAX(id)
            FROM macs
            WHERE macs.status = ?
            GROUP BY url_id
            )
            ORDER BY urls.url
        """, (STATUS.SUCCESS.value,))
        return cursor.fetchall()

    
    # Get all URLs in the database
    def get_all_urls(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT url FROM urls")
        return [row[0] for row in cursor.fetchall()]


    def insert_url(self, url):

        url = self.get_clean_url(url)

        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO urls (url) VALUES (?)", (url,))
        self.conn.commit()
        return self.get_url_id(url)


    def insert_mac(self, url, mac, expiration, status, error, german=None, adult=None):
        
        url = self.get_clean_url(url)
        
        url_id = self.get_url_id(url)
        if url_id is None:
            # If the URL does not exist, insert it
            url_id = self.insert_url(url)
        
        status_value = status.value if status is not None else None
        
        self.conn.execute(
            "INSERT INTO macs (url_id, mac, expiration, status, error, german, adult) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url_id, mac, expiration, status_value, error, german, adult)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()