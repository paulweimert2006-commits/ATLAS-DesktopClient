"""
Zentraler Daten-Cache Service

Cached Server-Daten persistent im Speicher:
- Dokumente (nach Box)
- Box-Statistiken
- VU-Verbindungen

Features:
- Lazy Loading: Daten werden erst bei Bedarf geladen
- Persistenter Cache: Daten bleiben beim View-Wechsel erhalten
- Auto-Refresh: Alle 30 Sekunden im Hintergrund
- Manuelle Aktualisierung: Bei explizitem Refresh-Button
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any

from PySide6.QtCore import QObject, Signal, QTimer

from api.client import APIClient
from api.documents import DocumentsAPI, Document, BoxStats

logger = logging.getLogger(__name__)

# Cache-Konfiguration
DEFAULT_AUTO_REFRESH_INTERVAL = 20  # Sekunden
CACHE_TTL = 300  # 5 Minuten (als Fallback wenn Auto-Refresh nicht laeuft)


@dataclass
class CacheEntry:
    """Ein Eintrag im Cache mit Timestamp."""
    data: Any
    loaded_at: datetime = field(default_factory=datetime.now)
    
    def is_expired(self, ttl_seconds: int = CACHE_TTL) -> bool:
        """Prueft ob der Cache-Eintrag abgelaufen ist."""
        return datetime.now() - self.loaded_at > timedelta(seconds=ttl_seconds)


class DataCacheService(QObject):
    """
    Zentraler Cache fuer Server-Daten.
    
    Singleton-Pattern: Eine Instanz pro App.
    
    Signals:
        documents_updated: Dokumente wurden aktualisiert (box_type)
        stats_updated: Statistiken wurden aktualisiert
        connections_updated: VU-Verbindungen wurden aktualisiert
        refresh_started: Hintergrund-Refresh gestartet
        refresh_finished: Hintergrund-Refresh beendet
    """
    
    # Signals fuer UI-Updates
    documents_updated = Signal(str)  # box_type oder 'all'
    stats_updated = Signal()
    connections_updated = Signal()
    refresh_started = Signal()
    refresh_finished = Signal()
    
    _instance: Optional['DataCacheService'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton-Pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, api_client: APIClient = None):
        """
        Initialisiert den Cache-Service.
        
        Args:
            api_client: API-Client (nur beim ersten Aufruf noetig)
        """
        if self._initialized:
            return
            
        super().__init__()
        
        if api_client is None:
            raise ValueError("api_client muss beim ersten Aufruf gesetzt werden")
        
        self.api_client = api_client
        self.docs_api = DocumentsAPI(api_client)
        
        # Cache-Storage
        self._documents_cache: Dict[str, CacheEntry] = {}  # box_type -> CacheEntry
        self._stats_cache: Optional[CacheEntry] = None
        self._connections_cache: Optional[CacheEntry] = None
        
        # Lock fuer Thread-Safety
        self._cache_lock = threading.Lock()
        
        # Auto-Refresh Timer
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)
        self._auto_refresh_interval = DEFAULT_AUTO_REFRESH_INTERVAL
        
        # Background-Worker laeuft?
        self._refresh_in_progress = False
        
        # Pause-Zaehler fuer verschachtelte Pause-Aufrufe
        # (z.B. wenn BiPRO-Download UND Verarbeitung gleichzeitig laufen)
        self._pause_count = 0
        self._was_running_before_pause = False
        
        self._initialized = True
        logger.info("DataCacheService initialisiert")
    
    # =========================================================================
    # DOKUMENTE
    # =========================================================================
    
    def get_documents(self, box_type: str = None, force_refresh: bool = False) -> List[Document]:
        """
        Holt Dokumente aus dem Cache oder laedt sie vom Server.
        
        Strategie: Einmal ALLE Dokumente laden, dann lokal nach box_type filtern.
        Das spart ~87% der API-Calls gegenueber pro-Box-Laden.
        
        Args:
            box_type: Box-Typ oder None fuer alle
            force_refresh: True = Cache ignorieren, neu laden
            
        Returns:
            Liste von Document-Objekten
        """
        with self._cache_lock:
            # Cache vorhanden und nicht abgelaufen?
            if not force_refresh and 'all' in self._documents_cache:
                entry = self._documents_cache['all']
                if not entry.is_expired():
                    all_docs = entry.data
                    if box_type:
                        filtered = [d for d in all_docs if d.box_type == box_type]
                        logger.debug(f"Dokumente aus Cache (gefiltert): {box_type} ({len(filtered)}/{len(all_docs)} Stk)")
                        return filtered
                    logger.debug(f"Dokumente aus Cache: all ({len(all_docs)} Stk)")
                    return all_docs
        
        # Neu laden (immer alle)
        all_docs = self._load_all_documents()
        
        if box_type:
            return [d for d in all_docs if d.box_type == box_type]
        return all_docs

    def get_documents_cached_only(self, box_type: str = None) -> Optional[List[Document]]:
        """
        Holt Dokumente nur aus dem Cache (kein Server-Call).
        
        Args:
            box_type: Box-Typ oder None fuer alle
        
        Returns:
            Liste von Document-Objekten wenn Cache vorhanden und gueltig,
            sonst None.
        """
        with self._cache_lock:
            if 'all' in self._documents_cache:
                entry = self._documents_cache['all']
                if not entry.is_expired():
                    all_docs = entry.data
                    if box_type:
                        filtered = [d for d in all_docs if d.box_type == box_type]
                        logger.debug(f"Dokumente aus Cache (cache-only, gefiltert): {box_type} ({len(filtered)} Stk)")
                        return filtered
                    logger.debug(f"Dokumente aus Cache (cache-only): all ({len(all_docs)} Stk)")
                    return all_docs
        
        return None
    
    def _load_all_documents(self) -> List[Document]:
        """Laedt ALLE Dokumente vom Server und cached sie zentral.
        
        Ein einzelner API-Call statt N Calls pro Box.
        Client-seitiges Filtern erfolgt in get_documents().
        """
        try:
            logger.info("Lade alle Dokumente vom Server (1 API-Call)")
            
            documents = self.docs_api.list_documents()
            
            with self._cache_lock:
                # Nur 'all' cachen - Box-Filter erfolgt client-seitig
                self._documents_cache['all'] = CacheEntry(data=documents)
            
            logger.info(f"Dokumente geladen und gecached: {len(documents)} Stk")
            return documents
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Dokumente: {e}")
            # Bei Fehler: Alten Cache zurueckgeben falls vorhanden
            with self._cache_lock:
                if 'all' in self._documents_cache:
                    return self._documents_cache['all'].data
            return []
    
    def invalidate_documents(self, box_type: str = None):
        """
        Invalidiert den Dokumente-Cache.
        
        Da alle Dokumente zentral gecacht werden, invalidiert jeder Aufruf
        den gesamten Cache (egal ob box_type angegeben oder nicht).
        
        Args:
            box_type: Wird fuer Logging verwendet, invalidiert aber immer alles
        """
        with self._cache_lock:
            self._documents_cache.clear()
            if box_type:
                logger.debug(f"Dokumente-Cache invalidiert (Trigger: {box_type})")
            else:
                logger.debug("Dokumente-Cache komplett invalidiert")
    
    # =========================================================================
    # STATISTIKEN
    # =========================================================================
    
    def get_stats(self, force_refresh: bool = False) -> Dict[str, int]:
        """
        Holt Box-Statistiken - bevorzugt berechnet aus dem Dokumente-Cache.
        
        Strategie:
        1. Wenn Dokumente im Cache sind: Stats client-seitig berechnen (kein API-Call)
        2. Wenn nicht: Stats vom Server laden (Fallback)
        
        Args:
            force_refresh: True = Cache ignorieren, neu laden
            
        Returns:
            BoxStats-Objekt oder Dict mit Box-Typ -> Anzahl
        """
        if not force_refresh:
            with self._cache_lock:
                if self._stats_cache and not self._stats_cache.is_expired():
                    logger.debug("Statistiken aus Cache")
                    return self._stats_cache.data
        
        # Versuche Stats aus Dokumente-Cache zu berechnen (spart 1 API-Call)
        computed = self._compute_stats_from_cache()
        if computed is not None:
            return computed
        
        # Fallback: Vom Server laden
        return self._load_stats()
    
    def _compute_stats_from_cache(self) -> Optional[Any]:
        """
        Berechnet Box-Statistiken aus dem Dokumente-Cache (kein API-Call).
        
        Returns:
            BoxStats wenn Dokumente-Cache vorhanden, sonst None
        """
        with self._cache_lock:
            if 'all' not in self._documents_cache:
                return None
            entry = self._documents_cache['all']
            if entry.is_expired():
                return None
            all_docs = entry.data
        
        # Zaehler initialisieren
        box_counts = {}
        archived_counts = {}
        total = 0
        
        for doc in all_docs:
            box = doc.box_type or 'sonstige'
            total += 1
            
            if doc.is_archived:
                archived_counts[box] = archived_counts.get(box, 0) + 1
            else:
                box_counts[box] = box_counts.get(box, 0) + 1
        
        stats = BoxStats(
            eingang=box_counts.get('eingang', 0),
            verarbeitung=box_counts.get('verarbeitung', 0),
            gdv=box_counts.get('gdv', 0),
            courtage=box_counts.get('courtage', 0),
            sach=box_counts.get('sach', 0),
            leben=box_counts.get('leben', 0),
            kranken=box_counts.get('kranken', 0),
            sonstige=box_counts.get('sonstige', 0),
            roh=box_counts.get('roh', 0),
            falsch=box_counts.get('falsch', 0),
            total=total,
            gdv_archived=archived_counts.get('gdv', 0),
            courtage_archived=archived_counts.get('courtage', 0),
            sach_archived=archived_counts.get('sach', 0),
            leben_archived=archived_counts.get('leben', 0),
            kranken_archived=archived_counts.get('kranken', 0),
            sonstige_archived=archived_counts.get('sonstige', 0),
            falsch_archived=archived_counts.get('falsch', 0),
        )
        
        with self._cache_lock:
            self._stats_cache = CacheEntry(data=stats)
        
        logger.info(f"Statistiken aus Dokumente-Cache berechnet: {stats}")
        return stats
    
    def _load_stats(self) -> Dict[str, int]:
        """Laedt Statistiken vom Server und cached sie (Fallback)."""
        try:
            logger.info("Lade Statistiken vom Server")
            stats = self.docs_api.get_box_stats()
            
            with self._cache_lock:
                self._stats_cache = CacheEntry(data=stats)
            
            logger.info(f"Statistiken geladen: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Statistiken: {e}")
            with self._cache_lock:
                if self._stats_cache:
                    return self._stats_cache.data
            # BUG-0008 Fix: Leeres BoxStats-Objekt statt {} zurueckgeben
            from api.documents import BoxStats
            return BoxStats()
    
    def invalidate_stats(self):
        """Invalidiert den Statistiken-Cache."""
        with self._cache_lock:
            self._stats_cache = None
            logger.debug("Statistiken-Cache invalidiert")
    
    # =========================================================================
    # VU-VERBINDUNGEN
    # =========================================================================
    
    def get_connections(self, force_refresh: bool = False) -> List[Any]:
        """
        Holt VU-Verbindungen aus dem Cache oder laedt sie vom Server.
        
        Args:
            force_refresh: True = Cache ignorieren, neu laden
            
        Returns:
            Liste von VU-Verbindungen
        """
        with self._cache_lock:
            if not force_refresh and self._connections_cache:
                if not self._connections_cache.is_expired():
                    logger.debug("VU-Verbindungen aus Cache")
                    return self._connections_cache.data
        
        return self._load_connections()
    
    def _load_connections(self) -> List[Any]:
        """Laedt VU-Verbindungen vom Server und cached sie."""
        try:
            from api.vu_connections import VUConnectionsAPI
            
            logger.info("Lade VU-Verbindungen vom Server")
            vu_api = VUConnectionsAPI(self.api_client)
            connections = vu_api.list_connections()
            
            with self._cache_lock:
                self._connections_cache = CacheEntry(data=connections)
            
            logger.info(f"VU-Verbindungen geladen: {len(connections)} Stk")
            return connections
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der VU-Verbindungen: {e}")
            with self._cache_lock:
                if self._connections_cache:
                    return self._connections_cache.data
            return []
    
    def invalidate_connections(self):
        """Invalidiert den VU-Verbindungen-Cache."""
        with self._cache_lock:
            self._connections_cache = None
            logger.debug("VU-Verbindungen-Cache invalidiert")
    
    # =========================================================================
    # AUTO-REFRESH
    # =========================================================================
    
    def start_auto_refresh(self, interval_seconds: int = DEFAULT_AUTO_REFRESH_INTERVAL):
        """
        Startet den Auto-Refresh Timer.
        
        Args:
            interval_seconds: Intervall in Sekunden (default: 90)
        """
        self._auto_refresh_interval = interval_seconds
        self._auto_refresh_timer.start(interval_seconds * 1000)
        logger.info(f"Auto-Refresh gestartet: alle {interval_seconds} Sekunden")
    
    def stop_auto_refresh(self):
        """Stoppt den Auto-Refresh Timer."""
        self._auto_refresh_timer.stop()
        logger.info("Auto-Refresh gestoppt")
    
    def pause_auto_refresh(self):
        """
        Pausiert den Auto-Refresh temporaer.
        
        Kann mehrfach aufgerufen werden (verschachtelt).
        Erst bei gleichvielen resume_auto_refresh() Aufrufen
        wird der Refresh wieder gestartet.
        
        Nutzung:
            cache.pause_auto_refresh()
            try:
                # Lange Operation (BiPRO-Download, Verarbeitung...)
                pass
            finally:
                cache.resume_auto_refresh()
        """
        with self._cache_lock:
            self._pause_count += 1
            should_stop = (self._pause_count == 1)
            if should_stop:
                # Erster Pause-Aufruf: Timer-Zustand merken
                self._was_running_before_pause = self._auto_refresh_timer.isActive()
        # Timer-Stop ausserhalb Lock (Main-Thread QTimer Operation)
        if should_stop and self._was_running_before_pause:
            self._auto_refresh_timer.stop()
            logger.info("Auto-Refresh pausiert")
    
    def resume_auto_refresh(self):
        """
        Setzt den Auto-Refresh nach pause_auto_refresh() fort.
        
        Der Timer wird nur gestartet wenn:
        - Alle pause_auto_refresh() Aufrufe mit resume_auto_refresh() beendet wurden
        - Der Timer vor dem Pausieren aktiv war
        """
        should_resume = False
        with self._cache_lock:
            if self._pause_count > 0:
                self._pause_count -= 1
                should_resume = (self._pause_count == 0 and self._was_running_before_pause)
        # Timer-Start ausserhalb Lock (Main-Thread QTimer Operation)
        if should_resume:
            self._auto_refresh_timer.start(self._auto_refresh_interval * 1000)
            logger.info("Auto-Refresh fortgesetzt")
    
    def is_auto_refresh_paused(self) -> bool:
        """Prueft ob Auto-Refresh aktuell pausiert ist."""
        with self._cache_lock:
            return self._pause_count > 0
    
    def _on_auto_refresh(self):
        """Callback fuer Auto-Refresh Timer."""
        with self._cache_lock:
            if self._refresh_in_progress:
                logger.debug("Auto-Refresh uebersprungen (laeuft bereits)")
                return
        logger.info("Auto-Refresh gestartet")
        self.refresh_all_async()
    
    def refresh_all_async(self):
        """
        Aktualisiert alle Caches asynchron im Hintergrund.
        
        Sendet Signals wenn fertig.
        """
        with self._cache_lock:
            if self._refresh_in_progress:
                return
            self._refresh_in_progress = True
        # Signal-Emit und Thread-Start ausserhalb Lock
        self.refresh_started.emit()
        
        # In Thread ausfuehren
        thread = threading.Thread(target=self._refresh_all_background, daemon=True)
        thread.start()
    
    def _refresh_all_background(self):
        """Background-Worker fuer Refresh.
        
        Optimierung: Statt N API-Calls (einen pro gecachte Box) wird nur
        EIN Call fuer alle Dokumente gemacht. Client-seitiges Filtern
        spart ~87% der Netzwerk-Anfragen.
        
        WICHTIG: Signal-Emission direkt (nicht ueber QTimer.singleShot!).
        QTimer.singleShot funktioniert NICHT aus einem threading.Thread,
        da kein Qt-Event-Loop vorhanden ist. Direkte Emission ist sicher,
        weil alle UI-Verbindungen QueuedConnection verwenden - Qt stellt
        die Zustellung im Main-Thread automatisch sicher.
        """
        try:
            # 1. Alle Dokumente in einem API-Call laden (statt pro Box)
            self._load_all_documents()
            # 'all' Signal emittieren - UI filtert lokal
            self.documents_updated.emit('all')
            
            # 2. Statistiken aus Dokumente-Cache berechnen (kein extra API-Call)
            computed = self._compute_stats_from_cache()
            if computed is None:
                # Fallback: Vom Server laden
                self._load_stats()
            self.stats_updated.emit()
            
            # VU-Verbindungen
            if self._connections_cache:
                self._load_connections()
                self.connections_updated.emit()
            
            logger.info("Auto-Refresh abgeschlossen (1 API-Call fuer Dokumente)")
            
        except Exception as e:
            logger.error(f"Fehler beim Auto-Refresh: {e}")
        finally:
            with self._cache_lock:
                self._refresh_in_progress = False
            self.refresh_finished.emit()
    
    def refresh_all_sync(self):
        """
        Aktualisiert alle Caches synchron (blockierend).
        
        Fuer manuellen Refresh-Button.
        """
        logger.info("Manueller Refresh gestartet")
        
        # Alles invalidieren
        self.invalidate_documents()
        self.invalidate_stats()
        self.invalidate_connections()
        
        # Neu laden (wird beim naechsten Abruf gemacht)
        self._load_stats()
        self.stats_updated.emit()
    
    # =========================================================================
    # HILFSMETHODEN
    # =========================================================================
    
    def get_documents_cache_time(self) -> Optional[datetime]:
        """
        Gibt den Zeitpunkt zurueck, an dem der Dokumente-Cache zuletzt geladen wurde.
        
        Returns:
            datetime wenn Cache vorhanden und gueltig, sonst None
        """
        with self._cache_lock:
            if 'all' in self._documents_cache:
                entry = self._documents_cache['all']
                if not entry.is_expired():
                    return entry.loaded_at
        return None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Gibt Cache-Status-Informationen zurueck (fuer Debug)."""
        with self._cache_lock:
            return {
                'documents_cached': list(self._documents_cache.keys()),
                'stats_cached': self._stats_cache is not None,
                'connections_cached': self._connections_cache is not None,
                'auto_refresh_active': self._auto_refresh_timer.isActive(),
                'auto_refresh_interval': self._auto_refresh_interval,
            }
    
    @classmethod
    def reset_instance(cls):
        """Setzt die Singleton-Instanz zurueck (fuer Tests)."""
        with cls._lock:
            if cls._instance:
                cls._instance.stop_auto_refresh()
            cls._instance = None


def get_cache_service(api_client: APIClient = None) -> DataCacheService:
    """
    Factory-Funktion fuer den Cache-Service.
    
    Args:
        api_client: API-Client (nur beim ersten Aufruf noetig)
        
    Returns:
        DataCacheService Singleton-Instanz
    """
    return DataCacheService(api_client)
