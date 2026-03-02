"""
Presenter: Freie Provisionen / Sonderzahlungen.

Vermittelt zwischen FreeCommissionPanel (View, IFreeCommissionView) und dem
Backend-Repository. Steuert CRUD-Operationen und asynchrone Worker fuer
Sonderzahlungen, die nicht VU-gebunden sind.
"""

import logging
from typing import Optional

from domain.provision.interfaces import IFreeCommissionView
from infrastructure.api.provision_repository import ProvisionRepository
from infrastructure.threading.provision_workers import (
    FreeCommissionLoadWorker, FreeCommissionSaveWorker, FreeCommissionDeleteWorker,
)

logger = logging.getLogger(__name__)


class FreeCommissionPresenter:

    def __init__(self, repository: ProvisionRepository):
        self._repo = repository
        self._view: Optional[IFreeCommissionView] = None
        self._load_worker: Optional[FreeCommissionLoadWorker] = None
        self._save_worker: Optional[FreeCommissionSaveWorker] = None
        self._delete_worker: Optional[FreeCommissionDeleteWorker] = None

    def set_view(self, view: IFreeCommissionView) -> None:
        self._view = view

    def load_free_commissions(self, von: str = None, bis: str = None) -> None:
        if self._view:
            self._view.show_loading(True)
        if self._load_worker and self._load_worker.isRunning():
            return
        self._load_worker = FreeCommissionLoadWorker(self._repo, von=von, bis=bis)
        self._load_worker.finished.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_error)
        self._load_worker.start()

    def _on_loaded(self, raw_list) -> None:
        if self._view:
            self._view.show_loading(False)
            from domain.provision.entities import FreeCommission
            items = [FreeCommission.from_dict(d) for d in raw_list]
            self._view.show_free_commissions(items)

    def save_free_commission(self, data: dict, fc_id: int = None) -> None:
        if self._save_worker and self._save_worker.isRunning():
            return
        self._save_worker = FreeCommissionSaveWorker(self._repo, data, fc_id=fc_id)
        self._save_worker.finished.connect(self._on_saved)
        self._save_worker.error.connect(self._on_error)
        self._save_worker.start()

    def _on_saved(self, result: dict) -> None:
        if self._view:
            if result.get('success'):
                from i18n import de as texts
                msg = texts.PM_FREE_TOAST_UPDATED if 'id' not in result else texts.PM_FREE_TOAST_CREATED
                self._view.show_success(msg)
                self.refresh()
            else:
                self._view.show_error(result.get('message', ''))

    def delete_free_commission(self, fc_id: int) -> None:
        if self._delete_worker and self._delete_worker.isRunning():
            return
        self._delete_worker = FreeCommissionDeleteWorker(self._repo, fc_id)
        self._delete_worker.finished.connect(self._on_deleted)
        self._delete_worker.error.connect(self._on_error)
        self._delete_worker.start()

    def _on_deleted(self, result: dict) -> None:
        if self._view:
            if result.get('success'):
                from i18n import de as texts
                self._view.show_success(texts.PM_FREE_TOAST_DELETED)
                self.refresh()
            else:
                self._view.show_error(result.get('message', ''))

    def get_employees(self):
        return self._repo.get_employees()

    def _on_error(self, error: str) -> None:
        logger.error(f"FreeCommission-Fehler: {error}")
        if self._view:
            self._view.show_loading(False)
            self._view.show_error(error)

    def refresh(self) -> None:
        self.load_free_commissions()

    def has_running_workers(self) -> bool:
        for w in (self._load_worker, self._save_worker, self._delete_worker):
            if w and w.isRunning():
                return True
        return False

    def cleanup(self) -> None:
        for w in (self._load_worker, self._save_worker, self._delete_worker):
            if w and w.isRunning():
                w.quit()
                w.wait(5000)
