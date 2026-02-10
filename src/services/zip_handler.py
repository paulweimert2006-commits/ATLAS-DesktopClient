"""
ACENCIA ATLAS - ZIP Handler

Entpackt ZIP-Dateien und extrahiert deren Inhalt fuer den Upload.
Unterstuetzt passwortgeschuetzte ZIPs (Standard-PKZIP und AES-256).
Rekursive Verarbeitung: ZIPs in ZIPs, MSGs in ZIPs, PDFs in ZIPs.
Die ZIP-Datei selbst geht ins Roh-Archiv.
"""

import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Maximale Rekursionstiefe fuer verschachtelte ZIPs
MAX_RECURSION_DEPTH = 3
# SV-007 Fix: Kumulatives Groessenlimit fuer entpackte Daten (500 MB)
MAX_TOTAL_UNCOMPRESSED_SIZE = 500 * 1024 * 1024
# Maximale Groesse einer einzelnen entpackten Datei (100 MB)
MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024


@dataclass
class ZipExtractResult:
    """Ergebnis der ZIP-Extraktion."""
    zip_path: str
    extracted_paths: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_files(self) -> bool:
        return len(self.extracted_paths) > 0


def is_zip_file(file_path: str) -> bool:
    """Prueft ob eine Datei eine ZIP-Datei ist."""
    return Path(file_path).suffix.lower() == '.zip'


def extract_zip_contents(
    zip_path: str,
    temp_dir: Optional[str] = None,
    api_client=None,
    _depth: int = 0,
    _total_size: int = 0
) -> ZipExtractResult:
    """
    Entpackt eine ZIP-Datei und gibt die Pfade der extrahierten Dateien zurueck.
    
    Unterstuetzt:
    - Unverschluesselte ZIPs
    - Passwortgeschuetzte ZIPs (Passwoerter aus DB)
    - AES-256 verschluesselte ZIPs (via pyzipper)
    - Rekursive Entpackung (ZIPs in ZIPs, max. 3 Ebenen)
    
    Args:
        zip_path: Pfad zur ZIP-Datei
        temp_dir: Optionaler Ordner fuer temporaere Dateien.
                  Falls None, wird ein neuer temp-Ordner erstellt.
        api_client: Optionaler APIClient fuer dynamische Passwort-Abfrage
        _depth: Interne Rekursionstiefe (nicht manuell setzen)
    
    Returns:
        ZipExtractResult mit Pfaden zu extrahierten Dateien
    """
    result = ZipExtractResult(zip_path=zip_path)
    
    if _depth > MAX_RECURSION_DEPTH:
        result.error = f"Maximale Verschachtelungstiefe ({MAX_RECURSION_DEPTH}) erreicht"
        logger.warning(result.error)
        return result
    
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="atlas_zip_")
    
    # ZIP oeffnen (mit pyzipper fuer AES-Support, Fallback auf zipfile)
    zip_obj = None
    password_used = None
    
    try:
        zip_obj, password_used = _open_zip(zip_path, api_client)
    except Exception as e:
        result.error = str(e)
        logger.error(f"ZIP-Fehler bei {zip_path}: {e}")
        return result
    
    if zip_obj is None:
        result.error = "ZIP konnte nicht geoeffnet werden"
        return result
    
    try:
        # Dateien entpacken
        members = zip_obj.namelist()
        
        if not members:
            logger.info(f"ZIP ist leer: {Path(zip_path).name}")
            return result
        
        for member_name in members:
            # Verzeichnisse ueberspringen
            if member_name.endswith('/'):
                continue
            
            # Nur den Dateinamen (nicht den vollen Pfad in der ZIP)
            filename = Path(member_name).name
            if not filename:
                continue
            
            # Dateiname bereinigen
            filename = _sanitize_filename(filename)
            
            try:
                # Extrahieren
                target_path = _unique_path(os.path.join(temp_dir, filename))
                
                # Daten lesen und schreiben
                if password_used:
                    data = zip_obj.read(member_name, pwd=password_used.encode('utf-8'))
                else:
                    data = zip_obj.read(member_name)
                
                # SV-007 Fix: Einzeldatei-Groesse pruefen
                if len(data) > MAX_SINGLE_FILE_SIZE:
                    logger.warning(
                        f"ZIP-Eintrag '{filename}' ueberschreitet Einzeldatei-Limit "
                        f"({len(data)} > {MAX_SINGLE_FILE_SIZE} Bytes), uebersprungen"
                    )
                    continue
                
                # SV-007 Fix: Kumulatives Groessenlimit pruefen
                _total_size += len(data)
                if _total_size > MAX_TOTAL_UNCOMPRESSED_SIZE:
                    raise ValueError(
                        f"Kumulatives Groessenlimit ueberschritten "
                        f"({_total_size} > {MAX_TOTAL_UNCOMPRESSED_SIZE} Bytes). "
                        f"Moeglicherweise Zip-Bomb."
                    )
                
                with open(target_path, 'wb') as f:
                    f.write(data)
                
                logger.debug(f"ZIP-Eintrag extrahiert: {filename} ({len(data)} Bytes)")
                
                # Rekursive Verarbeitung: ZIP in ZIP
                if is_zip_file(target_path) and _depth < MAX_RECURSION_DEPTH:
                    logger.info(f"Verschachtelte ZIP gefunden: {filename}")
                    sub_dir = tempfile.mkdtemp(prefix="atlas_zip_sub_", dir=temp_dir)
                    # SV-007: Kumulatives Size-Tracking an rekursiven Aufruf weitergeben
                    sub_result = extract_zip_contents(
                        target_path, sub_dir, api_client, _depth + 1, _total_size
                    )
                    if sub_result.has_files:
                        result.extracted_paths.extend(sub_result.extracted_paths)
                    elif sub_result.error:
                        logger.warning(f"Verschachtelte ZIP-Fehler: {sub_result.error}")
                    # Verschachtelte ZIP selbst nicht als Ergebnis
                    try:
                        os.unlink(target_path)
                    except Exception:
                        pass
                    continue
                
                result.extracted_paths.append(target_path)
                
            except Exception as e:
                logger.warning(f"ZIP-Eintrag '{member_name}' konnte nicht extrahiert werden: {e}")
                continue
        
        logger.info(
            f"ZIP verarbeitet: {Path(zip_path).name} -> "
            f"{len(result.extracted_paths)} Datei(en) extrahiert"
        )
    
    finally:
        try:
            zip_obj.close()
        except Exception:
            pass
    
    return result


