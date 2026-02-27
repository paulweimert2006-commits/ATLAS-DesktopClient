"""
Presenter: Verteilschlüssel / Rollen.

Vermittelt zwischen VerteilschlüsselPanel (View, IDistributionView) und dem Backend-Repository
(Provisionszuordnungen, Mitarbeiter, Rollenzuweisungen etc.). Steuert asynchrone Datenlade- und
Speicher-Operationen (mit QThread/Worker) und Fehlerkommunikation.

Zentrale Aufgaben:
- Orchestriert Laden/Speichern von Verteilschlüssel-Modellen und Mitarbeitern.
- Leitet asynchrone Worker und deren Status an die View weiter.
- Behandelt Fehler, lädt Refreshes und informiert die View über Statusänderungen.
- Abstrakte Vermittlung zwischen darstellender UI und Geschäftslogik.
- Keine modalen Dialoge, Fehlerkommunikation via View-Methoden / Logging.

Siehe AGENTS.md/Coding-Standards: Asynchronität, Logging, Fehlerbehandlung, UI-Texte via i18n.
"""

import logging
from typing import Optional

from domain.provision.interfaces import IDistributionView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    VerteilschluesselLoadWorker, SaveEmployeeWorker, SaveModelWorker,
)

logger = logging.getLogger(__name__)


