import random
import time
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from urllib.parse import quote, urlparse, urlunparse

import requests
from Library import IPTV_Database, STK_Server, Settings, VLCPlayer, STATUS, EPG_Server, configure_vlc_parallel

from colorama import init, Fore, Style

import logging
logging.basicConfig(level=Settings.LOG_LEVEL, format=Settings.LOG_FORMAT)


def process_mac(db, url, mac):
    
    is_german = None
    is_adult = None 
    success = None
    success_message = ""
    # check if at least one random channel is working for MAC in a relevant genre
    with STK_Server(url, mac) as server:
        login_status, status_message = server.login()
        if login_status == STATUS.SUCCESS:
            logging.debug(f"Successfully logged in with MAC: {mac} for URL: {url}")
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
                                logging.debug(success_message)
                            continue

                        logging.debug(f"Processing genre [{relevantGenreCounter}/{Settings.MAX_FAILED_STATUS_ATTEMPTS}] '{genre.name}'...")

                        # get channels for the genre
                        status, message, channels = genre.get_channels()
                        if status == STATUS.SUCCESS:
                            if len(channels) == 0:
                                success = STATUS.CONTENT
                                success_message = f"No channels found for genre '{genre.name}'"
                                logging.debug(Fore.RED + success_message)
                            else:
                                # process 5 random channels from the genre
                                for i in range(Settings.MAX_FAILED_STATUS_ATTEMPTS):
                                    random_index = random.randint(0, len(channels) - 1)
                                    channel = channels[random_index]
                                    logging.debug(f"[{i+1}/{Settings.MAX_FAILED_STATUS_ATTEMPTS}] Channel '{channel.name}'.....")
                                    status, message = channel.validate_url()
                                    if status == STATUS.SUCCESS:
                                        success = STATUS.SUCCESS
                                        success_message = ""
                                        logging.debug("Channel is valid.")
                                        # exit the loop if a working channel was found
                                        break
                                    else:
                                        success = STATUS.ERROR
                                        success_message = f"Channel validation failed: {message}"
                                        logging.debug(success_message)
                        else:
                            success = STATUS.CONTENT
                            success_message = f"Failed to get channels for genre '{genre.name}': {message}"
                            logging.debug(success_message)                            


                # If no relevant genres were found, set success to CONTENT because no relevant genres were found    
                if success == None:
                    success = STATUS.CONTENT
                    success_message = f"No relevant genres found"
                    logging.debug(success_message)
            else:
                success = STATUS.CONTENT
                success_message = f"No genres found"
                logging.debug(success_message)
        else:
            success = login_status
            success_message = f"Login failed - Status: {login_status}, Message: {status_message}"

    return success, success_message, is_german, is_adult


def normalize_status(status_value):
    if isinstance(status_value, STATUS):
        return status_value.value
    return (status_value or "").strip().upper()


