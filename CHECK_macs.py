import random
import time
import subprocess
import argparse
from urllib.parse import quote, urlparse, urlunparse

import requests
from Library import IPTV_Database, STK_Server, Settings, VLCPlayer, STATUS, EPG_Server

from colorama import init, Fore, Style

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def process_mac(db, url, mac):
    
    is_german = None
    is_adult = None 
    success = None
    success_message = ""
    # check if at least one random channel is working for MAC in a relevant genre
    with STK_Server(url, mac) as server:
        login_status, status_message = server.login()
        if login_status == STATUS.SUCCESS:
            logging.info(f"Successfully logged in with MAC: {mac} for URL: {url}")
            status, message, genres = server.get_genres()
            if status == STATUS.SUCCESS and genres:
                relevantGenreCounter = 0
                for genre in genres:
                    is_german = genre.is_german() or is_german
                    is_adult = genre.is_adult() or is_adult
                    # skip genre if working channel was already found with previous genre
                    # process genre if it is relevant
                    if genre.is_relevant() and success != STATUS.SUCCESS:
                        # if still no success but MAX_FAILED_STATUS_ATTEMPTS is reached, the set to failed content and 
                        # do not process any channels for the remaining genres
                        relevantGenreCounter += 1
                        if relevantGenreCounter > Settings.MAX_FAILED_STATUS_ATTEMPTS:
                            if success == None:
                                success = STATUS.CONTENT
                                success_message = f"Reached maximum attempts for genre. "
                                logging.error(success_message)
                            continue

                        logging.info(f"{Fore.LIGHTBLUE_EX}Processing genre [{relevantGenreCounter}/{Settings.MAX_FAILED_STATUS_ATTEMPTS}] '{genre.name}'...")

                        # get channels for the genre
                        status, message, channels = genre.get_channels()
                        if status == STATUS.SUCCESS:
                            if len(channels) == 0:
                                success = STATUS.CONTENT
                                success_message = f"No channels found for genre '{genre.name}'"
                                logging.error(Fore.RED + success_message) 
                            else:
                                # process 5 random channels from the genre
                                for i in range(Settings.MAX_FAILED_STATUS_ATTEMPTS):
                                    random_index = random.randint(0, len(channels) - 1)
                                    channel = channels[random_index]
                                    logging.info(f"{Fore.CYAN}[{i+1}/{Settings.MAX_FAILED_STATUS_ATTEMPTS}] Channel '{channel.name}'.....")
                                    status, message = channel.validate_url()
                                    if status == STATUS.SUCCESS:
                                        success = STATUS.SUCCESS
                                        success_message = ""
                                        logging.info(f"{Fore.GREEN}Channel is valid.")
                                        # exit the loop if a working channel was found
                                        break
                                    else:
                                        success = STATUS.ERROR
                                        success_message = f"Channel validation failed: {message}"
                                        logging.info(Fore.RED + success_message)
                        else:
                            success = STATUS.CONTENT
                            success_message = f"Failed to get channels for genre '{genre.name}': {message}"
                            logging.info(Fore.RED + success_message)                            


                # If no relevant genres were found, set success to CONTENT because no relevant genres were found    
                if success == None:
                    success = STATUS.CONTENT
                    success_message = f"No relevant genres found"
                    logging.info(Fore.RED +success_message)
            else:
                success = STATUS.CONTENT
                success_message = f"No genres found"
                logging.info(Fore.RED + success_message)
        else:
            success = login_status
            success_message = f"Login failed - Status: {login_status}, Message: {status_message}"

    return success, success_message, is_german, is_adult


