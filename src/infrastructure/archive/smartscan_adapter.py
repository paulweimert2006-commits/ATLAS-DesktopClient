"""
Infrastructure-Adapter: SmartScan-Integration.

Wrappt die SmartScanAPI fuer das Archive-Modul.
"""

import logging
from typing import Optional, List, Dict, Tuple

from api.client import APIClient

logger = logging.getLogger(__name__)


class SmartScanAdapter:
    """Implementiert ISmartScanAdapter."""

    def __init__(self, client: APIClient):
        self._client = client

    def is_enabled(self) -> bool:
        """Prueft ob SmartScan in den Server-Einstellungen aktiviert ist."""
        try:
            from api.smartscan import SmartScanAPI
            smartscan_api = SmartScanAPI(self._client)
            settings = smartscan_api.get_settings()
            return bool(settings and int(settings.get('enabled', 0) or 0))
        except Exception as e:
            logger.warning(f"SmartScan-Status konnte nicht geladen werden: {e}")
            return False

    def send_documents(
        self, doc_ids: List[int], *,
        mode: str = 'scan',
        archive_after: bool = False,
        recolor: bool = False,
        recolor_color: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[Dict]]:
        """Sendet Dokumente an SmartScan. Gibt (job_id, result) zurueck."""
        try:
            from api.smartscan import SmartScanAPI
            smartscan_api = SmartScanAPI(self._client)
            return smartscan_api.send_documents(
                doc_ids=doc_ids,
                mode=mode,
                archive_after=archive_after,
                recolor=recolor,
                recolor_color=recolor_color,
            )
        except Exception as e:
            logger.error(f"SmartScan-Versand fehlgeschlagen: {e}")
            return None, None
