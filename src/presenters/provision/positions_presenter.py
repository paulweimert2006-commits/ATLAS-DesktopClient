"""
Presenter: Provisionspositionen.

Vermittelt zwischen ProvisionspositionenPanel (View, IPositionsView) und den Anwendungsfällen des Backends.
Kapselt sämtliche Anzeigelogik, Formatierung und asynchronen Datenlade-/Speicher-Aktionen für Provisionspositionen.
Stellt Filterlogik, Fehlerbehandlung, UI-State-Weitergabe und Worker-Koordination zur Verfügung.

Hauptaufgaben:
- Asynchrones Laden & Anzeige von Provisionspositionen inkl. Filterung (z.B. Relevanz, Paginierung)
- Fehlerhandling und Statusweitergabe ausschließlich über View-Methoden (keine modalen Popups!)
- Lebenszyklus- und Parallelitätssteuerung der relevanten QThread-Worker (Positionen, Audit, Ignore)
- Schnittstelle zu spezifischen Backend-Operationen zur weiteren Verarbeitung (Mapping, Matching, Notizen etc.)
- Hält aktuellen Filter- und UI-State zur nahtlosen Aktualisierung der Anzeige

Siehe AGENTS.md: Dokument auf Projektregeln zu Presenter-/UI-Logik, Fehlerbehandlung, Logging & i18n.
"""

import logging
from typing import Optional, List

from domain.provision.entities import Commission, PaginationInfo
from domain.provision.interfaces import IPositionsView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    PositionsLoadWorker, AuditLoadWorker, IgnoreWorker,
)

logger = logging.getLogger(__name__)


