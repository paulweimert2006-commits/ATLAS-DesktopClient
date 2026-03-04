# -*- coding: utf-8 -*-
"""
ACENCIA ATLAS - App Router

Shell-Fenster das zwischen Dashboard, MainHub (Core) und ProvisionHub (Ledger)
per QStackedWidget umschaltet. Ersetzt die direkte MainHub-Instanziierung in main.py.
"""

import os
import logging

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from api.client import APIClient
from api.auth import AuthAPI
from i18n import de as texts
from ui.dashboard_screen import DashboardScreen
from ui.toast import ToastManager
from services.global_heartbeat import GlobalHeartbeat
from ui.styles.tokens import (
    FONT_BODY, FONT_SIZE_BODY, PRIMARY_500, BG_PRIMARY,
)

APP_VERSION_FILE = "VERSION"

logger = logging.getLogger(__name__)

_IDX_DASHBOARD = 0
_IDX_CORE = 1
_IDX_LEDGER = 2
_IDX_WORKFORCE = 3


class AppRouter(QMainWindow):
    """Router-Shell: Dashboard -> Core (MainHub) / Ledger (ProvisionHub)."""

    def __init__(self, api_client: APIClient, auth_api: AuthAPI):
        super().__init__()

        self.api_client = api_client
        self.auth_api = auth_api

        username = auth_api.current_user.username if auth_api.current_user else ""
        self.setWindowTitle(f"ACENCIA ATLAS - {username}")
        self.setMinimumSize(1400, 900)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._core_widget = None      # MainHub, lazy
        self._ledger_widget = None    # ProvisionHub, lazy
        self._workforce_widget = None # WorkforceHub, lazy

        app_version = self._read_version()

        user = auth_api.current_user
        visible = ["core"]
        if user and user.is_admin:
            visible.append("admin")
        if user and user.has_permission('provision_access'):
            visible.append("ledger")
        if user and user.has_permission('hr.view'):
            visible.append("workforce")

        self._dashboard = DashboardScreen(
            username=username, app_version=app_version,
            api_client=api_client,
        )
        self._dashboard.set_modules(visible)
        self._dashboard.module_requested.connect(self._open_module)
        self._dashboard.logout_requested.connect(self._on_logout)
        self._stack.addWidget(self._dashboard)  # Index 0

        self._dashboard.load_messages(api_client)

        self._stack.addWidget(QWidget())  # Placeholder Index 1 (Core)
        self._stack.addWidget(QWidget())  # Placeholder Index 2 (Ledger)
        self._stack.addWidget(QWidget())  # Placeholder Index 3 (Workforce)

        self._toast_manager = ToastManager(self)
        self._active_module: str | None = None

        self._heartbeat = GlobalHeartbeat(api_client, auth_api, parent=self)
        self._heartbeat.session_invalid.connect(self._on_session_invalid)
        self._heartbeat.notifications_updated.connect(self._on_notifications_updated)
        self._heartbeat.system_status_changed.connect(self._on_system_status_changed)
        self._heartbeat.start()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_dashboard(self):
        """Zeigt das Dashboard (Index 0)."""
        self._stop_active_module_heartbeat()
        self._active_module = None
        self._stack.setCurrentIndex(_IDX_DASHBOARD)

    def _open_module(self, module_id: str):
        self._stop_active_module_heartbeat()

        if module_id == "core":
            self._ensure_core()
            self._core_widget.reset_to_default_view()
            self._stack.setCurrentIndex(_IDX_CORE)
            self._start_module_heartbeat(self._core_widget, "core")
        elif module_id == "admin":
            user = self.auth_api.current_user
            if not user or not user.is_admin:
                logger.warning("Admin-Zugriff ohne Admin-Recht abgelehnt")
                return
            self._ensure_core()
            self._core_widget.reset_to_default_view()
            self._stack.setCurrentIndex(_IDX_CORE)
            self._core_widget.navigate_to_admin()
            self._start_module_heartbeat(self._core_widget, "core")
        elif module_id == "ledger":
            user = self.auth_api.current_user
            if not user or not user.has_permission('provision_access'):
                logger.warning("Ledger-Zugriff ohne provision_access abgelehnt")
                return
            self._ensure_ledger()
            self._stack.setCurrentIndex(_IDX_LEDGER)
            self._start_module_heartbeat(self._ledger_widget, "ledger")
        elif module_id == "workforce":
            user = self.auth_api.current_user
            if not user or not user.has_permission('hr.view'):
                logger.warning("Workforce-Zugriff ohne hr.view abgelehnt")
                return
            self._ensure_workforce()
            self._stack.setCurrentIndex(_IDX_WORKFORCE)
            self._start_module_heartbeat(self._workforce_widget, "workforce")

    # ------------------------------------------------------------------
    # Module Heartbeat Lifecycle
    # ------------------------------------------------------------------

    def _start_module_heartbeat(self, widget, module_id: str):
        self._active_module = module_id
        if widget and hasattr(widget, 'start_module_heartbeat'):
            widget.start_module_heartbeat()

    def _stop_active_module_heartbeat(self):
        if not self._active_module:
            return
        widget = self._get_active_module_widget()
        if widget and hasattr(widget, 'stop_module_heartbeat'):
            widget.stop_module_heartbeat()

    def _get_active_module_widget(self):
        if self._active_module == "core":
            return self._core_widget
        elif self._active_module == "ledger":
            return self._ledger_widget
        elif self._active_module == "workforce":
            return self._workforce_widget
        return None

    # ------------------------------------------------------------------
    # Global Heartbeat Callbacks
    # ------------------------------------------------------------------

    def _on_session_invalid(self):
        logger.warning("GlobalHeartbeat: Session ungueltig -- Forced Logout")
        self._heartbeat.stop()
        self._stop_active_module_heartbeat()
        if hasattr(self.api_client, '_trigger_forced_logout'):
            self.api_client._trigger_forced_logout("Session abgelaufen")
        else:
            self.auth_api.logout()
            self.close()

    def _on_notifications_updated(self, summary: dict):
        self._dashboard.on_notifications_updated(summary)
        if self._core_widget and hasattr(self._core_widget, 'on_notifications_updated'):
            self._core_widget.on_notifications_updated(summary)

    def _on_system_status_changed(self, status: str, message: str):
        if self._core_widget and hasattr(self._core_widget, 'on_system_status_changed'):
            self._core_widget.on_system_status_changed(status, message)

    # ------------------------------------------------------------------
    # Lazy Init
    # ------------------------------------------------------------------

    def _ensure_core(self):
        if self._core_widget is not None:
            return
        from ui.main_hub import MainHub
        hub = MainHub(api_client=self.api_client, auth_api=self.auth_api)
        hub.back_to_dashboard_requested.connect(self.show_dashboard)
        self._core_widget = hub

        old = self._stack.widget(_IDX_CORE)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(_IDX_CORE, hub)

    def _ensure_ledger(self):
        if self._ledger_widget is not None:
            return
        try:
            from ui.provision.provision_hub import ProvisionHub
            widget = ProvisionHub(self.api_client, self.auth_api)
            widget._toast_manager = self._toast_manager
            widget.back_requested.connect(self.show_dashboard)
        except Exception:
            logger.exception("ProvisionHub konnte nicht geladen werden, zeige Placeholder")
            widget = self._create_ledger_placeholder()
        self._ledger_widget = widget

        old = self._stack.widget(_IDX_LEDGER)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(_IDX_LEDGER, widget)

    def _ensure_workforce(self):
        if self._workforce_widget is not None:
            return
        try:
            from ui.workforce.workforce_hub import WorkforceHub
            widget = WorkforceHub(self.api_client, self.auth_api)
            widget._toast_manager = self._toast_manager
            widget.back_requested.connect(self.show_dashboard)
        except Exception:
            logger.exception("WorkforceHub konnte nicht geladen werden, zeige Placeholder")
            widget = self._create_workforce_placeholder()
        self._workforce_widget = widget

        old = self._stack.widget(_IDX_WORKFORCE)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(_IDX_WORKFORCE, widget)

    def _create_workforce_placeholder(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        lbl = QLabel(texts.WF_DASHBOARD_TILE)
        lbl.setStyleSheet(
            f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY}; color: {PRIMARY_500};"
        )
        layout.addWidget(lbl, alignment=Qt.AlignCenter)
        w.setStyleSheet(f"background-color: {BG_PRIMARY};")
        return w

    def _create_ledger_placeholder(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        lbl = QLabel(texts.DASHBOARD_TILE_LEDGER)
        lbl.setStyleSheet(
            f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY}; color: {PRIMARY_500};"
        )
        layout.addWidget(lbl, alignment=Qt.AlignCenter)
        w.setStyleSheet(f"background-color: {BG_PRIMARY};")
        return w

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def _on_logout(self):
        reply = QMessageBox.question(
            self,
            texts.NAV_ABMELDEN,
            texts.LOGOUT_CONFIRM
            if hasattr(texts, "LOGOUT_CONFIRM")
            else "Wirklich abmelden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._heartbeat.stop()
            self._stop_active_module_heartbeat()
            self.auth_api.logout()
            self.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_version() -> str:
        try:
            import main as _m
            return getattr(_m, "APP_VERSION", "")
        except Exception:
            return ""
