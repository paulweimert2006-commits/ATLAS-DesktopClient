"""
Presenter: Klärfälle / Zuordnung.

Vermittelt zwischen ZuordnungPanel (View) und UseCases. Steuert alle asynchronen
Datenladungen & Mapping-Aktionen für das Klärfälle/Zuordnung-UI im Provisionsmanagement.

Dieser Presenter kapselt:
- Laden und Aktualisieren der offenen Provisions-Klärfälle vom Backend.
- Mapping und (Neu-)Zuordnung von Beratern zu importierten VU-Namen.
- Triggern von Auto-Matching/Match-Vorschlags-Suchen.
- Abstraktion und Statussteuerung asynchroner Worker (QThread/Worker-Objekte).
- Fehlerbehandlung via View (Toast, Fehleranzeigen).

View:     domain.provision.interfaces.IClearanceView
Repo:     infrastructure.api.provision_repository.ProvisionRepository
Workers:  infrastructure.threading.provision_workers.[...]

Siehe Coding-Standards AGENTS.md: Keine modalen Popups, Logging, UI-Texte via i18n.
"""

import logging
from typing import Optional

from domain.provision.interfaces import IClearanceView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    ClearanceLoadWorker, MappingSyncWorker, MatchSearchWorker,
)

logger = logging.getLogger(__name__)