class PositionsPresenter:
    """
    Presenter/Controller für das Provisionspositionen-Panel im MVP-Pattern.

    Vermittelt das Zusammenspiel zwischen UI-View (IPositionsView) und Daten-/Service-Layer.
    Übernimmt:
      - Lebenszyklusverwaltung und Parallelitätskontrolle aller relevanten Worker (QThread)
      - Status-, Fehler- und Ergebnisweitergabe an die View (UI-State-Handling)
      - Filterverwaltung (z.B. nur relevante Positionen)
      - Hilfsmethoden für Mapping, Matching, Notizspeicherung u.a.

    Args:
        repository (ProvisionRepository): Backend-API/DB-Repository für alle Datenoperationen
    """
    def __init__(self, repository: ProvisionRepository):
        self._repo = repository
        self._view: Optional[IPositionsView] = None    # UI-View-Referenz für State-Kommunikation
        self._load_worker: Optional[PositionsLoadWorker] = None   # Lade-Worker für Positionen
        self._audit_worker: Optional[AuditLoadWorker] = None      # Lade-Worker für Audit-Logs
        self._ignore_worker: Optional[IgnoreWorker] = None        # Worker zum Ignorieren von Positionen

        self._only_relevant: bool = True                # Flag: Filtert View standardmäßig auf relevante Positionen
        self._current_filters: dict = {}                # Aktuelle Filterparameter für die Positionsliste

    def set_view(self, view: IPositionsView) -> None:
        """
        Bindet die View (UI-Seite) für Statusrückmeldungen und Anzeige-Updates.

        Args:
            view (IPositionsView): UI-Komponente mit den darzustellenden Methoden
        """
        self._view = view

    @property
    def only_relevant(self) -> bool:
        """
        Getter: Gibt zurück, ob zurzeit nur relevante Provisionen angezeigt werden.

        Returns:
            bool: True, wenn nur relevante Positionen geladen werden.
        """
        return self._only_relevant

    @only_relevant.setter
    def only_relevant(self, value: bool) -> None:
        """
        Setter für das only_relevant-Attribut der Positionsfilter.

        Args:
            value (bool): True = Positionen werden nach Relevanz gefiltert.
        """
        self._only_relevant = value

    def load_positions(self, **filters) -> None:
        """
        Startet den asynchronen Ladeprozess aller Provisionspositionen mit gegebenen Filtern.
        Aktualisiert auch die gespeicherten Filterparameter für Refreshs.

        Args:
            **filters: Beliebige Positionsfilter (z.B. Berater, Status, Zeitraum, ...)
        """
        self._current_filters = filters
        if self._view:
            self._view.show_loading(True)  # Ladeindikator einblenden

        # Eventuelle laufende Worker vor Start beenden (keine Konkurrenz zulassen)
        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.quit()
            self._load_worker.wait(2000)

        # Starte neuen PositionsLoadWorker mit den derzeitigen Filterparametern
        self._load_worker = PositionsLoadWorker(
            self._repo,
            is_relevant=True if self._only_relevant else None,
            **filters,
        )
        self._load_worker.finished.connect(self._on_positions_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_positions_loaded(self, commissions: List[Commission],
                              pagination: Optional[PaginationInfo]) -> None:
        """
        Callback, wenn PositionsLoadWorker abgeschlossen ist.

        Args:
            commissions (List[Commission]): Geladene Provisionspositionen
            pagination (Optional[PaginationInfo]): Paginierungsdaten für UI
        """
        if self._view:
            self._view.show_loading(False)
            self._view.show_commissions(commissions, pagination)

    def _on_load_error(self, error: str) -> None:
        """
        Fehlerbehandlung bei allen Positionen-Worker-Rückgaben.
        Leitet Fehler via View weiter und loggt diese.

        Args:
            error (str): Fehlerbeschreibung
        """
        logger.error(f"Fehler beim Laden der Positionen: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def load_audit(self, commission_id: int) -> None:
        """
        Asynchrones Laden des Audit-Logs (Änderungshistorie) für eine einzelne Commission.

        Args:
            commission_id (int): ID der Commission, deren Audit geladen werden soll.
        """
        if self._audit_worker and self._audit_worker.isRunning():
            return
        self._audit_worker = AuditLoadWorker(self._repo, commission_id)
        self._audit_worker.finished.connect(self._on_audit_loaded)
        self._audit_worker.start()

    def _on_audit_loaded(self, comm_id: int, entries: list) -> None:
        """
        Callback: Liefert die Audit-Log-Einträge an die View weiter.

        Args:
            comm_id (int): Commission-ID
            entries (list): Audit-Eintragsliste
        """
        if self._view and hasattr(self._view, 'show_audit'):
            self._view.show_audit(comm_id, entries)

    def ignore_commission(self, commission_id: int) -> None:
        """
        Markiert eine Provisionsposition als ignoriert (z.B. zur Ausblendung im UI/Prozess).

        Args:
            commission_id (int): ID der zu ignorierenden Provisionsposition.
        """
        if self._ignore_worker and self._ignore_worker.isRunning():
            return
        self._ignore_worker = IgnoreWorker(self._repo, commission_id)
        self._ignore_worker.finished.connect(self._on_ignore_finished)
        self._ignore_worker.error.connect(self._on_load_error)
        self._ignore_worker.start()

    def _on_ignore_finished(self, success: bool) -> None:
        """
        Callback nach Fertigstellung des Ignorier-Workers.
        Bei Erfolg wird Ansicht neu geladen.

        Args:
            success (bool): True, wenn der Vorgang erfolgreich war.
        """
        if success:
            self.refresh()

    def get_commissions(self, **kwargs):
        """
        Synchrone Direktabfrage aller Commission-Objekte aus dem Repo (ohne UI-Status/Threading).

        Args:
            **kwargs: Filterparameter für Backendabfrage.
        Returns:
            Siehe ProvisionRepository.get_commissions
        """
        return self._repo.get_commissions(**kwargs)

    def get_employees(self):
        """
        Synchrone Abfrage aller relevanten Mitarbeiter/Mappings aus dem Backend.

        Returns:
            Siehe ProvisionRepository.get_employees
        """
        return self._repo.get_employees()

    def create_mapping(self, name: str, berater_id: int):
        """
        Erstellt neues Berater-Mapping im Backend.

        Args:
            name (str): Anzeigename des neuen Mappings
            berater_id (int): Zugehörige Berater-ID
        Returns:
            Siehe ProvisionRepository.create_mapping
        """
        return self._repo.create_mapping(name, berater_id)

    def trigger_auto_match(self, batch_id: int = None):
        """
        Löst die automatische Zuordnung ("Auto-Match") im Backend aus – optional für bestimmten Batch.

        Args:
            batch_id (int, optional): Falls angegeben, wird nur für diesen Batch gematcht.
        Returns:
            Siehe ProvisionRepository.trigger_auto_match
        """
        return self._repo.trigger_auto_match(batch_id)

    def get_audit_log(self, **kwargs):
        """
        Ruft Audit-Log-Einträge (Change-Tracking) für eine oder mehrere Positionen ab.

        Args:
            **kwargs: Filterparameter für Backendabfrage.
        Returns:
            Siehe ProvisionRepository.get_audit_log
        """
        return self._repo.get_audit_log(**kwargs)

    def get_match_suggestions(self, commission_id: int, **kwargs):
        """
        Holt Zuordnungsvorschläge für gegebenen Commission (Matching-Vorschläge aus Backend).

        Args:
            commission_id (int): ID der Position
            **kwargs: Weitere Filter/Steuerparameter
        Returns:
            Siehe ProvisionRepository.get_match_suggestions
        """
        return self._repo.get_match_suggestions(commission_id, **kwargs)

    def assign_contract(self, commission_id: int, contract_id: int,
                        force_override: bool = False):
        """
        Weist einer Commission einen Vertrag zu (Mapping/Zuordnung).

        Args:
            commission_id (int): Zu mappende Provisionsposition
            contract_id (int): Ziel-Vertrag
            force_override (bool, optional): Erzwingt Zuordnung auch bei potenziellen Konflikten.
        Returns:
            Siehe ProvisionRepository.assign_contract
        """
        return self._repo.assign_contract(commission_id, contract_id, force_override)

    def set_commission_override(self, commission_id: int, amount_settled: float,
                                reason: str = None) -> dict:
        """
        Setzt einen Override-Betrag auf einer Commission (Korrektur/Abweichung durch Admin).

        Args:
            commission_id (int): Ziel-Position
            amount_settled (float): Neuer Auszahlungsbetrag
            reason (str, optional): Begründung für den Override
        Returns:
            dict: Rückgabedaten des Repos (Status)
        """
        return self._repo.set_commission_override(commission_id, amount_settled, reason)

    def reset_commission_override(self, commission_id: int) -> dict:
        """
        Setzt etwaige Overrides auf einer Commission zurück (auf ursprünglichen Wert).

        Args:
            commission_id (int): Ziel-Position
        Returns:
            dict: Rückgabedaten des Repos (Status)
        """
        return self._repo.reset_commission_override(commission_id)

    def save_commission_note(self, commission_id: int, note: str) -> bool:
        """
        Speichert/aktualisiert einen Notiztext zu einer Commission.

        Args:
            commission_id (int): Zielposition
            note (str): Zu speichernde Anmerkung
        Returns:
            bool: True, wenn speichern erfolgreich.
        """
        return self._repo.save_commission_note(commission_id, note)

    def refresh(self) -> None:
        """
        Löst das Neuladen der aktuellen Ansicht mit zuletzt gesetzten Filterparametern aus.
        Typisch nach Statusänderung, Filterwechsel, o.ä.
        """
        self.load_positions(**self._current_filters)

    def toggle_relevance(self) -> None:
        """
        Schaltet den Relevanzfilter (nur relevante Positionen) um und aktualisiert die Ansicht.
        """
        self._only_relevant = not self._only_relevant
        self.refresh()

    def has_running_workers(self) -> bool:
        """
        Gibt an, ob aktuell einer der asynchronen Worker (PositionsLoad/Audit/Ignore) aktiv ist.

        Returns:
            bool: True, wenn mindestens 1 Worker läuft.
        """
        for w in (self._load_worker, self._audit_worker, self._ignore_worker):
            if w and w.isRunning():
                return True
        return False