def _open_zip(zip_path: str, api_client=None):
    """
    Oeffnet eine ZIP-Datei, ggf. mit Passwort.
    
    Versucht:
    1. Ohne Passwort oeffnen
    2. Mit pyzipper (AES-Support) oeffnen
    3. Passwoerter aus DB durchprobieren
    
    Returns:
        Tuple (zip_object, password_used_or_None)
        
    Raises:
        ValueError: Wenn ZIP verschluesselt und kein Passwort passt
        Exception: Bei sonstigen Fehlern
    """
    # 1. Zuerst pruefen ob die Datei ueberhaupt eine gueltige ZIP ist
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"'{Path(zip_path).name}' ist keine gueltige ZIP-Datei")
    
    # 2. Versuche ohne Passwort zu oeffnen (Standard zipfile)
    try:
        zf = zipfile.ZipFile(zip_path, 'r')
        # Pruefen ob verschluesselt: Versuch eine Datei zu lesen
        members = zf.namelist()
        if members:
            # Versuche erste Nicht-Verzeichnis-Datei zu lesen
            for m in members:
                if not m.endswith('/'):
                    zf.read(m)
                    break
        return (zf, None)
    except RuntimeError as e:
        # BUG-0026 Fix: ZipFile-Handle schliessen vor Fallback
        try:
            zf.close()
        except Exception:
            pass
        # "That is a encrypted file..." -> Passwort noetig
        if 'encrypt' in str(e).lower() or 'password' in str(e).lower():
            logger.info(f"ZIP ist verschluesselt: {Path(zip_path).name}")
        else:
            raise
    except Exception:
        # BUG-0026 Fix: ZipFile-Handle schliessen vor Fallback
        try:
            zf.close()
        except Exception:
            pass
    
    # 3. Passwoerter laden
    from services.pdf_unlock import get_known_passwords
    passwords = get_known_passwords('zip', api_client)
    
    if not passwords:
        raise ValueError(
            f"ZIP '{Path(zip_path).name}' ist passwortgeschuetzt "
            f"- keine ZIP-Passwoerter konfiguriert"
        )
    
    # 4. Versuche mit pyzipper (AES-256 Support)
    try:
        import pyzipper
        has_pyzipper = True
    except ImportError:
        has_pyzipper = False
        logger.debug("pyzipper nicht installiert - nur Standard-ZIP-Verschluesselung")
    
    # 5. Passwoerter durchprobieren
    for pw in passwords:
        pw_bytes = pw.encode('utf-8')
        
        # Zuerst mit pyzipper (AES Support)
        if has_pyzipper:
            try:
                zf = pyzipper.AESZipFile(zip_path, 'r')
                members = zf.namelist()
                if members:
                    for m in members:
                        if not m.endswith('/'):
                            zf.read(m, pwd=pw_bytes)
                            break
                logger.info(f"ZIP mit Passwort entsperrt (AES): {Path(zip_path).name}")
                return (zf, pw)
            except Exception:
                try:
                    zf.close()
                except Exception:
                    pass
        
        # Standard-zipfile mit Passwort
        try:
            zf = zipfile.ZipFile(zip_path, 'r')
            members = zf.namelist()
            if members:
                for m in members:
                    if not m.endswith('/'):
                        zf.read(m, pwd=pw_bytes)
                        break
            logger.info(f"ZIP mit Passwort entsperrt: {Path(zip_path).name}")
            return (zf, pw)
        except Exception:
            try:
                zf.close()
            except Exception:
                pass
    
    # Kein Passwort hat funktioniert
    raise ValueError(
        f"ZIP '{Path(zip_path).name}' ist passwortgeschuetzt "
        f"- keines der bekannten Passwoerter passt"
    )


def _sanitize_filename(filename: str) -> str:
    """Entfernt unerlaubte Zeichen aus Dateinamen."""
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        filename = filename.replace(ch, '_')
    filename = filename.strip(' .')
    return filename or "datei"


def _unique_path(path: str) -> str:
    """Erstellt einen eindeutigen Dateipfad (haengt _2, _3, ... an bei Kollision)."""
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 2
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"
