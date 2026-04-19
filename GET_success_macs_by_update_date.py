import logging
from Library.Sqllite import IPTV_Database


logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler("success_macs_by_update_date.log", mode='w'), logging.StreamHandler()])


def main():
    db = IPTV_Database()

    header = f"{'URL':60} | {'MAC':17} | {'Expiration':12} | {'German':6} | {'Adult':5} | {'Last Update':19}"

    logging.info("")
    logging.info('#' * len(header))
    logging.info("")

    success_macs = db.get_all_success_macs_by_update_date()

    logging.info("SUCCESS MACS ORDERED BY LAST UPDATE (NEWEST FIRST)")
    logging.info(header)
    logging.info('-' * len(header))

    for url, mac, expiration, german, adult, last_updated in success_macs:
        logging.info(f"{url[:60]:60} | {mac:17} | {str(expiration):12} | {str(german):6} | {str(adult):5} | {str(last_updated):19}")

    all_urls = db.get_all_urls()
    logging.info('-' * len(header))
    logging.info(f"{len(success_macs)} SUCCESS MAC entries across {len(all_urls)} URLs in the database.")

    db.close()


if __name__ == '__main__':
    main()
