"""
System-Status API Client

Fragt den globalen ATLAS Live-Status ab (public/closed/locked).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from api.client import APIClient, APIError

logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    """Aktueller System-Status von ATLAS."""
    status: str = 'public'
    message: Optional[str] = None

    @property
    def is_public(self) -> bool:
        return self.status == 'public'

    @property
    def is_closed(self) -> bool:
        return self.status == 'closed'

    @property
    def is_locked(self) -> bool:
        return self.status == 'locked'


class SystemStatusAPI:
    """Client fuer den /system/status Endpunkt."""

    def __init__(self, client: APIClient):
        self._client = client

    def get_status(self) -> SystemStatus:
        """Aktuellen System-Status abfragen (oeffentlich, kein Auth noetig)."""
        try:
            response = self._client.get('/system/status')
            data = response.get('data', {})
            return SystemStatus(
                status=data.get('status', 'public'),
                message=data.get('message')
            )
        except APIError as e:
            logger.warning(f"System-Status Abfrage fehlgeschlagen: {e}")
            return SystemStatus(status='public')
        except Exception as e:
            logger.warning(f"System-Status Abfrage Fehler: {e}")
            return SystemStatus(status='public')


def has_access(system_status: str, is_admin: bool, dev_mode: bool) -> bool:
    """Prueft ob der Nutzer bei gegebenem Status Zugang hat.

    Args:
        system_status: 'public', 'closed' oder 'locked'
        is_admin: True wenn account_type == 'admin'
        dev_mode: True wenn App aus Python-Source laeuft (nicht als EXE)
    """
    if system_status == 'public':
        return True
    if system_status == 'closed':
        return is_admin or dev_mode
    if system_status == 'locked':
        return dev_mode
    return False
