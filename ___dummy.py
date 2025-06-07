# add new column error to table macs
from Library.Sqllite import IPTVDatabase


db = IPTVDatabase()
db.conn.execute("""
    UPDATE macs SET failed = 0
""")    

db.conn.commit()
db.close()
