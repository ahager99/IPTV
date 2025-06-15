# class to handle the stalker functionality
import logging
import re
import subprocess
import time
from urllib.parse import quote, urlparse, urlunparse

import requests
from Library.Settings import STATUS
from Library.vlc_player import VLCPlayer



class STK_Channel:
    def __init__(self, genre, name, cmd, logo):
        self.genre = genre
        self.name = name
        self.cmd = cmd
        self.logo = logo
        self.channel_url = None
        self.real_url = None


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


    def __getitem__(self, key):
        return getattr(self, key)
    

    def __test_vlc_stream(url, timeout=10):
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

    def __is_stream_url_playable(url):
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
    

    def __load_real_stream_url(self):
        logging.debug("Fetching real url...")
        if not self.channel_url:
            self.real_url = None
            return STATUS.ERROR, "No channel url set"

        try:
            headers = {
            'User-Agent': 'Mozilla/5.0'
            }

            # Step 1: Send a GET request to the PHP proxy
            response = requests.get(self.channel_url, headers=headers, stream=True, allow_redirects=True)

            # Step 2: Check if the real URL is in the headers (e.g., via a Location redirect)
            if response.history:
                logging.debug("[*] Redirect chain detected:")
                for resp in response.history:
                    logging.debug(" →", resp.url)
                logging.debug("[*] Final URL:", response.url)
                self.real_url = response.url.strip()
                return STATUS.SUCCESS, ""

            # Step 3: Check for URL in the content (e.g., m3u8, mpd, etc.)
            content_type = response.headers.get('Content-Type', '')
            if 'application/vnd.apple.mpegurl' in content_type or '.m3u8' in response.text:
                # Look for .m3u8 or similar URL in body
                urls = re.findall(r'(https?://[^\s"\']+\.m3u8)', response.text)
                if urls:
                    logging.debug("[*] Stream URL found in response body")
                    self.real_url = urls[0].strip()
                    return STATUS.SUCCESS, ""

            logging.debug("[!] Could not find real stream URL in headers or body")
            self.real_url = None
            return STATUS.ERROR, "Could not find real stream URL in headers or body"

        except Exception as e:
            logging.debug(f"[!] Error: {e}")
            self.real_url = None
            return STATUS.ERROR, f"Error at fetching real stream URL: {e}"
    

    def get_url(self):
        # Get the channel url - preferred the real url or if not possible the url stored in channel
        if self.real_url:
            stream_url = self.real_url
        else:
            if not self.channel_url:
                status, message = self.load_stream_url()
                if status != STATUS.SUCCESS:
                    return status, message, None
        
            status, message = self.__load_real_stream_url()
            if status == STATUS.SUCCESS:
                stream_url = self.real_url  # Remove extra spaces
            else:
                stream_url = self.channel_url.strip()
        
        return STATUS.SUCCESS, "", stream_url



    def validate_url(self):

        # get the stream URL
        status, message, stream_url = self.get_url()
        if status != STATUS.SUCCESS:
            return status, message
        
        # List of known prefixes to strip
        known_prefixes = ["ffmpeg ", "ffrt3 "]  # Add any other prefixes here

        # Strip any known prefix
       
        for prefix in known_prefixes:
            if stream_url.lower().startswith(prefix.lower()):
                stream_url = stream_url[len(prefix):].strip()


        result2 = False

        # Log the final URL
        logging.info(f"Channel URL: {self.channel_url}")
        logging.info(f"Real URL: {self.real_url}")
        logging.info(f"Launching media player with cleaned URL: {stream_url}")

        # Check if VLC can play the stream
        with VLCPlayer(stream_url) as vlc_player_instance:
            vlc_player_instance.play()
            for i in range(5):
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
                vlc_player_instance.stop()
                return STATUS.SUCCESS, f"VLC is playing the stream"
            else:
                return STATUS.ERROR, f"VLC is not playing the stream"



    def load_stream_url(self):
        cmd = self.cmd
        if not cmd:
            # No command found for channel/episode
            return STATUS.ERROR, "No command found for channel/episode"

        needs_create_link = False
        if "/ch/" in cmd and cmd.endswith("_"):
            needs_create_link = True

        if needs_create_link:
            try:
                url = self.genre.server.base_url
                mac_address = self.genre.server.mac_address

                # Refresh token if needed
                status, message = self.genre.server.validate_token()
                if status != STATUS.SUCCESS:
                    return status, message
                token = self.genre.server.token
                
                                
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
                response = self.genre.server.session.get(
                    create_link_url,
                    cookies=self.genre.server.cookies,
                    headers=self.genre.server.headers,
                    timeout=10,
                )
                response.raise_for_status()
                json_response = response.json()
                cmd_value = json_response.get("js", {}).get("cmd")
                if cmd_value:
                    if cmd.lower().startswith("ffmpeg"):
                        cmd = cmd[6:].strip()
                    self.channel_url = cmd_value
                else:
                    # Stream URL not found in the response.
                    return STATUS.ERROR, "No stream URL found for channel/episode"
            except Exception as e:
                # Error creating stream link
                return STATUS.ERROR, "Error creating stream link: " + str(e)
        else:
            # Strip 'ffmpeg ' prefix if present
            if cmd.startswith("ffmpeg "):
                cmd = cmd[len("ffmpeg "):]
                
            self.channel_url = cmd 

        return STATUS.SUCCESS, "" 
 


