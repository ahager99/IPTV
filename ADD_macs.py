import logging
from datetime import datetime
from Library.Sqllite import IPTV_Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_mac_entries_from_file(filepath):
    entries = []
    with open(filepath, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    for i in range(0, len(lines), 4):
        try:
            url = lines[i].split(":", 1)[1].strip()
            mac = lines[i+1].split(":", 1)[1].strip()
            exp_raw = lines[i+2].split(":", 1)[1].strip()
            # Join the first two comma-separated parts to get "Month Day, Year"
            exp_date = ", ".join(exp_raw.split(",")[:2]).strip()
            expiration = datetime.strptime(exp_date, "%B %d, %Y").date().isoformat()
            entries.append((url, mac, expiration))
        except Exception as e:
            logging.warning(f"Could not parse block starting at line {i+1}: {e}")
    return entries

def main(new_url_macs):
    mac_entries = read_mac_entries_from_file(r"D:\Tools\MacAttack_build\MacAttackOutput.txt")

    with IPTV_Database() as db:
        for url, mac, expiration in mac_entries:
            if db.get_mac_id(url, mac):
                #logging.info(f"EXISTS: {url} - {mac}")
                continue
            db.insert_mac(url, mac, expiration, None, None)
            logging.info(f"ADDED: {url} - {mac} - {expiration}")

        for entry in new_url_macs:
            url = entry["url"]
            mac = entry["mac"]
            expiration = entry["expiration"]
            if db.get_mac_id(url, mac):
                logging.info(f"EXISTS: {url} - {mac}")
                continue
            db.insert_mac(url, mac, expiration, None, None)
            logging.info(f"ADDED: {url} - {mac} - {expiration}")

if __name__ == "__main__":
    
    new_url_macs = [{"url": "http://wtc05.mi20.cc/stalker_portal/c", "mac": "00:1A:79:79:57:A1", "expiration": None},
                   {"url": "http://wyveep.com:8080/c", "mac": "00:1A:79:50:49:AA", "expiration": None},
                   {"url": "http://restream.globaltv1.net:8080/c", "mac": "00:1a:79:08:46:3b", "expiration": None},
                   {"url": "http://tr.redatvgold.com/c", "mac": "00:1A:79:76:78:8D", "expiration": None}]

    main(new_url_macs)


