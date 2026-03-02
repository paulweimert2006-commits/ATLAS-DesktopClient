"""
Presenter: Import / Abrechnungsläufe (Provisionsmanagement).

Vermittler/Präsentationslogik zwischen AbrechnungslaeufPanel (View, IImportView)
und sämtlichen Import-bezogenen UseCases/Fachservice-Schichten.

Kapselt:
- Laden und Anzeige von Import-/Abrechnungsläufen (Batches)
- Excel/CSV-Dateiparsing (asynchron, mit Fortschritt)
- Start und Überwachung von Import-Vorgängen
- Statusmanagement asynchroner Worker (QThread/Worker)
- Fehlerweitergabe an das UI via View-Methoden (keine modalen Dialoge!)
- Fortschritts-/Ergebnisübermittlung an die View

Siehe AGENTS.md zum Pattern/Fehler-/Logginghandling und UI-Textregeln.
"""

import logging
from typing import Optional, List, Dict

from domain.provision.interfaces import IImportView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    VuBatchesLoadWorker, VuParseFileWorker, VuImportWorker,
)

logger = logging.getLogger(__name__)


class ImportPresenter:
    """
    Presenter für das Import/Abrechnungsläufe-Panel der Provisionsverwaltung.

    Verantwortlichkeiten:
        - Orchestriert alle Import-bezogenen UI-Operationen zwischen View und Backend-Worker/Services.
        - Kümmert sich um Lebenszyklus, Parallelitätskontrolle und Fehlerbehandlung asynchroner Worker.
        - Gibt Ladezustände, Fortschritte und Ergebnisse an die View weiter.
        - Bewahrt UI/Domain-Trennung (kein Business Code im Panel selbst).
    """

    def __init__(self, repository: ProvisionRepository):
        """
        Initialisiert den Presenter. Setzt alle Worker-Referenzen auf None.
        
        Args:
            repository: Bereitgestelltes Repository für Backend-API/DB-Zugriffe.
        """
        self._repo = repository
        self._view: Optional[IImportView] = None
        self._batches_worker: Optional[VuBatchesLoadWorker] = None
        self._parse_worker: Optional[VuParseFileWorker] = None
        self._import_worker: Optional[VuImportWorker] = None

    def set_view(self, view: IImportView) -> None:
        """
        Registriert die vom Presenter gesteuerte View.

        Args:
            view: Panel/View-Objekt, das das Interface IImportView implementiert.
        """
        self._view = view

    def load_batches(self) -> None:
        """
        Löst das (asynchrone) Laden aller vorhandenen Import-/Abrechnungsläufe aus.

        Setzt Ladeanzeige in der View. Verhindert Mehrfachaufrufe (nur 1 Worker gleichzeitig).
        Ergebnisse werden nach Abschluss über show_batches in die UI übergeben.
        """
        if self._view:
            self._view.show_loading(True)

        # Kein Doppelstart: laufenden Worker blockiert erneuten Aufruf
        if self._batches_worker and self._batches_worker.isRunning():
            return

        self._batches_worker = VuBatchesLoadWorker(self._repo)
        self._batches_worker.finished.connect(self._on_batches_loaded)
        self._batches_worker.error.connect(self._on_error)
        self._batches_worker.start()

    def _on_batches_loaded(self, batches) -> None:
        """
        Callback: Import-Läufe erfolgreich geladen.

        Args:
            batches: Geladene Importläufe/Abrechnungsläufe.
        """
        if self._view:
            self._view.show_loading(False)
            self._view.show_batches(batches)

    def _on_error(self, error: str) -> None:
        """
        Generischer Fehlerhandler für alle Worker.

        Übergibt Fehlermeldung an die View und deaktiviert ggf. Ladeanzeige.
        Loggt Fehler ins File.

        Args:
            error: Fehlerbeschreibung
        """
        logger.error(f"Import-Fehler: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def parse_file(self, filepath: str) -> None:
        """
        Startet asynchronen Worker zum Parsen einer Importdatei (Excel/CSV).

        Args:
            filepath: Pfad zur zu verarbeitenden Quelldatei.
        """
        if self._parse_worker and self._parse_worker.isRunning():
            return
        self._parse_worker = VuParseFileWorker(filepath)
        self._parse_worker.finished.connect(self._on_parse_done)
        self._parse_worker.error.connect(self._on_error)
        self._parse_worker.start()

    def _on_parse_done(self, rows, vu_name, sheet_name, log_text) -> None:
        """
        Callback: Parsing der Datei abgeschlossen.

        Args:
            rows: Geparste Datenzeilen (für Import).
            vu_name: Erkannter Versicherer (VU).
            sheet_name: Tabellenblatt-Name der Quelle (nur Excel-relevant).
            log_text: Log/Erläuterungstext für Benutzer (Fortschritt etc.).
        """
        if self._view:
            self._view.show_parse_progress(log_text)
            # Optional auf spezifischen Completion-Handler prüfen (legacy)
            if hasattr(self._view, 'on_parse_complete'):
                self._view.on_parse_complete(rows, vu_name, sheet_name)

    def start_import(self, rows: List[Dict], filename: str,
                     sheet_name: str, vu_name: str, file_hash: str,
                     raw_data_map: dict = None) -> None:
        """
        Startet den eigentlichen Datenimport (asynchron) für das Panel.

        Args:
            rows: Datenzeilen, wie vom Parser geliefert
            filename: Ursprungsdateiname
            sheet_name: Sheet-Name aus der Datei (falls relevant)
            vu_name: Versicherername (VU)
            file_hash: Dateihash (Fingerprint für Duplikatsprüfung)
            raw_data_map: Rohdaten pro Sheet (Headers + alle Zeilen)
        """
        if self._import_worker and self._import_worker.isRunning():
            return
        self._import_worker = VuImportWorker(
            self._repo, rows, filename, sheet_name, vu_name, file_hash,
            raw_data_map=raw_data_map)
        self._import_worker.progress.connect(self._on_import_progress)
        self._import_worker.finished.connect(self._on_import_done)
        self._import_worker.error.connect(self._on_error)
        self._import_worker.start()

    def _on_import_progress(self, message: str) -> None:
        """
        Callback: Importfortschritt während des Imports.

        Args:
            message: Fortschrittstext/Fortschrittsbeschreibung
        """
        if self._view:
            self._view.show_parse_progress(message)

    def _on_import_done(self, result) -> None:
        """
        Callback: Datenimport abgeschlossen.

        Args:
            result: Ergebnisobjekt/-daten des Imports
        """
        if self._view:
            self._view.show_import_result(result)

    def refresh(self) -> None:
        """
        Triggert komplettes (Re-)Laden aller Import-Läufe – Kurzform für UI-Events.
        """
        self.load_batches()

    def has_running_workers(self) -> bool:
        """
        Prüft, ob einer der Worker gerade ausgeführt wird.

        Returns:
            True, wenn mindestens ein Worker läuft; sonst False.
        """
        for w in (self._batches_worker, self._parse_worker, self._import_worker):
            if w and w.isRunning():
                return True
        return False

    def cleanup(self) -> None:
        for w in (self._import_worker, self._parse_worker, self._batches_worker):
            if w and w.isRunning():
                logger.info(f"Warte auf Worker {w.__class__.__name__}...")
                w.quit()
                w.wait(10000)
