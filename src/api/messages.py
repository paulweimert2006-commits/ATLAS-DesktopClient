"""
BiPro API - Mitteilungen + Notifications

API-Client fuer System-/Admin-Mitteilungen und Notification-Polling.
"""

from typing import Optional, Dict, List
import logging

from .client import APIClient, APIError

logger = logging.getLogger(__name__)


class MessagesAPI:
    """
    API-Client fuer Mitteilungen und Notification-Polling.
    
    Verwendung:
        messages_api = MessagesAPI(client)
        messages = messages_api.get_messages()
        summary = messages_api.get_notifications_summary()
    """
    
    def __init__(self, client: APIClient):
        self.client = client
    
    # ================================================================
    # Mitteilungen (System + Admin)
    # ================================================================
    
    def get_messages(self, page: int = 1, per_page: int = 20) -> Dict:
        """
        Paginierte Mitteilungen mit Read-Status pro User abrufen.
        
        Args:
            page: Seitennummer (1-basiert)
            per_page: Eintraege pro Seite (max 100)
            
        Returns:
            Dict mit 'data' (Liste) und 'pagination'
        """
        try:
            response = self.client.get(
                '/messages',
                params={'page': page, 'per_page': per_page}
            )
            return response
        except APIError as e:
            logger.error(f"Fehler beim Laden der Mitteilungen: {e}")
            raise
    
    def mark_as_read(self, message_ids: List[int]) -> None:
        """
        Mitteilungen als gelesen markieren (Bulk INSERT IGNORE).
        
        Args:
            message_ids: Liste von Mitteilungs-IDs
        """
        if not message_ids:
            return
        try:
            self.client.put('/messages/read', json_data={'message_ids': message_ids})
        except APIError as e:
            logger.warning(f"Fehler beim Markieren als gelesen: {e}")
    
    def create_message(self, title: str, description: str = None,
                       severity: str = 'info') -> Dict:
        """
        Neue Mitteilung erstellen (nur Admin).
        sender_name wird automatisch aus JWT gesetzt.
        
        Args:
            title: Titel der Mitteilung
            description: Optionale Beschreibung
            severity: 'info', 'warning', 'error', 'critical'
            
        Returns:
            Dict mit erstellter Mitteilung
        """
        data = {
            'title': title,
            'severity': severity,
        }
        if description:
            data['description'] = description
        
        try:
            response = self.client.post('/messages', json_data=data)
            if response.get('success'):
                return response.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Erstellen der Mitteilung: {e}")
            raise
        return {}
    
    def delete_message(self, message_id: int) -> bool:
        """
        Mitteilung loeschen (nur Admin).
        
        Args:
            message_id: ID der Mitteilung
            
        Returns:
            True bei Erfolg
        """
        try:
            response = self.client.delete(f'/messages/{message_id}')
            return response.get('success', False)
        except APIError as e:
            logger.error(f"Fehler beim Loeschen der Mitteilung {message_id}: {e}")
            raise
    
    # ================================================================
    # Notification Polling (leichtgewichtig)
    # ================================================================
    
    def get_notifications_summary(self, last_message_ts: Optional[str] = None) -> Dict:
        """
        Leichtgewichtiger Polling-Endpoint fuer Unread-Counts + Toast.
        
        Args:
            last_message_ts: ISO-Timestamp der letzten bekannten Chat-Nachricht
            
        Returns:
            Dict mit unread_chats, unread_system_messages, latest_chat_message
        """
        params = {}
        if last_message_ts:
            params['last_message_ts'] = last_message_ts
        
        try:
            response = self.client.get('/notifications/summary', params=params)
            return response
        except APIError as e:
            logger.debug(f"Polling-Fehler (wird ignoriert): {e}")
            # Polling-Fehler nicht propagieren
            return {
                'unread_chats': 0,
                'unread_system_messages': 0,
                'latest_chat_message': None
            }
