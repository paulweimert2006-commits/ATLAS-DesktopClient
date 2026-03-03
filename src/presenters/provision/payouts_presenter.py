"""
Presenter: Auszahlungen & Reports.

Vermittelt zwischen AuszahlungenPanel (View, IPayoutsView) und
Backend-Layern. Steuert alle asynchronen Lade- und Anzeigevorgänge
für Abrechnungen und Provisionspositionen von Beratern.

Kapselt:
- Laden und Anzeige von Auszahlungs-Abrechnungen nach Monat
- Abruf von Berater-spezifischen Provisionspositionen (mit Zeitraum-Filter)
- Fehlerbehandlung & Weitergabe an die View (KEINE modalen Dialoge, siehe AGENTS.md)
- Verwaltung der Lebenszyklen aller asynchronen Worker
- Trennung der UI-Logik von den Backend-Services (Repository)
"""

import calendar
import logging
from typing import List, Optional

from domain.provision.entities import BeraterAbrechnung, Commission
from domain.provision.interfaces import IPayoutsView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    AuszahlungenLoadWorker, AuszahlungenPositionenWorker,
)
from infrastructure.threading.worker_utils import detach_worker
from services.statement_export import (
    StatementData, build_statement_data, export_statement, export_batch,
    get_statement_filename, EXTENSIONS, FILE_FILTERS,
)

logger = logging.getLogger(__name__)


