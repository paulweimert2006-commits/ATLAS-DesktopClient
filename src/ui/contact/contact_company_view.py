"""
ContactCompanyView - Firmenverwaltung im Contact-Modul.

Zeigt Firmen als Karten in einer scrollbaren Liste.
Neue Firma per Dialog (mit Berechtigung contact.companies).
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QDialog, QFormLayout, QLineEdit,
)
from PySide6.QtCore import Signal, Qt, QThread

from contact.api_client import ContactApiClient
from ui.styles.tokens import (
    PRIMARY_500, PRIMARY_900, ACCENT_500, FONT_BODY,
    FONT_SIZE_BODY, FONT_SIZE_CAPTION, FONT_SIZE_H2,
    BG_PRIMARY, BORDER_DEFAULT, RADIUS_MD,
    get_button_primary_style, get_button_secondary_style,
)
from i18n import de as texts

logger = logging.getLogger(__name__)


class _CompanyLoadWorker(QThread):
    """Laedt Firmen im Hintergrund."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, api: ContactApiClient):
        super().__init__()
        self._api = api

    def run(self):
        try:
            companies = self._api.list_companies()
            self.finished.emit(companies)
        except Exception as e:
            logger.error("Firmen laden fehlgeschlagen: %s", e)
            self.error.emit(str(e))


