import argparse
import logging
from Library.Sqllite import IPTV_Database


# Configure logging to write block format output with no prefix
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.FileHandler("working_macs_blocks.log", mode='w'), logging.StreamHandler()])


def normalize_status(status_value):
    return (status_value or "").strip().upper()


def main():
    parser = argparse.ArgumentParser(description='Output working MACs in block format')
    parser.add_argument('--show-error', action='store_true', help='Include MACs with status ERROR in output.')
    parser.add_argument('--show-content', '--show-conent', dest='show_content', action='store_true', help='Include MACs with status CONTENT in output.')
    parser.add_argument('--show-login', action='store_true', help='Include MACs with status LOGIN in output.')
    parser.add_argument('--show-skipped', action='store_true', help='Include MACs with status SKIPPED in output.')
    args = parser.parse_args()

    excluded_statuses = {'ERROR', 'CONTENT', 'LOGIN', 'SKIPPED'}
    if args.show_error:
        excluded_statuses.discard('ERROR')
    if args.show_content:
        excluded_statuses.discard('CONTENT')
    if args.show_login:
        excluded_statuses.discard('LOGIN')
    if args.show_skipped:
        excluded_statuses.discard('SKIPPED')

    db = IPTV_Database()

    logging.info("")
    logging.info("=" * 80)
    logging.info("WORKING MACS - BLOCK FORMAT")
    logging.info("=" * 80)
    logging.info("")

    if excluded_statuses:
        logging.info(f"Filtering out MAC output with status: {', '.join(sorted(excluded_statuses))}")
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

        visible_count = 0
        for mac_entry in db.get_all_macs_by_url(url):
            status = normalize_status(mac_entry[3])
            if status in excluded_statuses:
                continue
            logging.info(f"  - mac: {mac_entry[1]}, expiration: {mac_entry[2]}, status: {mac_entry[3]}, failed: {mac_entry[7]}")
            visible_count += 1

        if visible_count == 0:
            logging.info("  - no MACs to show after status filter")
        logging.info("")

    # Get amount of working compared to total URLs in the database
    all_urls = db.get_all_urls()
    logging.info("")
    logging.info("=" * 80)
    logging.info("SUMMARY")
    logging.info("=" * 80)
    logging.info(f"Working URLs: {len(working_macs)}")
    logging.info(f"Total URLs:   {len(all_urls)}")
    success_rate = (len(working_macs) / len(all_urls) * 100) if all_urls else 0
    logging.info(f"Success Rate: {success_rate:.2f}%")
    logging.info("=" * 80)

    db.close()

if __name__ == '__main__':
    main()
