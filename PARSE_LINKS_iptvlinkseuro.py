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


def extract_entries_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    # Get all text lines, splitting on <br>
    lines = []
    for elem in soup.stripped_strings:
        # Split on <br> and &nbsp;
        for part in re.split(r'<br\s*/?>|[\r\n]+', elem):
            part = part.replace('\xa0', ' ').replace('&nbsp;', ' ').strip()
            if part:
                lines.append(part)

    results = []
    current_url = None

    for line in lines:
        url_match = URL_PATTERN.search(line)
        mac_match = MAC_PATTERN.search(line)
        date_match = DATE_PATTERN.search(line)

        if url_match:
            current_url = url_match.group()
            continue

        if mac_match:
            mac = mac_match.group()
            # Remove 'Mac ' prefix if present
            mac = mac.replace('Mac ', '').strip()
            expiration = None
            if date_match:
                expiration = parse_date(date_match.group())
            else:
                # Try to find a date after the MAC in the same line
                date_search = DATE_PATTERN.search(line[mac_match.end():])
                if date_search:
                    expiration = parse_date(date_search.group())
            results.append({'url': current_url, 'mac': mac, 'expiration': expiration})

    return results


def extract_entries_from_divs(divs):
    results = []
    current_url = None
    last_mac = None

    for div in divs:
        for p in div.find_all('p'):
            text = p.decode_contents()
            results.extend(extract_entries_from_html(text))

    return results


def get_matching_urls(base_url):
    response = requests.get(base_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    matching = [base_url] + [link['href'] for link in links if 'stbemu-codes-stalker-portal-mac' in link['href']]
    logging.info(f"Found {len(matching)} URLs matching the criteria.")
    return matching


def main():
    base_url = "https://iptvlinkseuro.blogspot.com/"
    logging.info(f"Start URL: {base_url}")

    matching_urls = get_matching_urls(base_url)
    all_results = []

    for idx, url in enumerate(matching_urls, 1):
        logging.info(f"Processing [{idx}/{len(matching_urls)}]: {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.find_all("div", class_="entry-content")
        all_results.extend(extract_entries_from_divs(divs))

    logging.info(f"Extracted {len(all_results)} entries.")

    skipped_count = 0
    inserted_count = 0
    with IPTV_Database() as db:
        for counter, entry in enumerate(all_results, 1):
            if db.get_mac_id(entry['url'], entry['mac']):
                #logging.info(f"[{counter}/{len(all_results)}] EXISTS: {entry['url']} - {entry['mac']}")
                skipped_count += 1
                continue
            logging.info(f"[{counter}/{len(all_results)}] INSERTING: {entry['url']} - {entry['mac']} - {entry['expiration']}")
            db.insert_mac(entry['url'], entry['mac'], entry['expiration'], None, None)
            inserted_count += 1

    logging.info("------------------------------------------")
    logging.info(f"Inserted {inserted_count} new MACs, skipped {skipped_count} existing MACs.")


if __name__ == "__main__":
    main()