class PayoutsPresenter:
    """
    Presenter/Controller für das Auszahlungen-Panel (Abrechnungsausgabe & Beraterreports).
    
    Verantwortlichkeiten:
    - Vermittelt zwischen View (IPayoutsView) und Backend (Repository, Worker).
    - Kapselt alle asynchronen Lade- und Anzeigelogs für Auszahlungsdaten.
    - Kümmert sich um Fehlerweitergabe, Worker-Steuerung, UI-State-Management.
    
    Hinweise zur Verwendung:
    - Worker laufen asynchron und signalisieren über .finished/.error.
    - Parallele Aufrufe des gleichen Workertyps werden verhindert.
    - Fehler/Nachrichten werden über die View-Methoden kommuniziert.
    """

    def __init__(self, repository: ProvisionRepository):
        """
        Initialisiert Presenter & setzt unverheiratete Worker- und View-Referenzen auf None.

        Args:
            repository: ProvisionRepository für Backend-API- und Datenzugriffe.
        """
        self._repo = repository
        self._view: Optional[IPayoutsView] = None
        self._load_worker: Optional[AuszahlungenLoadWorker] = None
        self._pos_worker: Optional[AuszahlungenPositionenWorker] = None

    def set_view(self, view: IPayoutsView) -> None:
        """
        Bindet die UI-View an diesen Presenter.

        Args:
            view: View-Objekt, das das Interface IPayoutsView implementiert.
        """
        self._view = view

    def load_abrechnungen(self, monat: str) -> None:
        """
        Asynchrones Laden & Anzeigen aller Auszahlungs-Abrechnungen für einen Monat.

        Args:
            monat: Monat der Abrechnung im Format YYYY-MM.
        """
        if self._view:
            self._view.show_loading(True)

        # Aktiven Worker verhindern (kein paralleler Ladevorgang zugelassen)
        if self._load_worker and self._load_worker.isRunning():
            return

        self._load_worker = AuszahlungenLoadWorker(self._repo, monat)
        self._load_worker.finished.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_loaded(self, abrechnungen) -> None:
        """
        Callback bei erfolgreichem Abschluss des Auszahlungs-Loaders.

        Args:
            abrechnungen: Liste/Datenstruktur der geladenen Abrechnungen für die View.
        """
        if self._view:
            self._view.show_loading(False)
            self._view.show_abrechnungen(abrechnungen)

    def _on_error(self, error: str) -> None:
        """
        Fehlercallback für alle Worker. Loggt Fehler & meldet an die View.
        
        Args:
            error: Fehlerbeschreibung/Text
        """
        logger.error(f"Auszahlungen-Fehler: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def load_berater_positionen(self, berater_id: int, von: str, bis: str) -> None:
        """
        Asynchrones Nachladen aller Provisionspositionen für einen Berater
        innerhalb eines bestimmten Zeitraums.

        Args:
            berater_id:   ID des Beraters (int)
            von:          Startdatum (Format: YYYY-MM-DD)
            bis:          Enddatum  (Format: YYYY-MM-DD)
        """
        if self._pos_worker and self._pos_worker.isRunning():
            return
        self._pos_worker = AuszahlungenPositionenWorker(
            self._repo, berater_id, von, bis)
        self._pos_worker.finished.connect(self._on_positions_loaded)
        self._pos_worker.error.connect(self._on_error)
        self._pos_worker.start()

    def _on_positions_loaded(self, berater_id, commissions) -> None:
        """
        Callback nach erfolgreichem Laden der Berater-Provisionspositionen.

        Args:
            berater_id:   ID des Beraters
            commissions:  Liste der jeweiligen Provisionspositionen
        """
        if self._view and hasattr(self._view, 'show_berater_positionen'):
            self._view.show_berater_positionen(berater_id, commissions)

    def get_abrechnungen(self, monat: str):
        """
        Synchrone API: Gibt alle Abrechnungen für einen Monat direkt aus dem Repository zurück.

        Args:
            monat: Monat im Format YYYY-MM.
        Returns:
            Liste mit Abrechnungsobjekten.
        """
        return self._repo.get_abrechnungen(monat)

    def get_commissions(self, **kwargs):
        """
        Synchrone API: Gibt alle Provisionspositionen nach Filterkriterien zurück.

        Args:
            **kwargs: Filter (z.B. berater_id, datum).
        Returns:
            Liste/Datenstruktur mit Commission-Objekten.
        """
        return self._repo.get_commissions(**kwargs)

    def generate_abrechnung(self, monat: str):
        """
        Erstellt/Generiert eine neue Abrechnung für den angegebenen Monat.

        Args:
            monat: Monat im Format YYYY-MM
        Returns:
            Ergebnis der Erstellungs-API (z.B. ID, Status).
        """
        return self._repo.generate_abrechnung(monat)

    def update_abrechnung_status(self, abrechnung_id: int, status: str):
        """
        Aktualisiert den Status einer bestimmten Abrechnung.

        Args:
            abrechnung_id: Eindeutige ID der Abrechnung
            status:        Neuer Status (z.B. 'fertig', 'angelegt')
        Returns:
            Ergebnis der Update-API (meist True/False).
        """
        return self._repo.update_abrechnung_status(abrechnung_id, status)

    # ── Statement-Export ──

    def build_statement(self, berater: BeraterAbrechnung) -> Optional[StatementData]:
        monat = berater.abrechnungsmonat[:7]
        try:
            year, month = int(monat[:4]), int(monat[5:7])
            _, last_day = calendar.monthrange(year, month)
            von = f"{monat}-01"
            bis = f"{monat}-{last_day:02d}"
        except (ValueError, IndexError):
            return None

        comms, _ = self._repo.get_commissions(
            berater_id=berater.berater_id, von=von, bis=bis, limit=5000)
        return build_statement_data(berater, comms)

    def export_single_statement(self, berater: BeraterAbrechnung,
                                fmt: str, path: str) -> None:
        data = self.build_statement(berater)
        if not data:
            raise ValueError("Keine Daten verfuegbar")
        export_statement(data, fmt, path)

    def build_all_statements(self, abrechnungen: List[BeraterAbrechnung]
                             ) -> List[StatementData]:
        results = []
        for b in abrechnungen:
            data = self.build_statement(b)
            if data:
                results.append(data)
        return results

    # ── Statement-E-Mail ──

    def send_statement_email(self, berater: BeraterAbrechnung) -> dict:
        import base64
        import tempfile
        import os

        data = self.build_statement(berater)
        if not data:
            return {'success': False, 'error': 'Keine Daten verfuegbar'}

        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            from services.statement_export import generate_pdf, get_statement_filename
            generate_pdf(data, tmp_path)
            with open(tmp_path, 'rb') as f:
                pdf_bytes = f.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')
            filename = get_statement_filename(berater, 'pdf')
            return self._repo.send_statement_email(berater.id, pdf_b64, filename)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def refresh(self) -> None:
        pass

    def has_running_workers(self) -> bool:
        """
        Gibt True zurück, solange (mindestens) ein Worker noch aktiv ist.

        Returns:
            bool (True, wenn Aktivitäten laufen)
        """
        for w in (self._load_worker, self._pos_worker):
            if w and w.isRunning():
                return True
        return False

    def cleanup(self) -> None:
        for w in (self._load_worker, self._pos_worker):
            if w and w.isRunning():
                detach_worker(w)
                w.wait(3000)
