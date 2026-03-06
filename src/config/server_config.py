"""
ATLAS Server-Konfiguration: LIVE vs. DEV LOCAL

Zum Umschalten: USE_DEV_SERVER auf True oder False setzen.
  - True  = Lokaler Entwicklungsserver (localhost:8080)
  - False = Produktionsserver (acencia.info)
"""

# ================================================================
# >>> HIER UMSCHALTEN <<<
# ================================================================
USE_DEV_SERVER: bool = True
# ================================================================


_SERVERS = {
    "live": {
        "base_url": "https://acencia.info/api",
        "verify_ssl": True,
        "label": "LIVE",
    },
    "dev": {
        "base_url": "http://localhost:8080/api",
        "verify_ssl": False,
        "label": "DEV LOCAL",
    },
}

_active = _SERVERS["dev"] if USE_DEV_SERVER else _SERVERS["live"]

API_BASE_URL: str = _active["base_url"]
API_VERIFY_SSL: bool = _active["verify_ssl"]
SERVER_LABEL: str = _active["label"]
IS_DEV: bool = USE_DEV_SERVER