class _CompanyCreateWorker(QThread):
    """Erstellt eine neue Firma im Hintergrund."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, api: ContactApiClient, data: dict):
        super().__init__()
        self._api = api
        self._data = data

    def run(self):
        try:
            result = self._api.create_company(self._data)
            self.finished.emit(result)
        except Exception as e:
            logger.error("Firma erstellen fehlgeschlagen: %s", e)
            self.error.emit(str(e))


class _CompanyCard(QFrame):
    """Karten-Widget fuer eine Firma."""

    def __init__(self, company: dict, parent=None):
        super().__init__(parent)
        self._company = company
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumWidth(280)
        self.setMinimumHeight(100)
        self.setObjectName("company_card")
        self.setStyleSheet(f"""
            QFrame#company_card {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        name = self._company.get("name", "") or "-"
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            font-family: {FONT_BODY}; font-size: {FONT_SIZE_H2};
            color: {PRIMARY_900}; font-weight: 600;
        """)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        phone = self._company.get("phone_central", "") or ""
        if phone:
            phone_label = QLabel(f"{texts.CONTACT_COMPANY_PHONE_CENTRAL}: {phone}")
            phone_label.setStyleSheet(f"""
                font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY};
                color: {PRIMARY_500};
            """)
            layout.addWidget(phone_label)

        email = self._company.get("email_domain", "") or ""
        if email:
            email_label = QLabel(f"{texts.CONTACT_COMPANY_EMAIL_DOMAIN}: {email}")
            email_label.setStyleSheet(f"""
                font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY};
                color: {PRIMARY_500};
            """)
            layout.addWidget(email_label)

        count = self._company.get("contact_count", 0)
        count_label = QLabel(f"{count} {texts.CONTACT_COMPANY_CONTACT_COUNT}")
        count_label.setStyleSheet(f"""
            font-family: {FONT_BODY}; font-size: {FONT_SIZE_CAPTION};
            color: {PRIMARY_500};
        """)
        layout.addWidget(count_label)


class _CreateCompanyDialog(QDialog):
    """Dialog zum Anlegen einer neuen Firma."""

    def __init__(self, parent=None, prefill_name: str = ''):
        super().__init__(parent)
        self._prefill_name = prefill_name
        self.setWindowTitle(texts.CONTACT_COMPANY_NEW)
        self.setMinimumWidth(360)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._name_input = QLineEdit(self._prefill_name)
        self._name_input.setPlaceholderText(texts.CONTACT_COMPANY_NAME)
        form.addRow(texts.CONTACT_COMPANY_NAME, self._name_input)

        self._phone_input = QLineEdit()
        self._phone_input.setPlaceholderText(texts.CONTACT_COMPANY_PHONE_CENTRAL)
        form.addRow(texts.CONTACT_COMPANY_PHONE_CENTRAL, self._phone_input)

        self._email_input = QLineEdit()
        self._email_input.setPlaceholderText(texts.CONTACT_COMPANY_EMAIL_DOMAIN)
        form.addRow(texts.CONTACT_COMPANY_EMAIL_DOMAIN, self._email_input)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton(texts.CANCEL)
        cancel_btn.setStyleSheet(get_button_secondary_style())
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton(texts.SAVE)
        save_btn.setStyleSheet(get_button_primary_style())
        save_btn.clicked.connect(self.accept)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def get_data(self) -> dict:
        return {
            "name": self._name_input.text().strip(),
            "phone_central": self._phone_input.text().strip() or None,
            "email_domain": self._email_input.text().strip() or None,
        }


class ContactCompanyView(QWidget):
    """Firmenverwaltung im Contact-Modul."""

    def __init__(self, contact_api: ContactApiClient, auth_api=None):
        super().__init__()
        self._contact_api = contact_api
        self._auth_api = auth_api
        self._toast_manager = None
        self._load_worker = None
        self._create_worker = None

        self._setup_ui()

    def _has_create_permission(self) -> bool:
        """Prueft ob der Benutzer Firmen anlegen darf."""
        if not self._auth_api:
            return True
        user = self._auth_api.current_user
        if not user:
            return False
        return user.has_permission("contact.companies") or user.is_module_admin("contact")

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel(texts.CONTACT_NAV_COMPANIES)
        title.setStyleSheet(f"""
            font-family: {FONT_BODY}; font-size: {FONT_SIZE_H2};
            color: {PRIMARY_900}; font-weight: 600;
        """)
        header.addWidget(title)
        header.addStretch()

        if self._has_create_permission():
            new_btn = QPushButton(texts.CONTACT_COMPANY_NEW)
            new_btn.setStyleSheet(get_button_primary_style())
            new_btn.setCursor(Qt.PointingHandCursor)
            new_btn.clicked.connect(self._on_create_company)
            header.addWidget(new_btn)

        root.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.setAlignment(Qt.AlignTop)

        self._scroll.setWidget(self._cards_container)
        root.addWidget(self._scroll)

        self._loading_label = QLabel(texts.CONTACT_COMPANY_LOADING)
        self._loading_label.setStyleSheet(f"""
            font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY};
            color: {PRIMARY_500};
        """)
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._cards_layout.addWidget(self._loading_label)

        self.refresh()

    def refresh(self):
        """Laedt die Firmenliste neu."""
        if self._load_worker and self._load_worker.isRunning():
            return
        self._loading_label.setVisible(True)
        self._load_worker = _CompanyLoadWorker(self._contact_api)
        self._load_worker.finished.connect(self._on_company_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_company_loaded(self, companies: list):
        """Rendert die Firmenkarten."""
        self._loading_label.setVisible(False)

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            w = item.widget()
            if w and w != self._loading_label:
                w.deleteLater()

        if not companies:
            empty = QLabel(texts.CONTACT_COMPANY_EMPTY)
            empty.setStyleSheet(f"""
                font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY};
                color: {PRIMARY_500};
            """)
            empty.setAlignment(Qt.AlignCenter)
            self._cards_layout.addWidget(empty)
            self._cards_layout.addWidget(self._loading_label)
            self._loading_label.setVisible(False)
            return

        for company in companies:
            card = _CompanyCard(company)
            self._cards_layout.addWidget(card)

        self._cards_layout.addWidget(self._loading_label)
        self._loading_label.setVisible(False)

    def _on_load_error(self, error: str):
        """Behandelt Ladefehler."""
        self._loading_label.setVisible(False)
        self._loading_label.setText(f"{texts.CONTACT_COMPANY_LOADING}: {error}")
        self._loading_label.setVisible(True)
        logger.error("Firmen laden: %s", error)
        if self._toast_manager:
            self._toast_manager.show_error(error)

    def open_create_dialog(self, prefill_name: str = ''):
        """Oeffentliche Methode zum Oeffnen des Anlage-Dialogs mit optionalem Vorbefuellen."""
        self._on_create_company(prefill_name)

    def _on_create_company(self, prefill_name: str = ''):
        """Oeffnet den Dialog zum Anlegen einer neuen Firma."""
        dialog = _CreateCompanyDialog(self, prefill_name=prefill_name)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_data()
        if not data["name"]:
            if self._toast_manager:
                self._toast_manager.show_warning(texts.CONTACT_COMPANY_NAME_REQUIRED)
            return

        if self._create_worker and self._create_worker.isRunning():
            return
        self._create_worker = _CompanyCreateWorker(self._contact_api, data)
        self._create_worker.finished.connect(self._on_company_created)
        self._create_worker.error.connect(self._on_create_error)
        self._create_worker.start()

    def _on_company_created(self, _result: dict):
        """Nach erfolgreichem Anlegen: Liste neu laden."""
        if self._toast_manager:
            self._toast_manager.show_success(texts.CONTACT_COMPANY_SAVED)
        self.refresh()

    def _on_create_error(self, error: str):
        """Behandelt Fehler beim Anlegen."""
        logger.error("Firma erstellen: %s", error)
        if self._toast_manager:
            self._toast_manager.show_error(error)
