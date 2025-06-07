import random
import time
import subprocess
from urllib.parse import quote, urlparse, urlunparse

import requests
from Library import IPTVDatabase, STK_Server, VLCPlayer, STATUS, EPG


import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Reintroduce get_token for non-stalker portals
def get_token(session, url, mac_address):
    try:
        handshake_url = f"{url}/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml"
        cookies = {
            "mac": mac_address,
            "stb_lang": "en",
            "timezone": "Europe/London",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
                          "AppleWebKit/533.3 (KHTML, like Gecko) "
                          "MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
        }
        response = session.get(handshake_url, cookies=cookies, headers=headers, timeout=15)
        response.raise_for_status()
        token = response.json().get("js", {}).get("token")
        if token:
            logging.debug(f"Token retrieved: {token}")
            return token
        else:
            logging.debug("Token not found in handshake response.")
            return None
    except Exception as e:
        logging.debug(f"Error getting token: {e}")
        return None


def is_token_valid(token, token_timestamp):
    # Assuming token is valid for 10 minutes
    if token and (time.time() - token_timestamp) < 600:
        return True
    return False






def test_vlc_stream(url, timeout=10):
    vlc_path = "C:/Program Files/VideoLAN/VLC/vlc.exe"
    try:
        start_time = time.time()
        proc = subprocess.Popen(
            [vlc_path, "--intf", "dummy", "--play-and-exit", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            outs, errs = proc.communicate(timeout=timeout)
            exited_by_timeout = False
        except subprocess.TimeoutExpired:
            proc.terminate()
            outs, errs = proc.communicate()
            exited_by_timeout = True
        elapsed = time.time() - start_time

        # If VLC exited quickly (<3s), likely failed
        if elapsed < 3:
            return False
        # If there are error keywords AND VLC did not run long, treat as fail
        error_keywords = [
            "main error", "cannot open", "Your input can't be opened", "no suitable access module"
        ]
        if any(keyword.lower() in errs.lower() for keyword in error_keywords):
            logging.error(f"Erros when launch VLC for stream: {url}")
            return False
        return True
    except Exception as e:
        logging.error(f"Launching VLC for stream failed: {url}")
        return False

def is_stream_url_playable(url):
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            # Check for common stream types
            if any(ct in content_type for ct in [
                'video', 'audio', 'application/vnd.apple.mpegurl', 'application/x-mpegURL', 'appplication/octet-stream'
            ]):
                return True
        # Some servers may not support HEAD, try GET as fallback
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if any(ct in content_type for ct in [
                'video', 'audio', 'application/vnd.apple.mpegurl', 'application/x-mpegURL', 'appplication/octet-stream'
            ]):
                return True
    except Exception as e:
        pass

    return False

def launch_media_player(stream_url):
    # List of known prefixes to strip
    known_prefixes = ["ffmpeg ", "ffrt3 "]  # Add any other prefixes here

    # Strip any known prefix
    original_url = stream_url
    stream_url = stream_url.strip()  # Remove extra spaces
    for prefix in known_prefixes:
        if stream_url.lower().startswith(prefix.lower()):
            stream_url = stream_url[len(prefix):].strip()


    result2 = False

    # Log the final URL
    logging.debug(f"Launching media player with cleaned URL: {stream_url}")

    # Check if VLC can play the stream
    with VLCPlayer(stream_url) as vlc_player_instance:
        vlc_player_instance.play()
        for i in range(20):
            is_playing = vlc_player_instance.is_playing()
            playback_failed = vlc_player_instance.playback_failed()
            if is_playing or playback_failed:
                logging.debug(f"VLC playback status: is_playing={is_playing}, playback_failed={playback_failed}")
                break
            else:
                logging.debug(f"Waiting for VLC to start playing the stream: {stream_url} (attempt {i+1})")
                time.sleep(1)
        
        result = vlc_player_instance.is_playing()
        if result:
            logging.debug(f"VLC is playing the stream: {stream_url}")
            vlc_player_instance.stop()
        else:
            logging.debug(f"VLC is not playing the stream, attempting to play: {stream_url}")
            
#    result2 = test_vlc_stream(stream_url)
#    if result2 != result:
#        logging.error(f"VLC different results")
#        return False

    return result

def checkServer(hostname, mac_address):
    
    parsed_url = urlparse(hostname)
    if not parsed_url.scheme and not parsed_url.netloc:
        parsed_url = urlparse(f"http://{hostname}")
    elif not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme="http")

    base_url = urlunparse(
        (parsed_url.scheme, parsed_url.netloc, "", "", "", "")
    )
    
    # Non-stalker logic: use RequestThread
    session = requests.Session()
    token = get_token(session, base_url, mac_address)
    token_timestamp = time.time()

    if not token:
        return IPTVDatabase.STATUS_LOGIN, "Failed to retrieve token. Check MAC/URL.", None, None

    cookies = {
                "mac": mac_address,
                "stb_lang": "en",
                "timezone": "Europe/London",
                "token": token,
            }
    headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
                              "AppleWebKit/533.3 (KHTML, like Gecko) "
                              "MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
                "Authorization": f"Bearer {token}",
            }

    # Fetch profile and account info
    try:
        profile_url = f"{base_url}/portal.php?type=stb&action=get_profile&JsHttpRequest=1-xml"
        response_profile = session.get(profile_url, cookies=cookies, headers=headers, timeout=10)
        response_profile.raise_for_status()
        profile_data = response_profile.json()
    except Exception as e:
        return IPTVDatabase.STATUS_ERROR, f"Error fetching profile: {e}", None, None

    try:
        account_info_url = f"{base_url}/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
        response_account_info = session.get(account_info_url, cookies=cookies, headers=headers, timeout=10)
        response_account_info.raise_for_status()
        account_info_data = response_account_info.json()
    except Exception as e:
        return IPTVDatabase.STATUS_ERROR, f"Error fetching account info: {e}", None, None


    # Get live genres
    genres = None
    german_genres = []
    adult_genres = []
    try:
        genres_url = f"{base_url}/portal.php?type=itv&action=get_genres&JsHttpRequest=1-xml"
        response = session.get(genres_url, cookies=cookies, headers=headers, timeout=10)
        response.raise_for_status()
        genre_data = response.json().get("js", [])
        if genre_data:
            genres = [
                {
                    "name": i["title"],
                    "category_type": "IPTV",
                    "category_id": i["id"],
                }
                for i in genre_data
            ]
            genres.sort(key=lambda x: x["name"])

            # Check for German and Adult genres
            genre_text = ""
            for genre in genres:
                name_upper = genre["name"].upper()
                genre_text += name_upper + ", "
                if name_upper.startswith(("DE:", "DE ", "|DE|", "DE|", "GERMANY", "ALEMANHA")):
                    german_genres.append(genre)
                if name_upper.startswith(("[XXX]", "XXX")) or "ADULT" in name_upper or "XXX" in name_upper:
                    adult_genres.append(genre)
            logging.debug(f"Genres found: {genre_text}")
        else:
            return IPTVDatabase.STATUS_CONTENT, "No genres data found.", None, None
    except Exception as e:
        return IPTVDatabase.STATUS_ERROR, f"Error getting genres: {e}", None, None


    for i in range(5):
        if len(german_genres) > 0:
            random_index = random.randint(0, len(german_genres) - 1)
            genre = german_genres[random_index]
        elif len(adult_genres) > 0:
            random_index = random.randint(0, len(adult_genres) - 1)
            genre = adult_genres[random_index]
        else:
            random_index = random.randint(0, len(genres) - 1)
            genre = genres[random_index]
        logging.debug(f"Genre: {genre['name']}")

        # Get live channels
        try:
            channels = []
            category_id = genre["category_id"]
            initial_url = f"{base_url}/portal.php?type=itv&action=get_ordered_list&genre={category_id}&JsHttpRequest=1-xml&p=0"
            response = session.get(initial_url, cookies=cookies, headers=headers, timeout=10)
            response.raise_for_status()
            response_json = response.json()
            if len(response_json.get("js", {})) > 0:
                total_items = response_json.get("js", {}).get("total_items", 0)
                items_per_page = len(response_json.get("js", {}).get("data", []))
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 1
                channels_data = response_json.get("js", {}).get("data", [])
                for c in channels_data:
                    c["item_type"] = "channel"
                channels.extend(channels_data)

                # Fetch remaining pages in parallel
                pages_to_fetch = list(range(1, total_pages))
                if pages_to_fetch:
                    future_to_page = {}
                    for p in pages_to_fetch:
                        channels_url = f"{base_url}/portal.php?type=itv&action=get_ordered_list&genre={category_id}&JsHttpRequest=1-xml&p={p}"
                        logging.debug(f"Fetching page {p} URL: {channels_url}")
                        
                        response = session.get(channels_url, cookies=cookies, headers=headers, timeout=10)
                        response.raise_for_status()
                        response_json = response.json()
                        page_channels = response_json.get("js", {}).get("data", [])
                        for ch in page_channels:
                            ch["item_type"] = "channel"
                        
                        channels.extend(page_channels)

                # Remove duplicate channels based on 'id'
                unique_channels = {}
                for ch in channels:
                    cid = ch.get('id')
                    if cid and cid not in unique_channels:
                        unique_channels[cid] = ch
                channels = list(unique_channels.values())
                channels.sort(key=lambda x: x.get("name", ""))


                # check if some random channels are working
                if len(channels) > 0: 
                    random_chanel = random.randint(0, len(channels)-1)
                    channel = channels[random_chanel]       

                    
                    cmd = channel.get("cmd")
                    if not cmd:
                        # No command found for channel/episode
                        continue

                    needs_create_link = False
                    if "/ch/" in cmd and cmd.endswith("_"):
                        needs_create_link = True

                    if needs_create_link:
                        try:
                            url = base_url

                            # Refresh token if needed
                            if not is_token_valid(token, token_timestamp):
                                # Token is expired, get a new one
                                token = get_token(session, url, mac_address)
                                token_timestamp = time.time()
                                if not token:
                                    return IPTVDatabase.STATUS_TOKEN, "Failed to retrieve token. Please check your MAC address and URL.", None, None
                                    
                            cmd_encoded = quote(cmd)
                            cookies = {
                                "mac": mac_address,
                                "stb_lang": "en",
                                "timezone": "Europe/London",
                                "token": token,  # Include token in cookies
                            }
                            headers = {
                                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
                                            "AppleWebKit/533.3 (KHTML, like Gecko) "
                                            "MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
                                "Authorization": f"Bearer {token}",
                            }
                            create_link_url = f"{url}/portal.php?type=itv&action=create_link&cmd={cmd_encoded}&JsHttpRequest=1-xml"
                            response = session.get(
                                create_link_url,
                                cookies=cookies,
                                headers=headers,
                                timeout=10,
                            )
                            response.raise_for_status()
                            json_response = response.json()
                            cmd_value = json_response.get("js", {}).get("cmd")
                            if cmd_value:
                                if cmd.lower().startswith("ffmpeg"):
                                    cmd = cmd[6:].strip()
                                stream_url = cmd_value
                                if launch_media_player(stream_url):
                                    return IPTVDatabase.STATUS_SUCCESS, "Valid URL + MAC + working channels", len(german_genres) > 0, len(adult_genres) > 0 
                            else:
                                # Stream URL not found in the response.
                                continue
                        except Exception as e:
                            # Error creating stream link
                            continue
                    else:
                        # Strip 'ffmpeg ' prefix if present
                        if cmd.startswith("ffmpeg "):
                            cmd = cmd[len("ffmpeg "):]
                            
                        if launch_media_player(cmd):
                            return IPTVDatabase.STATUS_SUCCESS, "Valid URL + MAC + working channels", len(german_genres) > 0, len(adult_genres) > 0
                else:
                    # No channels found for this genre
                    return IPTVDatabase.STATUS_CONTENT, "No random channels data found.", None, None
            else:
                # No channels found for this genre
                return IPTVDatabase.STATUS_CONTENT, "No channels data found.", None, None

        except Exception as e:
            return IPTVDatabase.STATUS_ERROR, f"An error occurred while retrieving channels: {str(e)}", None, None

    return IPTVDatabase.STATUS_CONTENT, "No working channels found.", None, None



