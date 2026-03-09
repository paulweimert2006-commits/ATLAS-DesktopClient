"""
ACENCIA ATLAS - Universe Selector Dialog

Wird angezeigt wenn ein Benutzer Zugriff auf mehrere Universes hat.
Zeigt Karten mit Name, Rolle und Status.
"""

import logging
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from api.auth import TenantInfo
from i18n import de as t

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    'tenant_owner': t.UNIVERSE_ROLE_OWNER,
    'tenant_admin': t.UNIVERSE_ROLE_ADMIN,
    'tenant_user': t.UNIVERSE_ROLE_USER,
}

STATUS_LABELS = {
    'active': t.UNIVERSE_STATUS_ACTIVE,
    'maintenance': t.UNIVERSE_STATUS_MAINTENANCE,
    'suspended': t.UNIVERSE_STATUS_SUSPENDED,
}


class UniverseCard(QFrame):
    """Einzelne Universe-Karte."""

    clicked = Signal(int)

    def __init__(self, tenant: TenantInfo, parent=None):
        super().__init__(parent)
        self.tenant = tenant
        self.setObjectName("universeCard")
        self._enabled = tenant.status == 'active'
        self.setCursor(Qt.PointingHandCursor if self._enabled else Qt.ForbiddenCursor)
        self.setFrameShape(QFrame.StyledPanel)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        header = QHBoxLayout()

        name_label = QLabel(self.tenant.tenant_name)
        name_font = QFont()
        name_font.setPointSize(13)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #1e293b;")
        header.addWidget(name_label)

        status_text = STATUS_LABELS.get(self.tenant.status, self.tenant.status)
        status_label = QLabel(status_text)
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if self.tenant.status == 'active':
            status_label.setStyleSheet("color: #16a34a; font-weight: bold;")
        elif self.tenant.status == 'maintenance':
            status_label.setStyleSheet("color: #d97706; font-weight: bold;")
        else:
            status_label.setStyleSheet("color: #dc2626; font-weight: bold;")
        header.addWidget(status_label)
        layout.addLayout(header)

        role_text = ROLE_LABELS.get(self.tenant.role, self.tenant.role)
        role_label = QLabel(role_text)
        role_label.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(role_label)

        if self.tenant.status == 'maintenance':
            hint = QLabel(t.UNIVERSE_MAINTENANCE_HINT)
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #d97706; font-size: 11px; margin-top: 4px;")
            layout.addWidget(hint)

        if not self._enabled:
            self.setStyleSheet(
                "QFrame#universeCard { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#universeCard { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; }"
                "QFrame#universeCard:hover { border-color: #6366f1; background: #eef2ff; }"
            )

    def mousePressEvent(self, event):
        if self._enabled and event.button() == Qt.LeftButton:
            self.clicked.emit(self.tenant.tenant_id)
        super().mousePressEvent(event)


class UniverseSelectorDialog(QDialog):
    """Dialog zur Auswahl eines Universe."""

    universe_selected = Signal(int)

    def __init__(self, tenants: List[TenantInfo], parent=None):
        super().__init__(parent)
        self.tenants = tenants
        self.selected_tenant_id: Optional[int] = None
        self.setWindowTitle(t.UNIVERSE_SELECT_TITLE)
        self.setMinimumSize(420, 300)
        self.setMaximumSize(600, 600)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel(t.UNIVERSE_SELECT_TITLE)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(t.UNIVERSE_SELECT_SUBTITLE)
        subtitle.setStyleSheet("color: #64748b; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        cards_layout = QVBoxLayout(container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(8)

        for tenant in self.tenants:
            card = UniverseCard(tenant)
            card.clicked.connect(self._on_card_clicked)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        cancel_btn = QPushButton(t.CANCEL)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignRight)

    def _on_card_clicked(self, tenant_id: int):
        self.selected_tenant_id = tenant_id
        self.universe_selected.emit(tenant_id)
        self.accept()
