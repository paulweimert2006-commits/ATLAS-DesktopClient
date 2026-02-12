"""
BiPro API - Private Chat (1:1 Nachrichten)

API-Client fuer private Konversationen und Nachrichten.
"""

from typing import Optional, Dict, List
import logging

from .client import APIClient, APIError

logger = logging.getLogger(__name__)


class ChatAPI:
    """
    API-Client fuer 1:1 Chat-Nachrichten.
    
    Verwendung:
        chat_api = ChatAPI(client)
        conversations = chat_api.get_conversations()
        messages = chat_api.get_messages(conversation_id=5)
        chat_api.send_message(conversation_id=5, content="Hallo!")
    """
    
    def __init__(self, client: APIClient):
        self.client = client
    
    # ================================================================
    # Conversations
    # ================================================================
    
    def get_conversations(self) -> List[Dict]:
        """
        Eigene Chats abrufen (mit letzter Nachricht + Unread-Count).
        Sortiert nach updated_at DESC.
        
        Returns:
            Liste von Conversation-Dicts mit partner_name, last_message, unread_count
        """
        try:
            response = self.client.get('/chat/conversations')
            if response.get('success'):
                return response.get('data', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Chats: {e}")
            raise
        return []
    
    def create_conversation(self, target_user_id: int) -> Dict:
        """
        Neuen 1:1 Chat starten.
        
        Args:
            target_user_id: ID des Zielnutzers
            
        Returns:
            Dict mit id, partner_name, already_exists
        """
        try:
            response = self.client.post(
                '/chat/conversations',
                json_data={'target_user_id': target_user_id}
            )
            if response.get('success'):
                return response.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Erstellen des Chats: {e}")
            raise
        return {}
    
    # ================================================================
    # Messages
    # ================================================================
    
    def get_messages(self, conversation_id: int, page: int = 1,
                     per_page: int = 50) -> Dict:
        """
        Nachrichten eines Chats abrufen (paginiert, aelteste zuerst).
        
        Args:
            conversation_id: ID der Konversation
            page: Seitennummer
            per_page: Eintraege pro Seite
            
        Returns:
            Dict mit 'data' (Liste) und 'pagination'
        """
        try:
            response = self.client.get(
                f'/chat/conversations/{conversation_id}/messages',
                params={'page': page, 'per_page': per_page}
            )
            return response
        except APIError as e:
            logger.error(f"Fehler beim Laden der Nachrichten: {e}")
            raise
    
    def send_message(self, conversation_id: int, content: str) -> Dict:
        """
        Nachricht in einem Chat senden.
        
        Args:
            conversation_id: ID der Konversation
            content: Nachrichtentext (max 2000 Zeichen)
            
        Returns:
            Dict mit der gesendeten Nachricht
        """
        try:
            response = self.client.post(
                f'/chat/conversations/{conversation_id}/messages',
                json_data={'content': content}
            )
            if response.get('success'):
                return response.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Senden der Nachricht: {e}")
            raise
        return {}
    
    def mark_as_read(self, conversation_id: int) -> None:
        """
        Alle ungelesenen Nachrichten eines Chats als gelesen markieren.
        
        Args:
            conversation_id: ID der Konversation
        """
        try:
            self.client.put(f'/chat/conversations/{conversation_id}/read')
        except APIError as e:
            logger.warning(f"Fehler beim Markieren als gelesen: {e}")
    
    # ================================================================
    # Verfuegbare Chat-Partner
    # ================================================================
    
    def get_available_users(self) -> List[Dict]:
        """
        Nutzer auflisten, mit denen noch kein Chat besteht.
        
        Returns:
            Liste von Dicts mit id, username
        """
        try:
            response = self.client.get('/chat/users')
            if response.get('success'):
                return response.get('data', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der verfuegbaren Nutzer: {e}")
            raise
        return []
