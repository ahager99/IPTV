import logging
from datetime import datetime
from Library.Sqllite import IPTVDatabase

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

    with IPTVDatabase() as db:
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
                #logging.info(f"EXISTS: {url} - {mac}")
                continue
            db.insert_mac(url, mac, expiration, None, None)
            logging.info(f"ADDED: {url} - {mac} - {expiration}")

if __name__ == "__main__":
    
    new_url_macs = [{"url": "http://violetta.cfd:8080/c", "mac": "00:1A:79:41:E5:C7", "expiration": None},
                   {"url": "http://m.devtv.biz/c/", "mac": "00:1A:79:59:7B:28", "expiration": None},
                   {"url": "http://mutant.arrox.top/c", "mac": "00:1A:79:F5:73:0F", "expiration": None},
                   {"url": "http://slayerteam.in.rs:80/c/", "mac": "00:1A:79:e7:4b:71", "expiration": None}]

    main(new_url_macs)