def main():
    init(autoreset=True)  # Initialize colorama

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check MACs for IPTV URLs')
    parser.add_argument('--url', type=str, help='Optional URL to check MACs for. If not provided, all URLs will be processed.')
    parser.add_argument('--process-all', action='store_true', help='Process all MACs regardless of finding a working one. By default, remaining MACs are skipped after finding a working MAC.')
    args = parser.parse_args()

    # Remember start time
    start_time = time.time()


    with IPTV_Database() as db:
        # Get all URLs from the database or filter by provided URL
        if args.url:
            # Check if the provided URL exists in the database
            all_urls = db.get_all_urls()
            if args.url in all_urls:
                urls = [args.url]
                logging.info(f"Processing specific URL: {args.url}")
            else:
                logging.error(f"URL '{args.url}' not found in the database.")
                logging.info(f"Available URLs in database:")
                for url in all_urls:
                    logging.info(f"  - {url}")
                return
        else:
            urls = db.get_all_urls()

        # Iterate through each URL and fetch its MACs
        logging.info(f"Found {len(urls)} URLs to process.")
        urlCounter = 0
        for url in urls:
            urlCounter += 1
            URLPREFIX = f"URL[{urlCounter}/{len(urls)}] "
            success = None
            logging.info("")
            logging.info("")
            logging.info(f"{Fore.WHITE}#################################################")
            logging.info(f"Processing {URLPREFIX}'{url}'")
            

            # First check the newest working MAC for the URL
            mac_id = db.get_newest_working_mac_for_url(url)
            if mac_id:
                logging.info(f"{Fore.YELLOW}{URLPREFIX}------------------------------------------------")
                mac = db.get_mac_by_id(mac_id).mac
                logging.info(f"{URLPREFIX}Checking already known success MAC: '{mac}'")
                success, success_message, is_german, is_adult = process_mac(db, url, mac)
                logging.info(f"{Fore.YELLOW}{URLPREFIX}Final result for MAC: {success} - {success_message}, is_german: {is_german}, is_adult: {is_adult}")
                db.update_mac_status(mac_id, success, success_message, is_german, is_adult)

                # Processing the remaining MACs
                macs = db.get_all_other_macs_by_url(url, mac_id)
            else:
                macs = db.get_all_macs_by_url(url)
            	
            logging.info(f"{Fore.WHITE}{URLPREFIX}'{url}' with {len(macs)} unprocessed / success / skipped / error MACs")
            macCounter = 0
            for macItem in macs:
                logging.info(f"{Fore.YELLOW}------------------------------------------------")
                macCounter += 1
                MACPREFIX = f"{URLPREFIX} MAC[{macCounter}/{len(macs)}]"
                logging.info(f"URL: {url}")
                logging.info(f"{MACPREFIX} Processing {macItem.mac}: ID={macItem.id}, FAILED={macItem.failed}")

                # Skip if a previous MAC is already working (unless --process-all is set)
                if success == STATUS.SUCCESS and not args.process_all:
                    logging.info(f"{Fore.YELLOW}{MACPREFIX} Skipping already working MAC: {macItem.mac} for URL: {url}")
                    db.update_mac_status(macItem.id, STATUS.SKIPPED, "")
                else:
                    # Process the MAC
                    success, success_message, is_german, is_adult = process_mac(db, url, macItem.mac)

                    # Update the MAC status in the database
                    color = Fore.GREEN if success == STATUS.SUCCESS else (Fore.YELLOW if success == STATUS.SKIPPED else Fore.RED)
                    logging.info(f"{color}{MACPREFIX} Final result for MAC: {success} - {success_message}, is_german: {is_german}, is_adult: {is_adult}")
                    db.update_mac_status(macItem.id, success, success_message, is_german, is_adult)

            # Newline for better readability after URL processing    
            logging.info("") 
            logging.info("")

    # Calculate and log the total time taken
    end_time = time.time()
    total_time = end_time - start_time
    # Log the total time taken for processing in hours, minutes, and seconds
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    logging.info("------------------------------------------------")
    logging.info("Processing completed.")
    logging.info(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    logging.info(f"Finished at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
    logging.info(f"Total time taken: {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds")

if __name__ == "__main__":
    main()