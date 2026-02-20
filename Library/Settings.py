import os

from enum import Enum, auto

class STATUS(Enum):
    SUCCESS = "SUCCESS"
    LOGIN = "LOGIN"
    ERROR = "ERROR"
    CONTENT = "CONTENT"
    SKIPPED = "SKIPPED"

class Settings:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = "C:\\Users\\ahage\\OneDrive\\Sicherung\\IPTV.db"
    MAX_FAILED_STATUS_ATTEMPTS = 3
    VLC_MAX_PARALLEL = 1
    VLC_SEMAPHORE_TIMEOUT_SECONDS = 60
    VLC_PLAYBACK_CHECK_ATTEMPTS = 8
    VLC_PLAYBACK_CHECK_INTERVAL_SECONDS = 1


    EPG_URLS = [
    "https://www.open-epg.com/files/germany3.xml",
    "https://www.open-epg.com/files/germany1.xml",
    "https://www.open-epg.com/files/germany2.xml",
    "https://www.open-epg.com/files/germany4.xml",
    "https://www.open-epg.com/files/germany5.xml",
    "https://www.open-epg.com/files/austria1.xml",
    "https://www.open-epg.com/files/austria2.xml",
    "https://www.open-epg.com/files/austria3.xml",
    "https://www.open-epg.com/files/austria4.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    "https://www.open-epg.com/generate/Cgj6bBeeHA.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz",
    # Füge hier weitere URLs hinzu
]