# db = IPTVDatabase()

# # Get all URLs from the database
# urls = db.get_all_urls()

# # Iterate through each URL and fetch its MACs
# logging.info(f"Found {len(urls)} URLs in the database.")
# urlCounter = 0
# for url in urls:
#     urlCounter += 1
#     macs = db.get_all_macs_by_url(url)	
    
#     # Print the URL and its MACs
#     logging.info(f"Processing URL [{urlCounter}/{len(urls)}]: '{url}' with {len(macs)} unprocessed / success / skipped / error MACs")
#     counter = 0
#     success = ""
#     for id, mac, expiration, status, error, german, adult in macs:
#         counter += 1
#         # Skip if MAC is already working
#         if success == IPTVDatabase.STATUS_SUCCESS:
#             logging.info(f"[{counter}/{len(macs)}] Skipping already working MAC: {mac} for URL: {url}")
#             db.update_mac_status(id, IPTVDatabase.STATUS_SKIPPED, "")
#         else:
#             success, message, german, adult = checkServer(url, mac)
#             logging.info(f"[{counter}/{len(macs)}] MAC: {mac}, Expiration: {expiration}, Status: {success}, Message: {message}")

#             db.update_mac_status(id, success, message, german, adult)

#             # if success then process next url as we only need one working MAC per URL
#             if success == IPTVDatabase.STATUS_SUCCESS:
#                 logging.info(f"Working MAC found: {mac} for URL: {url}")

        
#     logging.info("")  # Newline for better readability



