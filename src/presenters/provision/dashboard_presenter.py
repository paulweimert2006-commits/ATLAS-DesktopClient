"""
Presenter: Dashboard.

Vermittelt zwischen DashboardPanel (View) und den UseCases/Services des Provisionsmanagement-Dashboards.

Zentrale Aufgaben:
- Vermittlung zwischen View (IDashboardView) und asynchronen Backend-Operationen.
- Steuerung und Statusverwaltung asynchroner Worker (DashboardLoadWorker, BeraterDetailWorker).
- Fehlerbehandlung, Ladedialogsteuerung und Ergebnisverarbeitung.
- Trennung von Darstellungslogik (View) und Domänenlogik (Repository/Workers).

Siehe AGENTS.md/Coding-Standards: Keine modalen Popups, Logging, UI-Texte per i18n.
"""

import logging
from typing import Optional

from domain.provision.entities import DashboardSummary
from domain.provision.interfaces import IDashboardView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    DashboardLoadWorker, BeraterDetailWorker,
)
from infrastructure.threading.worker_utils import detach_worker

logger = logging.getLogger(__name__)


class DashboardPresenter:
    """
    Präsentations-Controller für das Dashboard-Panel ("Presenter" im MVP-Pattern).

    Verantwortlichkeiten:
    - Orchestriert Ladevorgänge und Detailabfragen aus dem Provisions-Dashboard.
    - Vermittelt Ergebnisse und Fehler zwischen asynchron arbeitenden Workern und View.
    - Kümmert sich um Lebenszyklus (Start/Stop) und Parallelitätskontrolle der Worker.
    """

    def __init__(self, repository: ProvisionRepository):
        """
        Initialisiert den DashboardPresenter mit einem ProvisionRepository.
        
        Args:
            repository: Bereitgestelltes Repository für API- und Datenzugriffe.
        """
        self._repo = repository
        self._view: Optional[IDashboardView] = None
        self._load_worker: Optional[DashboardLoadWorker] = None
        self._detail_worker: Optional[BeraterDetailWorker] = None

    def set_view(self, view: IDashboardView) -> None:
        """
        Registriert die View, die vom Presenter gesteuert wird.

        Args:
            view: Implementierung von IDashboardView
        """
        self._view = view

    def load_dashboard(self, von: str = None, bis: str = None) -> None:
        """
        Löst das Laden der Übersichts-/Summendaten für das Dashboard aus.

        Args:
            von: Optional, Startdatum (Filter; Format: YYYY-MM-DD)
            bis: Optional, Enddatum (Filter; Format: YYYY-MM-DD)
        """
        if self._view:
            self._view.show_loading(True)

        if self._load_worker and self._load_worker.isRunning():
            detach_worker(self._load_worker)

        self._load_worker = DashboardLoadWorker(self._repo, von=von, bis=bis)
        self._load_worker.finished.connect(self._on_dashboard_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_dashboard_loaded(self, summary, clearance) -> None:
        """
        Callback bei erfolgreichem Laden des Dashboards.

        Args:
            summary: DashboardSummary-Objekt oder Datenstruktur mit Übersichtswerten.
            clearance: Aufbereitete Klärfall-Zählwerte (z.B. offene Zuordnungen).
        """
        if self._view:
            self._view.show_loading(False)
            self._view.show_summary(summary)
            if summary:
                self._view.show_clearance_counts(clearance)

    def _on_load_error(self, error: str) -> None:
        """
        Fehler-Callback für Ladevorgänge.
        Zeigt Fehler dem Nutzer via View, loggt Fehler via logging.

        Args:
            error: Fehlernachricht (str)
        """
        logger.error(f"Dashboard-Fehler: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def load_berater_detail(self, berater_id: int, berater_name: str,
                            row_data: dict, von: str = None, bis: str = None) -> None:
        """
        Lädt und zeigt Detaildaten für einen einzelnen Berater.

        Args:
            berater_id:        Datenbank-ID des Beraters
            berater_name:      Anzeigename des Beraters
            row_data:          Grunddatenzeile, die im UI angezeigt wurde
            von / bis:         Optionales Filterdatum (Format: YYYY-MM-DD)
        """
        if self._detail_worker and self._detail_worker.isRunning():
            # Bereits laufender Detail-Worker soll parallel nicht gestartet werden.
            return
        self._detail_worker = BeraterDetailWorker(
            self._repo, berater_id, berater_name, row_data, von=von, bis=bis)
        self._detail_worker.finished.connect(self._on_berater_detail)
        self._detail_worker.error.connect(self._on_load_error)
        self._detail_worker.start()

    def _on_berater_detail(self, berater_id, berater_name, row_data, detail) -> None:
        """
        Callback bei erfolgreichem Abruf der Berater-Detaildaten.

        Args:
            berater_id:    Datenbank-ID des Beraters
            berater_name:  Name des Beraters
            row_data:      Kontextzeile aus UI
            detail:        Detailobjekt/Daten für Anzeige
        """
        if self._view and hasattr(self._view, 'show_berater_detail'):
            self._view.show_berater_detail(berater_id, berater_name, row_data, detail)

    def refresh(self) -> None:
        """
        Löst ein komplettes Neuladen des Dashboards aus.
        """
        self.load_dashboard()

    def has_running_workers(self) -> bool:
        """
        Prüft, ob aktuell ein Dashboard- oder Detail-Worker läuft.
        Kann für UI-Sperren etc. verwendet werden.

        Returns:
            True, wenn min. einer der Worker aktiv ist, sonst False.
        """
        for w in (self._load_worker, self._detail_worker):
            if w and w.isRunning():
                return True
        return False

    def cleanup(self) -> None:
        for w in (self._load_worker, self._detail_worker):
            if w and w.isRunning():
                detach_worker(w)
                w.wait(3000)
