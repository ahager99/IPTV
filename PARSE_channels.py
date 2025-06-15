import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


from Library import IPTV_Database, STATUS, STK_Server


def process_channels(db, genre):
    # get channels for the genre
    status, message, channels = genre.get_channels()
    success = STATUS.CONTENT
    if status == STATUS.SUCCESS:
        channelCounter = 0
        for channel in channels:
            channelCounter += 1
            logging.info("------------------------------------------------")
            logging.info(f"[{channelCounter}/{len(channels)}] Channel '{channel.name}'.....")
            status, message = channel.validate_url()
            if status == STATUS.SUCCESS:
                logging.info(f"Channel is valid.")
                success = STATUS.SUCCESS
            else:
                logging.info(f"Channel validation failed: {message}")
    else:
        logging.error(f"Failed to get channels for genre '{genre.name}': {message}")  

    return success




def process_macs(db, url):
    # Get all not failed MACs for the current URL
    macs = db.get_all_not_failed_macs_by_url(url)	
    macCounter = 0
    logging.info(f"Found {len(macs)} unprocessed / success / skipped / error MACs.")
    for id, mac, expiration, status, error, german, adult in macs:
        macCounter += 1
            
        with STK_Server(url, mac) as server:
            login_status, status_message = server.login()
            if login_status == STATUS.SUCCESS:
                logging.info(f"Successfully logged in with MAC: {mac} for URL: {url}")
                status, message, genres = server.get_genres()
                # default sucess status is CONTENT failed
                success = STATUS.CONTENT
                if status == STATUS.SUCCESS:
                    genreCounter = 0
                    for genre in genres:
                        genreCounter += 1
                        if genre.is_relevant():
                            logging.info(f"[{genreCounter}/{len(genres)}] Processing genre '{genre.name}'...") 

                            # Process channels for the genre
                            status  = process_channels(db, genre)
                            if status == STATUS.SUCCESS:
                                # if at least one working channel was found, set success to SUCCESS
                                success = STATUS.SUCCESS                                                      
                        else:
                            logging.info(f"[{genreCounter}/{len(genres)}] Skipped genre '{genre.name}'")
                else:
                    logging.warning(f"[{genreCounter}/{len(genres)}] Failed to get genres for MAC: {mac} on URL: {url}")

                # Update the MAC status to SUCCESS
                db.update_mac_status(id, success, "")
            else:
                logging.error(f"[{genreCounter}/{len(genres)}] Login failed for MAC: {mac} on URL: {url}. Status: {login_status}, Message: {status_message}")
                db.update_mac_status(id, STATUS.STATUS_LOGIN, status_message)



def main():

    with IPTV_Database() as db:
        # Get all URLs from the database
        urls = db.get_all_urls()

        # Iterate through each URL and fetch its MACs
        logging.info(f"Found {len(urls)} URLs in the database.")
        urlCounter = 0
        for url in urls:
            urlCounter += 1
            logging.info(f"Processing URL [{urlCounter}/{len(urls)}]: '{url}'")
            # Process macs for the current URL
            process_macs(db, url)
                
            logging.info("")  # Newline for better readability

if __name__ == "__main__":
    main()