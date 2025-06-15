import logging
from Library.Sqllite import IPTV_Database

#logging.basicConfig(filename="working_macs.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = IPTV_Database()

logging.info("Fetching newest working MACs from the database...")
logging.info("------------------------------------------------")

working_macs = db.get_newest_working_mac_by_url()

# Print table header
header = f"{'URL':60} | {'MAC':17} | {'Expiration':12} | {'German':6} | {'Adult':5}"
logging.info(header)
logging.info('-' * len(header))

# Print each row
for url, mac, expiration, german, adult in working_macs:
    logging.info(f"{url[:60]:60} | {mac:17} | {str(expiration):12} | {str(german):6} | {str(adult):5}")

# Get amount of working compared to toal URLs in the database
all_urls = db.get_all_urls()
logging.info('-' * len(header))
logging.info(f"{len(working_macs)} working URLs of total {len(all_urls)} in the database.")

db.close()