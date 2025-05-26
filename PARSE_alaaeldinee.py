import logging
import requests
import re
from datetime import datetime 
from bs4 import BeautifulSoup
from Library import IPTVDatabase


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Function to safely parse date
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%B %d, %Y").date()
    except:
        return None




# URL of the target webpage
url = "https://stbstalker.alaaeldinee.com/?m=1"
logging.info(f"Start URL: {url}")

# Send a GET request to the URL
response = requests.get(url)
response.raise_for_status()  # Raise an error for bad status codes

# Parse the HTML content
soup = BeautifulSoup(response.text, 'html.parser')

# Find all anchor tags
links = soup.find_all('a', href=True)

# Filter and collect links where the text starts with "Smart STB Emu"
matching_urls = [url]
for link in links:
    link_text = link.get_text(strip=True)
    if link_text.startswith("Smart STB Emu"):
        matching_urls.append(link['href'])
        logging.debug(f"Found matching URL: {link['href']} with text: {link_text}")


results = []

# Print the results
logging.info(f"Found {len(matching_urls)} URLs matching the criteria.")
counter = 0
for url in matching_urls:
    counter += 1
    logging.info(f"Processing [{counter}/{len(matching_urls)}]: {url}")

    # Fetch page content
    response = requests.get(url)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <div> elements with class containing 'app-connt'
    divs = soup.select('div.ap-connt')

    # Regex patterns
    mac_pattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}')
    date_pattern = re.compile(
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b'
    )
    url_pattern = re.compile(r'https?://\S+')


    # Tracking state
    current_url = None
    last_mac = None  # holds MAC waiting for date

    for div in divs:
        paragraphs = div.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)

            # Check if it's a URL line
            if url_match := url_pattern.search(text):
                # Flush any unmatched MAC from previous block
                if last_mac:
                    results.append({
                        'url': current_url,
                        'mac': last_mac,
                        'expiration': None
                    })
                    last_mac = None

                current_url = url_match.group()
                continue

            # Check if it contains a MAC
            mac_match = mac_pattern.search(text)
            date_match = date_pattern.search(text)

            if mac_match:
                # If it also has a date on the same line
                if date_match:
                    results.append({
                        'url': current_url,
                        'mac': mac_match.group(),
                        'expiration': parse_date(date_match.group())
                    })
                    last_mac = None
                else:
                    # Save this MAC in case a date comes next
                    # But first flush the previous MAC (no date came for it)
                    if last_mac:
                        results.append({
                            'url': current_url,
                            'mac': last_mac,
                            'expiration': None
                        })
                    last_mac = mac_match.group()
                continue

            # If there's a date only (no MAC), assume it belongs to the last MAC
            if date_match and last_mac:
                results.append({
                    'url': current_url,
                    'mac': last_mac,
                    'expiration': parse_date(date_match.group())
                })
                last_mac = None

    # Flush any final MAC with no date
    if last_mac:
        results.append({
            'url': current_url,
            'mac': last_mac,
            'expiration': None
        })


# open database connection
db = IPTVDatabase()

# Output the extracted information
logging.info(f"Extracted {len(results)} entries.")
last_url = ""
success = False
counter = 0
for entry in results:
    counter += 1
    mac = db.get_mac_id(entry['url'], entry['mac'])
    if mac:
        logging.info(f"[{counter}/{len(results)}] EXISTS: {entry['url']} - {entry['mac']}")
        continue

    logging.info(f"[{counter}/{len(results)}] INSERTING: {entry['url']} - {entry['mac']} - {entry['expiration']}")
    db.insert_mac(
        entry['url'],
        entry['mac'],
        entry['expiration'],
        None,
        None
    )


db.close()