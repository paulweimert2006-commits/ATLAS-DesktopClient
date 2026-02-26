"""
UseCase: SmartScan-Versand.
"""

from typing import List, Optional

from domain.archive.entities import Document


class SmartScanSend:
    """Sendet Dokumente an den SmartScan-Service."""

    def __init__(self, api_client):
        self._api_client = api_client

    def execute(
        self, document_ids: List[int], *,
        mode: str = 'scan',
        box_type: Optional[str] = None,
        archive_after: bool = False,
        recolor_after: bool = False,
        recolor_color: Optional[str] = None,
    ) -> dict:
        """Startet einen SmartScan-Job. Gibt das initiale Ergebnis zurueck."""
        from api.smartscan import SmartScanAPI
        api = SmartScanAPI(self._api_client)
        result = api.send(
            mode=mode,
            document_ids=document_ids,
            box_type=box_type,
        )
        return result or {}
