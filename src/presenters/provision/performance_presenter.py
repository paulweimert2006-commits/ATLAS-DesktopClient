"""
Presenter: Erfolgsauswertung (Performance).

Vermittelt zwischen PerformancePanel (View) und dem Repository.
Steuert den asynchronen PerformanceLoadWorker und leitet
Ergebnisse / Fehler an die View weiter.
"""

import logging
from typing import Optional

from domain.provision.entities import PerformanceData
from domain.provision.interfaces import IPerformanceView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import PerformanceLoadWorker

logger = logging.getLogger(__name__)


class PerformancePresenter:
    """MVP-Presenter fuer das Erfolgsauswertung-Panel."""

    def __init__(self, repository: ProvisionRepository):
        self._repo = repository
        self._view: Optional[IPerformanceView] = None
        self._worker: Optional[PerformanceLoadWorker] = None

    def set_view(self, view: IPerformanceView) -> None:
        self._view = view

    def load_performance(self, von: str = None, bis: str = None) -> None:
        if self._view:
            self._view.show_loading(True)

        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

        self._worker = PerformanceLoadWorker(self._repo, von=von, bis=bis)
        self._worker.finished.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_loaded(self, data: Optional[PerformanceData]) -> None:
        if self._view:
            self._view.show_loading(False)
            if data:
                self._view.show_performance(data)
            else:
                self._view.show_error('')

    def _on_error(self, error: str) -> None:
        logger.error(f"Fehler beim Laden der Erfolgsauswertung: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)
