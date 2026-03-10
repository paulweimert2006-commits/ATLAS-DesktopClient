"""
Contact API Client - Kommunikation mit dem PHP-Backend.

Alle Contact-Endpoints unter /contact/* werden ueber diesen Client aufgerufen.
Folgt dem ATLAS-Pattern (wie WorkforceApiClient).
"""

import logging
from typing import Optional

from api.client import APIClient, APIError

logger = logging.getLogger(__name__)


class ContactApiClient:
    """API-Client fuer das Contact-Modul (PHP-Backend /contact/*)."""

    def __init__(self, client: APIClient):
        self.client = client

    # ── Contacts ──────────────────────────────────────────────

    def list_contacts(self, page: int = 1, per_page: int = 50,
                      tag: str = None, contact_type: str = None) -> dict:
        params = {'page': page, 'per_page': per_page}
        if tag:
            params['tag'] = tag
        if contact_type:
            params['type'] = contact_type
        try:
            resp = self.client.get('/contact/contacts', params=params)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Laden der Kontakte: {e}")
            raise
        return {'contacts': [], 'pagination': {}}

    def get_contact(self, contact_id: int) -> dict:
        try:
            resp = self.client.get(f'/contact/contacts/{contact_id}')
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Laden des Kontakts: {e}")
            raise
        return {}

    def create_contact(self, data: dict) -> dict:
        try:
            resp = self.client.post('/contact/contacts', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Erstellen des Kontakts: {e}")
            raise
        return {}

    def update_contact(self, contact_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/contacts/{contact_id}', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren des Kontakts: {e}")
            raise
        return {}

    def delete_contact(self, contact_id: int) -> dict:
        try:
            resp = self.client.delete(f'/contact/contacts/{contact_id}')
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Loeschen des Kontakts: {e}")
            raise
        return {}

    # ── Search ────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20) -> dict:
        try:
            resp = self.client.get('/contact/search', params={'q': query, 'limit': limit})
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler bei der Kontaktsuche: {e}")
            raise
        return {'contacts': [], 'companies': []}

    def find_contact_by_phone(self, phone: str) -> dict | None:
        """Exakter Lookup per E.164-Nummer (Call-Pop). Gibt Kontakt-dict oder None zurueck."""
        try:
            resp = self.client.get('/contact/by-phone', params={'phone': phone})
            if resp.get('success'):
                data = resp.get('data', {})
                if data.get('found') is False:
                    return None
                return data
        except APIError:
            return None

    # ── Phones ────────────────────────────────────────────────

    def add_phone(self, contact_id: int, data: dict) -> dict:
        try:
            resp = self.client.post(f'/contact/contacts/{contact_id}/phones', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Hinzufuegen der Nummer: {e}")
            raise
        return {}

    def update_phone(self, phone_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/phones/{phone_id}', json_data=data)
            return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren der Nummer: {e}")
            raise

    def delete_phone(self, phone_id: int) -> None:
        self.client.delete(f'/contact/phones/{phone_id}')

    # ── Emails ────────────────────────────────────────────────

    def add_email(self, contact_id: int, data: dict) -> dict:
        try:
            resp = self.client.post(f'/contact/contacts/{contact_id}/emails', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Hinzufuegen der E-Mail: {e}")
            raise
        return {}

    def update_email(self, email_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/emails/{email_id}', json_data=data)
            return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren der E-Mail: {e}")
            raise

    def delete_email(self, email_id: int) -> None:
        self.client.delete(f'/contact/emails/{email_id}')

    # ── Calls ─────────────────────────────────────────────────

    def list_calls(self, contact_id: int) -> list:
        try:
            resp = self.client.get(f'/contact/contacts/{contact_id}/calls')
            if resp.get('success'):
                return resp.get('data', {}).get('calls', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Telefonate: {e}")
            raise
        return []

    def create_call(self, contact_id: int, data: dict) -> dict:
        try:
            resp = self.client.post(f'/contact/contacts/{contact_id}/calls', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Anlegen des Telefonats: {e}")
            raise
        return {}

    def update_call(self, call_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/calls/{call_id}', json_data=data)
            return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren des Telefonats: {e}")
            raise

    def delete_call(self, call_id: int) -> None:
        self.client.delete(f'/contact/calls/{call_id}')

    # ── Notes ─────────────────────────────────────────────────

    def list_notes(self, contact_id: int) -> list:
        try:
            resp = self.client.get(f'/contact/contacts/{contact_id}/notes')
            if resp.get('success'):
                return resp.get('data', {}).get('notes', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Notizen: {e}")
            raise
        return []

    def create_note(self, contact_id: int, data: dict) -> dict:
        try:
            resp = self.client.post(f'/contact/contacts/{contact_id}/notes', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Erstellen der Notiz: {e}")
            raise
        return {}

    def update_note(self, note_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/notes/{note_id}', json_data=data)
            return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren der Notiz: {e}")
            raise

    def delete_note(self, note_id: int) -> None:
        self.client.delete(f'/contact/notes/{note_id}')

    # ── Callbacks ─────────────────────────────────────────────

    def get_callbacks(self) -> list:
        try:
            resp = self.client.get('/contact/callbacks')
            if resp.get('success'):
                return resp.get('data', {}).get('callbacks', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Wiedervorlagen: {e}")
            raise
        return []

    # ── Favorites ─────────────────────────────────────────────

    def get_favorites(self) -> list:
        try:
            resp = self.client.get('/contact/favorites')
            if resp.get('success'):
                return resp.get('data', {}).get('favorites', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Favoriten: {e}")
            raise
        return []

    def set_favorite(self, contact_id: int) -> None:
        self.client.post(f'/contact/favorites/{contact_id}', json_data={})

    def remove_favorite(self, contact_id: int) -> None:
        self.client.delete(f'/contact/favorites/{contact_id}')

    # ── Recent ────────────────────────────────────────────────

    def get_recent(self, recent_type: str = 'viewed', limit: int = 20) -> list:
        try:
            resp = self.client.get('/contact/recent', params={'type': recent_type, 'limit': limit})
            if resp.get('success'):
                return resp.get('data', {}).get('recent', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der letzten Kontakte: {e}")
            raise
        return []

    # ── Tags ──────────────────────────────────────────────────

    def get_tags(self) -> list:
        try:
            resp = self.client.get('/contact/tags')
            if resp.get('success'):
                return resp.get('data', {}).get('tags', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Tags: {e}")
            raise
        return []

    def set_tags(self, contact_id: int, tag_ids: list) -> None:
        self.client.put(f'/contact/contacts/{contact_id}/tags', json_data={'tag_ids': tag_ids})

    # ── Companies ─────────────────────────────────────────────

    def list_companies(self) -> list:
        try:
            resp = self.client.get('/contact/companies')
            if resp.get('success'):
                return resp.get('data', {}).get('companies', [])
        except APIError as e:
            logger.error(f"Fehler beim Laden der Firmen: {e}")
            raise
        return []

    def get_company(self, company_id: int) -> dict:
        try:
            resp = self.client.get(f'/contact/companies/{company_id}')
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Laden der Firma: {e}")
            raise
        return {}

    def create_company(self, data: dict) -> dict:
        try:
            resp = self.client.post('/contact/companies', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Erstellen der Firma: {e}")
            raise
        return {}

    def update_company(self, company_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/companies/{company_id}', json_data=data)
            return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren der Firma: {e}")
            raise

    def delete_company(self, company_id: int) -> None:
        self.client.delete(f'/contact/companies/{company_id}')

    def link_company(self, contact_id: int, company_id: int, role: Optional[str] = None) -> dict:
        data = {'company_id': company_id}
        if role:
            data['role'] = role
        try:
            resp = self.client.post(f'/contact/contacts/{contact_id}/company-link', json_data=data)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Verknuepfen der Firma: {e}")
            raise
        return {}

    def unlink_company(self, link_id: int) -> None:
        self.client.delete(f'/contact/company-links/{link_id}')

    # ── Custom Values ─────────────────────────────────────────

    def add_custom_value(self, contact_id: int, field_name: str, field_value: str) -> dict:
        try:
            resp = self.client.post(
                f'/contact/contacts/{contact_id}/custom-values',
                json_data={'field_name': field_name, 'field_value': field_value},
            )
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Anlegen des Felds: {e}")
            raise
        return {}

    def update_custom_value(self, cv_id: int, data: dict) -> dict:
        try:
            resp = self.client.put(f'/contact/custom-values/{cv_id}', json_data=data)
            return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Aktualisieren des Felds: {e}")
            raise

    def delete_custom_value(self, cv_id: int) -> None:
        self.client.delete(f'/contact/custom-values/{cv_id}')

    # ── Merge (Dubletten zusammenfuehren) ──────────────────────

    def merge_contacts(self, target_id: int, source_id: int,
                       field_resolutions: dict) -> dict:
        try:
            resp = self.client.post(
                f'/contact/contacts/{target_id}/merge',
                json_data={
                    'source_id': source_id,
                    'field_resolutions': field_resolutions,
                },
            )
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Zusammenfuehren: {e}")
            raise
        return {}

    # ── Duplicate Check ───────────────────────────────────────

    def check_duplicates(self, phone: str = '', email: str = '',
                         first_name: str = '', last_name: str = '') -> dict:
        params = {}
        if phone:
            params['phone'] = phone
        if email:
            params['email'] = email
        if first_name:
            params['first_name'] = first_name
        if last_name:
            params['last_name'] = last_name
        try:
            resp = self.client.get('/contact/duplicates/check', params=params)
            if resp.get('success'):
                return resp.get('data', {})
        except APIError as e:
            logger.error(f"Fehler beim Duplikat-Check: {e}")
            raise
        return {'duplicates': [], 'has_duplicates': False}
