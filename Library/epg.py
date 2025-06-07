from Library.Settings import STATUS, Settings

import logging
from io import BytesIO
import gzip

from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
from thefuzz import process



class EPG:

    def __init__(self):
        self.channels = self.__parse_urls()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


    def __parse_channels(self, xml_content):
        channels = []
        try:
            root = ET.fromstring(xml_content)
            
            for channel in root.findall('channel'):
                channel_id = channel.get('id')
                display_name = channel.findtext('display-name')
                icons = [icon.get('src') for icon in channel.findall('icon')]
                icon = icons[0] if icons else None
                url = channel.findtext('url')
                channels.append({
                    'id': channel_id,
                    'display_name': display_name,
                    'icon': icon,
                    'url': url
                })
        except Exception as e:
            pass
        return channels
    

    def __parse_urls(self):
        channels = []
        
        for url in Settings.EPG_URLS:
            logging.info(f"Processing EPG-URL: {url}")
            try:
                # Download file at the URL
                response = requests.get(url)
                # If file is archived, extract it
                if url.endswith('.gz'):
                    with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
                        content = f.read()
                else:
                    content = response.content

                channels.extend(self.__parse_channels(content))

            except requests.RequestException as e:
                logging.error(f"Error fetching EPG {url}: {e}")

        # Create a list of channels with IDs as keys
        if not channels:
            logging.error("No channels found in EPG data.")
            return None

        channel_ids = [(ch['id'], ch) for ch in channels]
        channels_dict = dict(channel_ids)
        # remove duplicates from channels_dict
        seen = set()
        for channel_id, channel in list(channels_dict.items()):
            if channel_id in seen:
                logging.warning(f"Duplicate channel ID found: {channel_id}. Removing duplicate.")
                del channels_dict[channel_id]
            else:
                seen.add(channel_id)

        return channels_dict
        



    def find_best_channel_id_match(self, name, threshold=80):
        # Returns the best match above the threshold, or None
        match, score = process.extractOne(name, self.channels.keys())
        if score >= threshold:
            logo = self.channels[match].get('icon', [None])
            display_name = self.channels[match].get('display_name', match)
            return match, display_name, logo
        return None, None, None