class ClearancePresenter:
    """
    Presenter für das Zuordnung/Klärfälle-Panel.

    Verantwortlichkeiten:
        - Vermittelt zwischen View und Backend-Repository.
        - Kapselt alle asynchronen Aktionen rund um offene Provisionszuordnungen ("Klärfälle").
        - Verarbeitet Zuordnungen, Maps, (Auto-)Matches und Fehlerzustände.
        - Reagiert auf Nutzer-Eingaben aus dem Panel (z.B. Mapping anlegen).
        - Hält Status der asynchronen Worker und gibt UI-Rückmeldungen.
    """

    def __init__(self, repository: ProvisionRepository):
        """
        Initialisiert Presenter und konfiguriert Repository + Worker-Slots.

        Args:
            repository: ProvisionRepository für API/DB-Operationen.
        """
        self._repo = repository
        self._view: Optional[IClearanceView] = None
        self._load_worker: Optional[ClearanceLoadWorker] = None
        self._mapping_worker: Optional[MappingSyncWorker] = None
        self._match_worker: Optional[MatchSearchWorker] = None

    def set_view(self, view: IClearanceView) -> None:
        """
        Setzt die zu verwendende View-Implementierung (UI-Panel).

        Args:
            view: UI-Komponente, die das Interface IClearanceView implementiert.
        """
        self._view = view

    def load_clearance(self) -> None:
        """
        Löst das (asynchrone) Nachladen aller Klärfälle und bestehenden Mappings aus.
        Setzt Ladeanzeige in der View. Beendet ggf. laufenden Worker zuvor.
        """
        if self._view:
            self._view.show_loading(True)

        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.quit()
            self._load_worker.wait(2000)

        self._load_worker = ClearanceLoadWorker(self._repo)
        self._load_worker.finished.connect(self._on_clearance_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_clearance_loaded(self, commissions, mappings_data) -> None:
        """
        Callback nach erfolgreichem Abschluss des Ladeworkers.

        Args:
            commissions: Liste der offenen Klärfälle (Provisionen).
            mappings_data: Dict mit `mappings` (bekannte Zuordnungen) & `unmapped` (noch offene Namen).
        """
        if self._view:
            self._view.show_loading(False)
            self._view.show_commissions(commissions)
            mappings = mappings_data.get('mappings', [])
            unmapped = mappings_data.get('unmapped', [])
            self._view.show_mappings(mappings, unmapped)

    def _on_error(self, error: str) -> None:
        """
        Behandelt Fehler aus Workern, leitet Fehlermeldungen an die View weiter.

        Args:
            error: Fehlerbeschreibung (vom Worker geliefert)
        """
        logger.error(f"Klärfälle-Fehler: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def create_mapping_and_rematch(self, primary_name: str, berater_id: int,
                                  also_vu_name: str = None) -> None:
        """
        Legt eine neue Zuordnung (Mapping) an (VU-Name → Berater) und stößt Rematching an.

        Args:
            primary_name: Exakter VU-Name, der zugeordnet werden soll.
            berater_id:   Zielberater (Datenbank-ID).
            also_vu_name: Optional, alternativer VU-Name (falls Synonym).
        """
        if self._mapping_worker and self._mapping_worker.isRunning():
            return
        self._mapping_worker = MappingSyncWorker(
            self._repo, primary_name, berater_id, also_vu_name)
        self._mapping_worker.finished.connect(self._on_mapping_done)
        self._mapping_worker.error.connect(self._on_error)
        self._mapping_worker.start()

    def _on_mapping_done(self, stats) -> None:
        """
        Callback nach Abschluss des Mapping-Workers (neues Mapping wurde gespeichert).
        Führt automatisches Refresh durch.
        """
        self.refresh()

    def search_match_suggestions(self, commission_id: int, q: str = None) -> None:
        """
        Löst asynchron die Suche nach Zuordnungsvorschlägen für eine Commission aus.

        Args:
            commission_id: Die zuzuordnende Commission (Klärfall).
            q: Optionaler Such-String zur Einschränkung.
        """
        if self._match_worker and self._match_worker.isRunning():
            return
        self._match_worker = MatchSearchWorker(self._repo, commission_id, q)
        self._match_worker.finished.connect(self._on_suggestions)
        self._match_worker.error.connect(self._on_error)
        self._match_worker.start()

    def _on_suggestions(self, suggestions, commission) -> None:
        """
        Callback nach Abschluss des Suggestions-Searchers.
        Leitet Vorschläge zur UI weiter (falls Methode implementiert).
        """
        if self._view and hasattr(self._view, 'show_match_suggestions'):
            self._view.show_match_suggestions(suggestions, commission)

    def trigger_auto_match(self, batch_id: int = None):
        """
        Löst automatisches Matching im Backend aus (ggf. für ganze Batches).

        Args:
            batch_id: Optional, nur einen Batch auto-matchen.
        Returns:
            Ergebnis/Status vom Repository.
        """
        return self._repo.trigger_auto_match(batch_id)

    def get_commissions(self, **kwargs):
        """
        Delegiert Abruf aller Klärfall-Kommissionen an das Repository.

        Args:
            **kwargs: Filterkriterien für Abfrage.
        Returns:
            Liste/Ergebnisstruktur laut Repository.
        """
        return self._repo.get_commissions(**kwargs)

    def get_mappings(self, **kwargs):
        """
        Delegiert Abruf aller bestehenden Berater-VU-Mappings an das Repository.

        Args:
            **kwargs: Filterkriterien für Abfrage.
        Returns:
            Liste/Ergebnisstruktur laut Repository.
        """
        return self._repo.get_mappings(**kwargs)

    def get_employees(self):
        """
        Ruft Liste aller verfügbaren Mitarbeiter/Berater ab.
        """
        return self._repo.get_employees()

    def create_mapping(self, name: str, berater_id: int):
        """
        Legt neues Mapping (VU-Name <-> Berater) dauerhaft im Backend an.

        Args:
            name: VU-Name
            berater_id: ID des zuzuordnenden Beraters
        """
        return self._repo.create_mapping(name, berater_id)

    def delete_mapping(self, mapping_id: int) -> bool:
        """
        Entfernt ein Mapping (Aufhebung: VU-Name nicht länger zugeordnet).

        Args:
            mapping_id: Zu entfernende Mapping-ID
        Returns:
            True/False je nach Erfolg
        """
        return self._repo.delete_mapping(mapping_id)

    def match_commission(self, commission_id: int, contract_id: int,
                         berater_id: int = None) -> bool:
        """
        Weist eine konkrete Commission einem Vertrag/Berater zu.

        Args:
            commission_id: Die Provision/Commission
            contract_id:   Vertrags-DB-ID
            berater_id:    Berater-DB-ID (optional, falls override)
        Returns:
            True/False je nach Erfolg
        """
        return self._repo.match_commission(commission_id, contract_id, berater_id)

    def ignore_commission(self, commission_id: int) -> bool:
        """
        Markiert eine Commission explizit als ignoriert (Klärfall kann ausgeblendet werden).

        Args:
            commission_id: Die zu ignorierende Commission.
        Returns:
            True/False nach Erfolg.
        """
        return self._repo.ignore_commission(commission_id)

    def get_match_suggestions(self, commission_id: int, **kwargs):
        """
        Holt Vorschläge (list of candidate matches) für einen spezifischen Klärfall.

        Args:
            commission_id: Klärfall-ID
            **kwargs: Zusätzliche Suchparameter
        Returns:
            Liste der Match-Vorschläge (laut Repository)
        """
        return self._repo.get_match_suggestions(commission_id, **kwargs)

    def assign_contract(self, commission_id: int, contract_id: int,
                        force_override: bool = False):
        """
        Weist einer Commission direkt einen Vertrag zu, ggf. mit Überschreiben.

        Args:
            commission_id: Zu bindende Commission
            contract_id:   Vertrags-ID
            force_override: Wenn True, erzwingt Zuweisung trotz Konflikten
        """
        return self._repo.assign_contract(commission_id, contract_id, force_override)

    def refresh(self) -> None:
        """
        Löst erneutes Laden aller Klärfall- und Mappingdaten (Komplett-Refresh aus).
        """
        self.load_clearance()

    def has_running_workers(self) -> bool:
        """
        Prüft, ob derzeit noch einer der background-Worker aktiv ist (für Disable UI etc).

        Returns:
            True wenn mindestens ein Worker läuft, sonst False.
        """
        for w in (self._load_worker, self._mapping_worker, self._match_worker):
            if w and w.isRunning():
                return True
        return False
