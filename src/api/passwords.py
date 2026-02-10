"""
BiPro API - Passwort-Verwaltung

Zentrale Verwaltung bekannter Passwoerter fuer PDF- und ZIP-Entschluesselung.
Oeffentlicher Endpunkt fuer Desktop-Client + Admin-CRUD.
"""

from typing import Optional, Dict, List
import logging

from .client import APIClient, APIError

logger = logging.getLogger(__name__)


class PasswordsAPI:
    """
    API-Client fuer die Passwort-Verwaltung.
    
    Verwendung:
        passwords = PasswordsAPI(client)
        pdf_pws = passwords.get_passwords('pdf')
        zip_pws = passwords.get_passwords('zip')
    """
    
    def __init__(self, client: APIClient):
        self.client = client
    
    # ================================================================
    # Oeffentliche Endpunkte (JWT erforderlich, kein Admin)
    # ================================================================
    
    def get_passwords(self, password_type: str) -> List[str]:
        """
        Aktive Passwoerter nach Typ abrufen.
        
        Args:
            password_type: 'pdf' oder 'zip'
            
        Returns:
            Liste von Passwort-Strings
        """
        try:
            response = self.client.get(f'/passwords?type={password_type}')
            if response.get('success'):
                return response['data'].get('passwords', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der {password_type}-Passwoerter: {e}")
            raise
        return []
    
    # ================================================================
    # Admin-Endpunkte (Admin-Rechte erforderlich)
    # ================================================================
    
    def get_all_passwords(self, password_type: str = None) -> List[Dict]:
        """
        Alle Passwoerter auflisten (Admin).
        
        Args:
            password_type: Optional - 'pdf' oder 'zip' zum Filtern
            
        Returns:
            Liste von Passwort-Dicts mit id, password_type, password_value, 
            description, created_at, created_by, is_active
        """
        try:
            url = '/admin/passwords'
            if password_type:
                url += f'?type={password_type}'
            response = self.client.get(url)
            if response.get('success'):
                return response['data'].get('passwords', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Passwoerter (Admin): {e}")
            raise
        return []
    
    def create_password(self, password_type: str, password_value: str,
                        description: str = '') -> Dict:
        """
        Neues Passwort anlegen (Admin).
        
        Args:
            password_type: 'pdf' oder 'zip'
            password_value: Das Passwort
            description: Optionale Beschreibung
            
        Returns:
            Das erstellte Passwort-Dict
        """
        data = {
            'password_type': password_type,
            'password_value': password_value,
            'description': description
        }
        try:
            response = self.client.post('/admin/passwords', json_data=data)
            if response.get('success'):
                return response['data'].get('password', {})
        except APIError as e:
            logger.error(f"Fehler beim Anlegen des Passworts: {e}")
            raise
        return {}
    
    def update_password(self, password_id: int, password_value: str = None,
                        description: str = None, is_active: bool = None) -> Dict:
        """
        Passwort bearbeiten (Admin).
        
        Args:
            password_id: ID des Passworts
            password_value: Neuer Passwort-Wert (optional)
            description: Neue Beschreibung (optional)
            is_active: Aktiv-Status (optional)
            
        Returns:
            Das aktualisierte Passwort-Dict
        """
        data = {}
        if password_value is not None:
            data['password_value'] = password_value
        if description is not None:
            data['description'] = description
        if is_active is not None:
            data['is_active'] = 1 if is_active else 0
        
        try:
            response = self.client.put(f'/admin/passwords/{password_id}', json_data=data)
            if response.get('success'):
                return response['data'].get('password', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren des Passworts {password_id}: {e}")
            raise
        return {}
    
    def delete_password(self, password_id: int) -> bool:
        """
        Passwort deaktivieren / Soft-Delete (Admin).
        
        Args:
            password_id: ID des Passworts
            
        Returns:
            True bei Erfolg
        """
        try:
            response = self.client.delete(f'/admin/passwords/{password_id}')
            return response.get('success', False)
        except APIError as e:
            logger.error(f"Fehler beim Deaktivieren des Passworts {password_id}: {e}")
            raise
