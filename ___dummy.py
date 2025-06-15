# add new column error to table macs
from Library.Sqllite import IPTV_Database


db = IPTV_Database()
db.conn.execute("""
    UPDATE macs SET failed = 0
""")    

db.conn.commit()
db.close()