def main():

    with IPTVDatabase() as db, EPG() as epg:
        # Get all URLs from the database
        urls = db.get_all_urls()

        # Iterate through each URL and fetch its MACs
        logging.info(f"Found {len(urls)} URLs in the database.")
        urlCounter = 0
        for url in urls:
            urlCounter += 1
            if urlCounter < 8:
                continue
            macs = db.get_all_not_failed_macs_by_url(url)	
            
            # Print the URL and its MACs
            logging.info(f"Processing URL [{urlCounter}/{len(urls)}]: '{url}' with {len(macs)} unprocessed / success / skipped / error MACs")
            macCounter = 0
            success = ""
            for id, mac, expiration, status, error, german, adult in macs:
                macCounter += 1
                # Skip if MAC is already working
                if success == STATUS.SUCCESS:
                    logging.info(f"[{macCounter}/{len(macs)}] Skipping already working MAC: {mac} for URL: {url}")
                    db.update_mac_status(id, IPTVDatabase.SKIPPED, "")
                else:
                    
                    with STK_Server(url, mac) as server:
                        login_status, status_message = server.login()
                        if login_status == STATUS.SUCCESS:
                            logging.info(f"Successfully logged in with MAC: {mac} for URL: {url}")
                            status, message, genres = server.get_genres()
                            if status == STATUS.SUCCESS:
                                genreCounter = 0
                                for genre in genres:
                                    genreCounter += 1
                                    if genre.is_relevant():
                                        logging.info(f"[{genreCounter}/{len(genres)}] Processing genre '{genre.name}'...") 

                                        # get channels for the genre
                                        status, message, channels = genre.get_channels()
                                        if status == STATUS.SUCCESS:
                                            channelCounter = 0
                                            for channel in channels:
                                                channelCounter += 1
                                                logging.info("------------------------------------------------")
                                                logging.info(f"[{channelCounter}/{len(channels)}] Channel '{channel.name}'.....")
                                                status, message = channel.validate_url()
                                                if status == STATUS.SUCCESS:
                                                    logging.info(f"Channel is valid.")
                                                    # Here you can add logic to process the channel further
                                                    epg_name, epg_display_name, epg_logo = epg.find_best_channel_id_match(channel.name, 89)
                                                    if epg_name:
                                                            logging.info(f"EPG name: {epg_name}")
                                                    else:
                                                            logging.info(f"No EPG matching")
                                                else:
                                                    logging.info(f"Channel validation failed: {message}")
                                        else:
                                            logging.error(f"Failed to get channels for genre '{genre.name}': {message}")                               
                                    else:
                                        logging.info(f"[{genreCounter}/{len(genres)}] Skipped genre '{genre.name}'")
                            else:
                                logging.warning(f"No genres found for MAC: {mac} on URL: {url}")
                        else:
                            logging.error(f"Login failed for MAC: {mac} on URL: {url}. Status: {login_status}, Message: {status_message}")
                            #db.update_mac_status(id, IPTVDatabase.STATUS_LOGIN, status_message)
                    
                    #success, message, german, adult = checkServer(url, mac)
                    #logging.info(f"[{counter}/{len(macs)}] MAC: {mac}, Expiration: {expiration}, Status: {success}, Message: {message}")

                    # db.update_mac_status(id, success, message, german, adult)

                    # # if success then process next url as we only need one working MAC per URL
                    # if success == IPTVDatabase.STATUS_SUCCESS:
                    #     logging.info(f"Working MAC found: {mac} for URL: {url}")

                
            logging.info("")  # Newline for better readability

if __name__ == "__main__":
    main()