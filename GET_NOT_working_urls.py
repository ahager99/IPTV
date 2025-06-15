import logging
from Library.Sqllite import IPTV_Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = IPTV_Database()

logging.info("Fetching not working URLs from the database...")
logging.info("------------------------------------------------")

not_working_macs = db.get_urls_without_working_mac()

# Print table header
logging.info('URL')
logging.info('-----------------------------------------------------------')

# Print each row
for url in not_working_macs:
    logging.info(f"{url}")

# Get amount of working compared to toal URLs in the database
all_urls = db.get_all_urls()
logging.info('-----------------------------------------------------------')
logging.info(f"{len(not_working_macs)} NOT working URLs of total {len(all_urls)} in the database.")

db.close()