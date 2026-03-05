"""
ACENCIA ATLAS - Modul-Admin: Zugriff-Tab

Zeigt User mit Modul-Zugriff, Rollen-Zuweisung.
"""

import logging
from typing import List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from api.client import APIClient, APIError
from api.auth import AuthAPI
from api.admin_modules import AdminModulesAPI
from i18n import de as texts
from ui.styles.tokens import (
    PRIMARY_900, PRIMARY_500, ACCENT_500,
    FONT_HEADLINE, FONT_BODY,
    FONT_SIZE_H3, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    RADIUS_MD,
)

logger = logging.getLogger(__name__)


class _LoadUsersWorker(QThread):
    finished = Signal(list)

    def __init__(self, api: AdminModulesAPI, module_key: str, parent=None):
        super().__init__(parent)
        self._api = api
        self._key = module_key

    def run(self):
        try:
            users = self._api.get_module_users(self._key)
            self.finished.emit(users)
        except Exception:
            self.finished.emit([])


class ModuleAccessPanel(QWidget):
    """Zeigt und verwaltet User-Zugriff fuer ein Modul."""

    def __init__(self, module_key: str, api_client: APIClient,
                 auth_api: AuthAPI, modules_api: AdminModulesAPI, parent=None):
        super().__init__(parent)
        self._module_key = module_key
        self._api_client = api_client
        self._auth_api = auth_api
        self._modules_api = modules_api
        self._users_data: List[Dict] = []
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        header = QHBoxLayout()
        title = QLabel(texts.MODULE_USERS_WITH_ACCESS)
        title.setStyleSheet(f"font-family: {FONT_HEADLINE}; font-size: {FONT_SIZE_H3}; font-weight: 700; color: {PRIMARY_900};")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton(texts.WF_REFRESH if hasattr(texts, 'WF_REFRESH') else "Aktualisieren")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.load_data)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Username", texts.ACCOUNT_TYPE_USER, texts.MODULE_COL_ENABLED,
            texts.USER_ACCESS_LEVEL, texts.USER_ROLES_HEADER
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        hint = QLabel(texts.MODULE_ENABLE_FIRST)
        hint.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}; color: {PRIMARY_500}; padding: 8px 0;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def load_data(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = _LoadUsersWorker(self._modules_api, self._module_key, self)
        self._worker.finished.connect(self._on_users_loaded)
        self._worker.start()

    def _on_users_loaded(self, users: List[Dict]):
        self._users_data = users
        self._table.setRowCount(len(users))
        for row, u in enumerate(users):
            self._table.setItem(row, 0, QTableWidgetItem(u.get('username', '')))

            at = u.get('account_type', 'user')
            type_labels = {'user': texts.ACCOUNT_TYPE_USER, 'admin': texts.ACCOUNT_TYPE_ADMIN, 'super_admin': texts.ACCOUNT_TYPE_SUPER_ADMIN}
            self._table.setItem(row, 1, QTableWidgetItem(type_labels.get(at, at)))

            enabled = u.get('is_enabled', False)
            self._table.setItem(row, 2, QTableWidgetItem("Ja" if enabled else "Nein"))

            al = u.get('access_level') or '-'
            level_labels = {'user': texts.ACCESS_LEVEL_USER, 'admin': texts.ACCESS_LEVEL_ADMIN}
            self._table.setItem(row, 3, QTableWidgetItem(level_labels.get(al, al)))

            roles = u.get('roles', [])
            role_names = ', '.join(r.get('name', r.get('role_key', '')) for r in roles)
            self._table.setItem(row, 4, QTableWidgetItem(role_names or '-'))