class STK_Genre:
    def __init__(self, server, name, category_type, catgeory_id):
        self.server = server
        self.name = name.upper()
        self.category_type = category_type
        self.category_id = catgeory_id

    def __getitem__(self, key):
        return getattr(self, key)

    def is_german(self):
        return self.name.startswith(("DE:", "DE ", "|DE|", "DE|", "GERMANY", "ALEMANHA")) or \
                "GERMANY" in self.name
    
    def is_austrian(self):
        return self.name.startswith(("AT:", "AT ", "|AT|", "AT|", "AUSTRIA")) or \
                "AUSTRIA" in self.name
    
    def is_adult(self):
        return self.name.startswith(("[XXX]", "XXX")) or \
                "ADULT" in self.name or \
                "XXX" in self.name

    def is_relevant(self):
        return (self.is_adult() or self.is_german() or self.is_austrian())
    

    def get_channels(self):
        # Get live channels
        try:
            channels = []
            initial_url = f"{self.server.base_url}/portal.php?type=itv&action=get_ordered_list&genre={self.category_id}&JsHttpRequest=1-xml&p=0"
            response = self.server.session.get(initial_url, cookies=self.server.cookies, headers=self.server.headers, timeout=10)
            response.raise_for_status()
            response_json = response.json()
            if len(response_json.get("js", {})) > 0:
                total_items = response_json.get("js", {}).get("total_items", 0)
                items_per_page = len(response_json.get("js", {}).get("data", []))
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 1
                channels_data = response_json.get("js", {}).get("data", [])
                channels.extend(channels_data)

                # Fetch remaining pages in parallel
                pages_to_fetch = list(range(1, total_pages))
                if pages_to_fetch:
                    future_to_page = {}
                    for p in pages_to_fetch:
                        channels_url = f"{self.server.base_url}/portal.php?type=itv&action=get_ordered_list&genre={self.category_id}&JsHttpRequest=1-xml&p={p}"
                        logging.debug(f"Fetching page {p} URL: {channels_url}")
                        
                        response = self.server.session.get(channels_url, cookies=self.server.cookies, headers=self.server.headers, timeout=10)
                        response.raise_for_status()
                        response_json = response.json()
                        page_channels = response_json.get("js", {}).get("data", [])
                        channels.extend(page_channels)

                # Remove duplicate channels based on 'id'
                unique_channels = {}
                for ch in channels:
                    cid = ch.get('id')
                    if cid and cid not in unique_channels:
                        unique_channels[cid] = STK_Channel(self, ch.get('name'), ch.get('cmd'), ch.get('logo'))
                        if ch.get('epg'):
                            pass
                channels = list(unique_channels.values())
                channels.sort(key=lambda x: x.name)  # Sort channels by name

            else:
                # No channels found for this genre
                return STATUS.CONTENT, "No channels data found.", None
        except Exception as e:
            return STATUS.ERROR, f"An error occurred while retrieving channels: {str(e)}", None

        return STATUS.SUCCESS, "", channels