class DistributionPresenter:
    """
    Presenter/controller für das UI-Panel "Verteilschlüssel/Rollen" im Provisionsmanagement.

    Verantwortlichkeiten:
    - Vermittelt und synchronisiert alle Daten zwischen View (IDistributionView) und Repository.
    - Kapselt und steuert asynchrone Worker zum Laden und Speichern (Modelle, Mitarbeiter).
    - Fehlerhandling & Statusupdates übergibt er an die View (ohne modale Popups!).
    
    Arbeitsweise:
    - Jede Save/Lade-Operation wird über spezialisierte Worker (QThread) durchgeführt.
    - Wiederholte Calls verhindern parallele Worker desselben Typs.
    - UI-Kommunikation läuft ausschließlich über die View und Events.
    """

    def __init__(self, repository: ProvisionRepository):
        """
        Initialisiert Presenter mit Backend-Repository und nullt Worker-Objekte.

        Args:
            repository: Provisions-Repository-Objekt für API/DB-Zugriffe.
        """
        self._repo = repository
        self._view: Optional[IDistributionView] = None
        self._load_worker: Optional[VerteilschluesselLoadWorker] = None
        self._save_emp_worker: Optional[SaveEmployeeWorker] = None
        self._save_model_worker: Optional[SaveModelWorker] = None

    def set_view(self, view: IDistributionView) -> None:
        """
        Setzt das zu steuernde View-Interface (UI-Panel).
        Muss vor Benutzeraktionen aufgerufen sein.

        Args:
            view: UI-Komponente (Panel) mit IDistributionView-Interface.
        """
        self._view = view

    def load_data(self) -> None:
        """
        Startet das asynchrone Laden von Verteilschlüssel-Modellen und Mitarbeitern.
        Setzt Ladeanzeige in der View. Beendet ggf. laufende Lade-Worker.

        Keine Parallelstarts!
        """
        if self._view:
            self._view.show_loading(True)

        if self._load_worker and self._load_worker.isRunning():
            return  # Ladevorgang läuft bereits

        self._load_worker = VerteilschluesselLoadWorker(self._repo)
        self._load_worker.finished.connect(self._on_data_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_data_loaded(self, models, employees) -> None:
        """
        Callback: Wird aufgerufen, wenn der Lade-Worker abgeschlossen ist.

        Args:
            models: Geladene Verteilschlüssel-Modelldaten
            employees: Aktuelle Mitarbeiterdaten (für Zuweisungen)
        """
        if self._view:
            self._view.show_loading(False)
            self._view.show_models(models)
            self._view.show_employees(employees)

    def _on_error(self, error: str) -> None:
        """
        Fehlerbehandlung: Reicht Meldungen an View & Logging weiter.

        Args:
            error: Fehlermeldung (meist vom Worker geliefert)
        """
        logger.error(f"Verteilschlüssel-Fehler: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def save_employee(self, emp_id: int, data: dict) -> None:
        """
        Startet asynchrones Speichern/Update eines Mitarbeiters (Rolle, Anteile, Name, ...).

        Args:
            emp_id: Datenbank-ID oder temporäre ID des Mitarbeiters
            data:   Dict mit Änderungsdaten
        """
        if self._save_emp_worker and self._save_emp_worker.isRunning():
            return
        self._save_emp_worker = SaveEmployeeWorker(self._repo, emp_id, data)
        self._save_emp_worker.finished.connect(self._on_employee_saved)
        self._save_emp_worker.error.connect(self._on_error)
        self._save_emp_worker.start()

    def _on_employee_saved(self, success, summary) -> None:
        """
        Callback nach erfolgreichem Speichern eines Mitarbeiters.
        Aktualisiert Datensicht und meldet Status via View.

        Args:
            success: Gespeichert (Bool)
            summary: Zusammenfassung/Info (oft Dict/Text)
        """
        if success:
            self.refresh()
        if self._view and hasattr(self._view, 'on_employee_saved'):
            self._view.on_employee_saved(success, summary)

    def save_model(self, model_id: int, data: dict) -> None:
        """
        Startet asynchrones Speichern/Update eines Verteilschlüssel-Modells.

        Args:
            model_id: ID des Modells
            data:    Änderungen am Modell (Dict)
        """
        if self._save_model_worker and self._save_model_worker.isRunning():
            return
        self._save_model_worker = SaveModelWorker(self._repo, model_id, data)
        self._save_model_worker.finished.connect(self._on_model_saved)
        self._save_model_worker.error.connect(self._on_error)
        self._save_model_worker.start()

    def _on_model_saved(self, success, summary) -> None:
        """
        Callback nach erfolgreichem Speichern des Modells.
        Synchronisiert UI und meldet Status via View-Event.

        Args:
            success: Erfolgreich gespeichert (Bool)
            summary: Info/Objekt über Modell/Status
        """
        if success:
            self.refresh()
        if self._view and hasattr(self._view, 'on_model_saved'):
            self._view.on_model_saved(success, summary)

    def create_model(self, data: dict):
        """
        Legt ein neues Verteilschlüssel-Modell an (synchron, direkt im Repo).

        Args:
            data:   Felder/Werte für das Modell als Dict
        Returns:
            Das erstellte Modell (dict/Object) oder Fehlerobjekt
        """
        return self._repo.create_model(data)

    def delete_model(self, model_id: int) -> bool:
        """
        Löscht ein Modell (synchron, direkt im Repo).

        Args:
            model_id: ID des zu löschenden Modells
        Returns:
            Erfolg True/False
        """
        return self._repo.delete_model(model_id)

    def create_employee(self, data: dict):
        """
        Legt einen neuen Mitarbeiter in einem Verteilschlüssel an.

        Args:
            data: Felder für den neuen Mitarbeiter (dict)
        Returns:
            Der gespeicherte Mitarbeiter (dict/Object) oder Fehler
        """
        return self._repo.create_employee(data)

    def update_employee(self, emp_id: int, data: dict):
        """
        Aktualisiert Mitarbeiterdaten (synchron).

        Args:
            emp_id: Mitarbeiter-ID
            data:   Neue Felder/Werte (dict)
        Returns:
            Aktualisiertes Mitarbeiterobjekt/dict
        """
        return self._repo.update_employee(emp_id, data)

    def delete_employee(self, emp_id: int, hard: bool = False):
        """
        Löscht (oder deaktiviert) einen Mitarbeiter in einem Modell.

        Args:
            emp_id:  ID des zu löschenden Mitarbeiters
            hard:    True = wirklich löschen, False = ggf. nur deaktivieren
        Returns:
            Erfolg True/False
        """
        return self._repo.delete_employee(emp_id, hard=hard)

    def refresh(self) -> None:
        """
        Lädt alle Daten des Panels neu (Models, Mitarbeiter).
        """
        self.load_data()

    def has_running_workers(self) -> bool:
        """
        Gibt zurück, ob aktuell mindestens ein asynchroner Worker läuft.
        Praktisch für UI-Disabling o.ä.

        Returns:
            True wenn einer der Worker aktiv ist, sonst False.
        """
        for w in (self._load_worker, self._save_emp_worker, self._save_model_worker):
            if w and w.isRunning():
                return True
        return False
