"""
ACENCIA ATLAS - Modul-Admin: Zugriff-Tab

Zeigt User mit Modul-Zugriff, Rollen-Zuweisung pro User.
"""

import logging
from typing import List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QComboBox,
    QMessageBox, QDialog, QListWidget, QListWidgetItem, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from api.client import APIClient, APIError
from api.auth import AuthAPI
from api.admin_modules import AdminModulesAPI
from i18n import de as texts
from ui.styles.tokens import (
    PRIMARY_900, PRIMARY_500, ACCENT_500, SUCCESS, ERROR,
    FONT_HEADLINE, FONT_BODY,
    FONT_SIZE_H3, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    RADIUS_MD,
)

logger = logging.getLogger(__name__)


class _LoadDataWorker(QThread):
    finished = Signal(list, list)

    def __init__(self, api: AdminModulesAPI, module_key: str, parent=None):
        super().__init__(parent)
        self._api = api
        self._key = module_key

    def run(self):
        try:
            users = self._api.get_module_users(self._key)
            roles = self._api.get_module_roles(self._key)
            self.finished.emit(users, roles)
        except Exception:
            self.finished.emit([], [])


class _AssignRolesDialog(QDialog):
    """Dialog zum Zuweisen von Rollen an einen User fuer dieses Modul."""

    def __init__(self, username: str, available_roles: List[Dict],
                 current_role_ids: List[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{texts.USER_ROLES_HEADER}: {username}")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        info = QLabel(f"{texts.USER_ROLES_HEADER} fuer <b>{username}</b>:")
        layout.addWidget(info)

        self._role_list = QListWidget()
        for role in available_roles:
            item = QListWidgetItem(f"{role.get('name', '')} ({role.get('role_key', '')})")
            item.setData(Qt.UserRole, role['id'])
            item.setCheckState(Qt.Checked if role['id'] in current_role_ids else Qt.Unchecked)
            self._role_list.addItem(item)
        layout.addWidget(self._role_list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_role_ids(self) -> List[int]:
        result = []
        for i in range(self._role_list.count()):
            item = self._role_list.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.data(Qt.UserRole))
        return result


class ModuleAccessPanel(QWidget):
    """Zeigt und verwaltet User-Zugriff + Rollen-Zuweisung fuer ein Modul."""

    def __init__(self, module_key: str, api_client: APIClient,
                 auth_api: AuthAPI, modules_api: AdminModulesAPI, parent=None):
        super().__init__(parent)
        self._module_key = module_key
        self._api_client = api_client
        self._auth_api = auth_api
        self._modules_api = modules_api
        self._users_data: List[Dict] = []
        self._roles_data: List[Dict] = []
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

        refresh_btn = QPushButton(texts.SRVMGMT_REFRESH)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.load_data)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Username", texts.ADMIN_COL_TYPE if hasattr(texts, 'ADMIN_COL_TYPE') else "Typ",
            texts.MODULE_COL_ENABLED, texts.USER_ACCESS_LEVEL,
            texts.USER_ROLES_HEADER, ""
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 180)
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
        self._worker = _LoadDataWorker(self._modules_api, self._module_key, self)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.start()

    def _on_data_loaded(self, users: List[Dict], roles: List[Dict]):
        self._users_data = users
        self._roles_data = roles
        self._table.setRowCount(len(users))

        for row, u in enumerate(users):
            self._table.setItem(row, 0, QTableWidgetItem(u.get('username', '')))

            at = u.get('account_type', 'user')
            type_labels = {
                'super_admin': texts.ACCOUNT_TYPE_SUPER_ADMIN,
                'admin': texts.ACCOUNT_TYPE_ADMIN,
                'user': texts.ACCOUNT_TYPE_USER,
            }
            type_item = QTableWidgetItem(type_labels.get(at, at))
            if at == 'super_admin':
                type_item.setForeground(QColor('#e74c3c'))
            elif at == 'admin':
                type_item.setForeground(QColor(ACCENT_500))
            self._table.setItem(row, 1, type_item)

            enabled = u.get('is_enabled', False)
            en_item = QTableWidgetItem("Ja" if enabled else "Nein")
            en_item.setForeground(QColor(SUCCESS) if enabled else QColor(ERROR))
            self._table.setItem(row, 2, en_item)

            al = u.get('access_level') or '-'
            level_labels = {'user': texts.ACCESS_LEVEL_USER, 'admin': texts.ACCESS_LEVEL_ADMIN}
            self._table.setItem(row, 3, QTableWidgetItem(level_labels.get(al, al)))

            user_roles = u.get('roles', [])
            role_names = ', '.join(r.get('name', r.get('role_key', '')) for r in user_roles)
            self._table.setItem(row, 4, QTableWidgetItem(role_names or '-'))

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            if enabled:
                roles_btn = QPushButton(texts.USER_ROLES_HEADER)
                roles_btn.setCursor(Qt.PointingHandCursor)
                roles_btn.clicked.connect(lambda _, uid=u['id'], uname=u['username'], uroles=user_roles: self._assign_roles(uid, uname, uroles))
                actions_layout.addWidget(roles_btn)
            else:
                no_btn = QLabel(texts.MODULE_NOT_ENABLED)
                no_btn.setStyleSheet(f"color: {PRIMARY_500}; font-size: {FONT_SIZE_CAPTION};")
                actions_layout.addWidget(no_btn)

            self._table.setCellWidget(row, 5, actions)

    def _assign_roles(self, user_id: int, username: str, current_roles: List[Dict]):
        current_ids = [r.get('role_id', r.get('id', 0)) for r in current_roles]
        dlg = _AssignRolesDialog(username, self._roles_data, current_ids, parent=self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected_role_ids()
            try:
                self._modules_api.assign_user_roles(self._module_key, user_id, selected)
                tm = getattr(self, '_toast_manager', None)
                if tm:
                    tm.show_success(texts.USER_ROLES_ASSIGNED)
                self.load_data()
            except APIError as e:
                tm = getattr(self, '_toast_manager', None)
                if tm:
                    tm.show_error(str(e))