def main():
    init(autoreset=True)  # Initialize colorama

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check MACs for IPTV URLs')
    parser.add_argument('--url', type=str, help='Optional URL to check MACs for. If not provided, all URLs will be processed.')
    parser.add_argument('--process-all', action='store_true', help='Process all MACs regardless of finding a working one. By default, remaining MACs are skipped after finding a working MAC.')
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers for MAC checks (default: 10).')
    parser.add_argument('--vlc-workers', type=int, default=Settings.VLC_MAX_PARALLEL, help=f'Number of parallel VLC stream validations (default: {Settings.VLC_MAX_PARALLEL}).')
    parser.add_argument('--skip-login', action='store_true', help='Skip MACs already marked with status LOGIN.')
    parser.add_argument('--skip-error', action='store_true', help='Skip MACs already marked with status ERROR.')
    parser.add_argument('--skip-content', action='store_true', help='Skip MACs already marked with status CONTENT.')
    args = parser.parse_args()

    configure_vlc_parallel(args.vlc_workers)
    logging.info(f"VLC parallel validations: {max(1, args.vlc_workers)}")

    skip_statuses = set()
    if args.skip_login:
        skip_statuses.add(STATUS.LOGIN.value)
    if args.skip_error:
        skip_statuses.add(STATUS.ERROR.value)
    if args.skip_content:
        skip_statuses.add(STATUS.CONTENT.value)
    if skip_statuses:
        logging.info(f"Skipping MACs with existing status: {', '.join(sorted(skip_statuses))}")

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
                logging.warning("Available URLs in database:")
                for url in all_urls:
                    logging.warning(f"  - {url}")
                return
        else:
            urls = db.get_all_urls()

        # Iterate through each URL and fetch its MACs
        total_urls = len(urls)
        global_status_counts = {
            STATUS.SUCCESS.value: 0,
            STATUS.LOGIN.value: 0,
            STATUS.ERROR.value: 0,
            STATUS.CONTENT.value: 0,
            STATUS.SKIPPED.value: 0,
        }
        logging.info(f"Found {total_urls} URLs to process.")
        for urlCounter, url in enumerate(urls, start=1):
            URLPREFIX = f"URL[{urlCounter}/{total_urls}]"
            url_progress_percent = (urlCounter / total_urls) * 100 if total_urls else 100
            success = None
            status_counts = {
                STATUS.SUCCESS.value: 0,
                STATUS.LOGIN.value: 0,
                STATUS.ERROR.value: 0,
                STATUS.CONTENT.value: 0,
                STATUS.SKIPPED.value: 0,
            }
            logging.info(f"{Fore.CYAN}{URLPREFIX} ------------------------------------------------------------------------")
            logging.info(f"{Fore.CYAN}{URLPREFIX} ({url_progress_percent:.0f}%) {url}")
            

            # First check the newest working MAC for the URL
            mac_id = db.get_newest_working_mac_for_url(url)
            if mac_id:
                mac = db.get_mac_by_id(mac_id).mac
                logging.debug(f"{Fore.YELLOW}{URLPREFIX}Known good MAC check: {mac}")
                success, success_message, is_german, is_adult = process_mac(db, url, mac)
                logging.debug(f"{Fore.YELLOW}{URLPREFIX}Known good MAC result: {success}")
                db.update_mac_status(mac_id, success, success_message, is_german, is_adult)
                if success == STATUS.SUCCESS:
                    logging.info(f"{Fore.GREEN}{URLPREFIX} Known good MAC result: {success} - {success_message}")
                else:
                    logging.info(f"{Fore.RED}{URLPREFIX} Known good MAC result: {success} - {success_message}")

                # Processing the remaining MACs
                macs = db.get_all_other_macs_by_url(url, mac_id)
            else:
                macs = db.get_all_macs_by_url(url)

            if skip_statuses:
                original_count = len(macs)
                new_macs = []
                for macItem in macs:
                    if normalize_status(macItem.status) not in skip_statuses:
                        new_macs.append(macItem)
                    
                macs = new_macs
                filtered_out_count = original_count - len(macs)
                if filtered_out_count:
                    logging.info(
                        f"{Fore.YELLOW}{URLPREFIX} skipped by status filter: {filtered_out_count}"
                    )
            	
            total_macs = len(macs)
            logging.info(f"{Fore.WHITE}{URLPREFIX} MACs to check: {total_macs}, workers: {max(1, args.workers)}")

            if success == STATUS.SUCCESS and not args.process_all:
                for macCounter, macItem in enumerate(macs, start=1):
                    MACPREFIX = f"{URLPREFIX} MAC[{macCounter}/{total_macs}]"
                    mac_progress_percent = (macCounter / total_macs) * 100 if total_macs else 100
                    logging.info(f"{Fore.YELLOW}{MACPREFIX} ({mac_progress_percent:.0f}%) SKIP (already working): {macItem.mac}")
                    status_counts[STATUS.SKIPPED.value] += 1
                    db.update_mac_status(macItem.id, STATUS.SKIPPED, "")
            else:
                max_workers = max(1, args.workers)
                available_workers = deque(range(1, max_workers + 1))
                mac_entries = list(enumerate(macs, start=1))
                mac_iter = iter(mac_entries)
                futures = {}
                stop_submitting = False
                completed_macs = 0

                def submit_next():
                    try:
                        macCounter, macItem = next(mac_iter)
                    except StopIteration:
                        return False

                    if not available_workers:
                        return False

                    worker_id = available_workers.popleft()
                    MACPREFIX = f"{URLPREFIX} MAC[{macCounter}/{total_macs}]"
                    logging.debug(f"{Fore.CYAN}W{worker_id} START {url} {macItem.mac} (id={macItem.id}, failed={macItem.failed})")
                    future = executor.submit(process_mac, db, url, macItem.mac)
                    futures[future] = (macCounter, macItem, MACPREFIX, worker_id)
                    return True

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    while len(futures) < max_workers and submit_next():
                        pass

                    while futures:
                        for future in as_completed(list(futures.keys())):
                            macCounter, macItem, MACPREFIX, worker_id = futures.pop(future)
                            try:
                                result_success, success_message, is_german, is_adult = future.result()
                            except Exception as exc:
                                result_success = STATUS.ERROR
                                success_message = f"Unhandled error: {exc}"
                                is_german = None
                                is_adult = None

                            if result_success == STATUS.SUCCESS:
                                success = STATUS.SUCCESS
                                if not args.process_all:
                                    stop_submitting = True

                            completed_macs += 1
                            mac_progress_percent = (completed_macs / total_macs) * 100 if total_macs else 100
                            color = Fore.GREEN if result_success == STATUS.SUCCESS else (Fore.YELLOW if result_success == STATUS.SKIPPED else Fore.RED)
                            logging.info(f"{color}{MACPREFIX} ({completed_macs}/{total_macs}, {mac_progress_percent:.0f}%) -> {result_success} - {success_message}")
                            result_key = normalize_status(result_success)
                            if result_key in status_counts:
                                status_counts[result_key] += 1
                            db.update_mac_status(macItem.id, result_success, success_message, is_german, is_adult)
                            available_workers.append(worker_id)

                            if not stop_submitting:
                                submit_next()

                if stop_submitting and not args.process_all:
                    for macCounter, macItem in mac_iter:
                        completed_macs += 1
                        MACPREFIX = f"{URLPREFIX} MAC[{macCounter}/{total_macs}]"
                        mac_progress_percent = (completed_macs / total_macs) * 100 if total_macs else 100
                        logging.info(f"{Fore.YELLOW}{MACPREFIX} ({completed_macs}/{total_macs}, {mac_progress_percent:.0f}%) SKIP (already working): {macItem.mac}")
                        status_counts[STATUS.SKIPPED.value] += 1
                        db.update_mac_status(macItem.id, STATUS.SKIPPED, "")

            total_counted = sum(status_counts.values())
            for state, count in status_counts.items():
                global_status_counts[state] += count
            logging.info(
                f"{Fore.WHITE}{URLPREFIX} summary: "
                f"success={status_counts[STATUS.SUCCESS.value]}, "
                f"login={status_counts[STATUS.LOGIN.value]}, "
                f"error={status_counts[STATUS.ERROR.value]}, "
                f"content={status_counts[STATUS.CONTENT.value]}, "
                f"skipped={status_counts[STATUS.SKIPPED.value]}, "
                f"total={total_counted}"
            )

    # Calculate and log the total time taken
    end_time = time.time()
    total_time = end_time - start_time
    # Log the total time taken for processing in hours, minutes, and seconds
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    logging.info("------------------------------------------------")
    logging.info("Processing completed.")
    global_total_counted = sum(global_status_counts.values())
    logging.info(
        f"{Fore.WHITE}GLOBAL summary: "
        f"success={global_status_counts[STATUS.SUCCESS.value]}, "
        f"login={global_status_counts[STATUS.LOGIN.value]}, "
        f"error={global_status_counts[STATUS.ERROR.value]}, "
        f"content={global_status_counts[STATUS.CONTENT.value]}, "
        f"skipped={global_status_counts[STATUS.SKIPPED.value]}, "
        f"total={global_total_counted}"
    )
    logging.info(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    logging.info(f"Finished at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
    logging.info(f"Total time taken: {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds")

if __name__ == "__main__":
    main()