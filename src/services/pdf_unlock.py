"""
ACENCIA ATLAS - PDF Passwortschutz-Entsperrung

Erkennt passwortgeschuetzte PDFs und entsperrt sie mit bekannten Passwoertern.
Die entsperrte PDF wird ohne Passwortschutz gespeichert, damit sie
bei der KI-Verarbeitung und beim Download korrekt gelesen werden kann.

Passwoerter werden dynamisch aus der Datenbank geladen (via API).
Fallback auf hartcodierte Liste wenn keine API verfuegbar.
"""

import logging
import os
import tempfile
import shutil
import threading
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# SV-001 Fix: Keine hardcoded Fallback-Passwoerter mehr.
# Passwoerter werden ausschliesslich ueber die API aus der DB geladen.
# Bei API-Fehler wird eine leere Liste zurueckgegeben.

# Session-Cache: Passwoerter werden einmal pro Session geladen
_password_cache: dict = {}  # {'pdf': [...], 'zip': [...]}
_cache_lock = threading.Lock()


def get_known_passwords(password_type: str, api_client=None) -> List[str]:
    """
    Laedt bekannte Passwoerter fuer einen Typ (pdf/zip).
    
    Caching: Passwoerter werden einmal geladen und dann aus dem Cache bedient.
    Bei API-Fehler wird auf die hartcodierte Fallback-Liste zurueckgegriffen.
    
    Args:
        password_type: 'pdf' oder 'zip'
        api_client: Optionaler APIClient fuer API-Zugriff
        
    Returns:
        Liste von Passwort-Strings
    """
    with _cache_lock:
        if password_type in _password_cache:
            return _password_cache[password_type]
    
    passwords = []
    
    # Versuche von API zu laden
    if api_client is not None:
        try:
            from api.passwords import PasswordsAPI
            pw_api = PasswordsAPI(api_client)
            passwords = pw_api.get_passwords(password_type)
            if passwords:
                logger.info(
                    f"{len(passwords)} {password_type}-Passwoerter von API geladen"
                )
                with _cache_lock:
                    _password_cache[password_type] = passwords
                return passwords
        except Exception as e:
            logger.warning(
                f"Konnte {password_type}-Passwoerter nicht von API laden: {e}"
            )
    
    # SV-001 Fix: Kein Fallback auf hartcodierte Passwoerter.
    # Leere Liste zurueckgeben und warnen.
    logger.warning(
        f"Keine {password_type}-Passwoerter verfuegbar "
        f"(API nicht erreichbar oder keine Passwoerter konfiguriert)"
    )
    
    with _cache_lock:
        _password_cache[password_type] = passwords
    
    return passwords


def clear_password_cache():
    """Cache leeren (z.B. nach Passwort-Aenderung im Admin)."""
    with _cache_lock:
        _password_cache.clear()
    logger.debug("Passwort-Cache geleert")


def unlock_pdf_if_needed(file_path: str, api_client=None) -> bool:
    """
    Prueft ob eine PDF passwortgeschuetzt ist und entsperrt sie ggf.

    Die Datei wird in-place ueberschrieben (ohne Passwortschutz).

    Args:
        file_path: Pfad zur PDF-Datei
        api_client: Optionaler APIClient fuer dynamische Passwort-Abfrage

    Returns:
        True wenn die PDF entsperrt wurde, False wenn kein Schutz vorhanden war.

    Raises:
        ValueError: Wenn die PDF geschuetzt ist aber keines der Passwoerter passt.
        Exception: Bei sonstigen Fehlern (keine PDF, korrupte Datei, etc.)
    """
    if not Path(file_path).suffix.lower() == '.pdf':
        return False

    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF nicht installiert - PDF-Unlock nicht verfuegbar")
        return False

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.warning(f"PDF konnte nicht geoeffnet werden: {file_path} - {e}")
        return False

    try:
        if not doc.is_encrypted:
            return False

        # Passwoerter dynamisch laden
        passwords = get_known_passwords('pdf', api_client)
        
        if not passwords:
            logger.warning("Keine PDF-Passwoerter verfuegbar")
            raise ValueError(
                f"PDF '{Path(file_path).name}' ist passwortgeschuetzt "
                f"- keine Passwoerter konfiguriert"
            )

        # Passwoerter durchprobieren
        for pw in passwords:
            if doc.authenticate(pw):
                # Entsperrt! In Temp-Datei speichern (PyMuPDF kann nicht
                # in die gleiche Datei speichern die gerade geoeffnet ist)
                # SV-024 Fix: try/finally mit garantiertem Cleanup
                temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(temp_fd)
                try:
                    doc.save(temp_path, encryption=fitz.PDF_ENCRYPT_NONE)
                    doc.close()
                    # Original ersetzen
                    shutil.move(temp_path, file_path)
                    temp_path = None  # Move erfolgreich, kein Cleanup noetig
                finally:
                    # Temp-Datei aufraeumen wenn noch vorhanden
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                logger.info(f"PDF entsperrt: {Path(file_path).name}")
                return True

        # Kein Passwort hat funktioniert
        logger.warning(
            f"PDF ist passwortgeschuetzt, keines der bekannten "
            f"Passwoerter passt: {Path(file_path).name}"
        )
        raise ValueError(
            f"PDF '{Path(file_path).name}' ist passwortgeschuetzt "
            f"- keines der bekannten Passwoerter passt"
        )

    finally:
        if not doc.is_closed:
            doc.close()
