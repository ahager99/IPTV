import logging
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from Library import IPTV_Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAC_PATTERN = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}')
DATE_PATTERN = re.compile(
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b'
)
URL_PATTERN = re.compile(r'https?://\S+')

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%B %d, %Y").date()
    except Exception:
        return None

def extract_entries_from_divs(divs):
    results = []
    current_url = None
    last_mac = None

    for div in divs:
        for p in div.find_all('p'):
            text = p.get_text(strip=True)
            url_match = URL_PATTERN.search(text)
            mac_match = MAC_PATTERN.search(text)
            date_match = DATE_PATTERN.search(text)

            if url_match:
                if last_mac:
                    results.append({'url': current_url, 'mac': last_mac, 'expiration': None})
                    last_mac = None
                current_url = url_match.group()
                continue

            if mac_match:
                if date_match:
                    results.append({
                        'url': current_url,
                        'mac': mac_match.group(),
                        'expiration': parse_date(date_match.group())
                    })
                    last_mac = None
                else:
                    if last_mac:
                        results.append({'url': current_url, 'mac': last_mac, 'expiration': None})
                    last_mac = mac_match.group()
                continue

            if date_match and last_mac:
                results.append({
                    'url': current_url,
                    'mac': last_mac,
                    'expiration': parse_date(date_match.group())
                })
                last_mac = None

    if last_mac:
        results.append({'url': current_url, 'mac': last_mac, 'expiration': None})

    return results

def get_matching_urls(base_url):
    response = requests.get(base_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    matching = [base_url] + [link['href'] for link in links if link.get_text(strip=True).startswith("Smart STB Emu")]
    logging.info(f"Found {len(matching)} URLs matching the criteria.")
    return matching

def main():
    base_url = "https://stbstalker.alaaeldinee.com/?m=1"
    logging.info(f"Start URL: {base_url}")

    matching_urls = get_matching_urls(base_url)
    all_results = []

    for idx, url in enumerate(matching_urls, 1):
        logging.info(f"Processing [{idx}/{len(matching_urls)}]: {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.select('div.ap-connt')
        all_results.extend(extract_entries_from_divs(divs))

    logging.info(f"Extracted {len(all_results)} entries.")

    skipped_count = 0
    inserted_count = 0
    with IPTV_Database() as db:
        for counter, entry in enumerate(all_results, 1):
            if not entry['url'] or not entry['mac']:
                logging.warning(f"Skipping entry with missing URL or MAC: {entry}")
                continue
            if db.get_mac_id(entry['url'], entry['mac']):
                #logging.info(f"[{counter}/{len(all_results)}] EXISTS: {entry['url']} - {entry['mac']}")
                skipped_count += 1
                continue
            logging.info(f"[{counter}/{len(all_results)}] INSERTING: {entry['url']} - {entry['mac']} - {entry['expiration']}")
            db.insert_mac(entry['url'], entry['mac'], entry['expiration'], None, None)
            inserted_count += 1

    logging.info("------------------------------------------")
    logging.info(f"Inserted {inserted_count} new entries, skipped {skipped_count} existing entries.")

if __name__ == "__main__":
    main()