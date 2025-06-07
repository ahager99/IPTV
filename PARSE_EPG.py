import logging
from Library import EPG, IPTVDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    with EPG() as epg, IPTVDatabase() as db:
        channels = epg.channels
        if channels:
            logging.info(f"Found {len(channels)} channels in EPG.")
            for channel in channels:
                logging.info(f"Channel ID: {channel['id']}, Name: {channel['display_name']}, URL: {channel['url']}, Icon: {channel['icon']}")
        else:
            logging.warning("No channels found in EPG.")


if __name__ == "__main__":
    main()
