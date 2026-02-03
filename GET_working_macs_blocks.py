import logging
from Library.Sqllite import IPTV_Database


# Configure logging to write block format output with no prefix
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.FileHandler("working_macs_blocks.log", mode='w'), logging.StreamHandler()])


db = IPTV_Database()

logging.info("")
logging.info("=" * 80)
logging.info("WORKING MACS - BLOCK FORMAT")
logging.info("=" * 80)
logging.info("")

working_macs = db.get_url_and_newest_working_mac()

# Print each entry as a block
for index, (url, mac, expiration, german, adult) in enumerate(working_macs, 1):
    logging.info(f"Entry #{index}")
    logging.info("-" * 80)
    logging.info(f"URL:        {url}")
    logging.info(f"MAC:        {mac}")
    logging.info(f"Expiration: {expiration}")
    logging.info(f"German:     {german}")
    logging.info(f"Adult:      {adult}")
    logging.info("=" * 80)
    logging.info("")
    logging.info("All working MACs for this URL:")
    for mac in db.get_all_macs_by_url(url):
        logging.info(f"  - mac: {mac[1]}, expiration: {mac[2]}, status: {mac[3]}, failed: {mac[7]}")
    logging.info("")

# Get amount of working compared to total URLs in the database
all_urls = db.get_all_urls()
logging.info("")
logging.info("=" * 80)
logging.info("SUMMARY")
logging.info("=" * 80)
logging.info(f"Working URLs: {len(working_macs)}")
logging.info(f"Total URLs:   {len(all_urls)}")
logging.info(f"Success Rate: {len(working_macs)/len(all_urls)*100:.2f}%")
logging.info("=" * 80)

db.close()