class STK_Server:

    STB_LANG = "en"
    STB_TIMEZONE = "Europe/London"


    def __init__(self, hostname, mac_address):

        self.hostname = hostname
        self.mac_address = mac_address
        self.token = None
        self.token_timestamp = None

        parsed_url = urlparse(hostname)
        if not parsed_url.scheme and not parsed_url.netloc:
            parsed_url = urlparse(f"http://{hostname}")
        elif not parsed_url.scheme:
            parsed_url = parsed_url._replace(scheme="http")

        self.base_url = urlunparse(
            (parsed_url.scheme, parsed_url.netloc, "", "", "", "")
        )

        self.session = requests.Session()
        

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                # Close the session if it exists
                self.session.close()
            except Exception as e:
                logging.debug(f"Error closing session: {e}")
            finally:
                self.session = None


    # Reintroduce get_token for non-stalker portals
    def get_token(self):
        try:
            handshake_url = f"{self.base_url}/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml"
            cookies = {
                "mac": self.mac_address,
                "stb_lang": self.STB_LANG,
                "timezone": self.STB_TIMEZONE,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
                            "AppleWebKit/533.3 (KHTML, like Gecko) "
                            "MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            }
            response = self.session.get(handshake_url, cookies=cookies, headers=headers, timeout=15)
            response.raise_for_status()
            token = response.json().get("js", {}).get("token")
            if token:
                self.token = token
                self.token_timestamp = time.time()
                return STATUS.SUCCESS, "Token retrieved"
            else:
                logging.debug("Token not found in handshake response.")
                return STATUS.LOGIN, "Token not found in handshake response."
        except Exception as e:
            return STATUS.ERROR, f"Error getting token: {e}"


    def is_token_valid(self):
        # Assuming token is valid for 10 minutes
        if self.token and (time.time() - self.token_timestamp) < 600:
            return True
        return False
    
    def validate_token(self):
        if not self.is_token_valid():
            return self.get_token()
        else:
            logging.debug("Token is still valid.")
            return STATUS.SUCCESS, "Token is valid"



    def login(self):
         # Non-stalker logic: use RequestThread
        status, message = self.get_token()
        if status != STATUS.SUCCESS:
            return status, message

        self.cookies = {
                    "mac": self.mac_address,
                    "stb_lang": self.STB_LANG,
                    "timezone": self.STB_TIMEZONE,
                    "token": self.token,
                }
        self.headers = {
                    "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
                                "AppleWebKit/533.3 (KHTML, like Gecko) "
                                "MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
                    "Authorization": f"Bearer {self.token}",
                }

        # Fetch profile and account info
        try:
            profile_url = f"{self.base_url}/portal.php?type=stb&action=get_profile&JsHttpRequest=1-xml"
            response_profile = self.session.get(profile_url, cookies=self.cookies, headers=self.headers, timeout=10)
            response_profile.raise_for_status()
            profile_data = response_profile.json()
        except Exception as e:
            return STATUS.ERROR, f"Error fetching profile: {e}"

        try:
            account_info_url = f"{self.base_url}/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
            response_account_info = self.session.get(account_info_url, cookies=self.cookies, headers=self.headers, timeout=10)
            response_account_info.raise_for_status()
            account_info_data = response_account_info.json()
        except Exception as e:
            return STATUS.ERROR, f"Error fetching account info: {e}"
        
        return STATUS.SUCCESS, "Login successful"
    

    def get_genres(self):
        # Get live genres
        genres = None
        try:
            genres_url = f"{self.base_url}/portal.php?type=itv&action=get_genres&JsHttpRequest=1-xml"
            response = self.session.get(genres_url, cookies=self.cookies, headers=self.headers, timeout=10)
            response.raise_for_status()
            genre_data = response.json().get("js", [])
            if genre_data:
                genres = []
                for i in genre_data:
                    genre = STK_Genre(
                        self,
                        name=i["title"],
                        category_type="IPTV",
                        catgeory_id=i["id"]
                    )
                    genres.append(genre)

        except Exception as e:
            return STATUS.ERROR, f"Error getting genres: {e}", None
        
        return STATUS.SUCCESS, "", genres