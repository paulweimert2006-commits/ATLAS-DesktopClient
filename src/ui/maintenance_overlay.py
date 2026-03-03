"""
ATLAS Wartungsmodus-UI

MaintenanceOverlay:  Widget das ueber dem MainHub eingeblendet wird (Betrieb-Sperre).
MaintenanceWindow:   Eigenstaendiges Fenster fuer den Fall dass der Hub gar nicht geoeffnet wird.
SystemStatusChecker: QThread-Worker fuer nicht-blockierende Status-Abfragen.
"""

import logging
import os

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QPainter, QColor, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QMainWindow, QHBoxLayout
)

from i18n import de as texts
from ui.styles.tokens import (
    PRIMARY_900, PRIMARY_500, PRIMARY_100, PRIMARY_0,
    ACCENT_500, BG_PRIMARY, TEXT_PRIMARY, TEXT_SECONDARY,
    FONT_HEADLINE, FONT_BODY, FONT_SIZE_H1, FONT_SIZE_H2,
    FONT_SIZE_BODY, FONT_SIZE_CAPTION, FONT_WEIGHT_MEDIUM,
    RADIUS_LG, SPACING_MD, SPACING_LG,
    get_button_secondary_style,
)

logger = logging.getLogger(__name__)

RECHECK_INTERVAL_MS = 60_000


class SystemStatusCheckWorker(QThread):
    """Fragt /system/status in einem Hintergrund-Thread ab."""
    status_received = Signal(str, str)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api_client = api_client

    def run(self):
        try:
            from api.system_status import SystemStatusAPI
            api = SystemStatusAPI(self._api_client)
            result = api.get_status()
            self.status_received.emit(result.status, result.message or '')
        except Exception as e:
            logger.warning(f"System-Status Check fehlgeschlagen: {e}")
            self.status_received.emit('public', '')


def _build_maintenance_content(parent_layout: QVBoxLayout) -> dict:
    """Erzeugt den gemeinsamen Wartungsmodus-Inhalt. Gibt Label-Referenzen zurueck."""

    container = QFrame()
    container.setObjectName("maintenanceContainer")
    container.setFixedWidth(520)
    container.setStyleSheet(f"""
        QFrame#maintenanceContainer {{
            background-color: {BG_PRIMARY};
            border-radius: {RADIUS_LG};
            border: 1px solid {PRIMARY_100};
        }}
    """)
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(40, 36, 40, 36)
    container_layout.setSpacing(16)

    # Logo
    _src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(_src_dir, "ui", "assets", "icon.ico")
    if os.path.exists(logo_path):
        logo_label = QLabel()
        pixmap = QPixmap(logo_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(logo_label)

    # Headline
    headline = QLabel(texts.MAINTENANCE_HEADLINE)
    headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
    headline.setWordWrap(True)
    headline.setStyleSheet(f"""
        font-family: {FONT_HEADLINE};
        font-size: {FONT_SIZE_H2};
        color: {TEXT_PRIMARY};
        font-weight: {FONT_WEIGHT_MEDIUM};
        margin-top: 8px;
    """)
    container_layout.addWidget(headline)

    # Body
    body = QLabel(texts.MAINTENANCE_BODY)
    body.setAlignment(Qt.AlignmentFlag.AlignCenter)
    body.setWordWrap(True)
    body.setStyleSheet(f"""
        font-family: {FONT_BODY};
        font-size: {FONT_SIZE_BODY};
        color: {TEXT_SECONDARY};
        line-height: 1.5;
    """)
    container_layout.addWidget(body)

    # Server-Nachricht (optional, initial versteckt)
    server_msg_label = QLabel("")
    server_msg_label.setObjectName("serverMsgLabel")
    server_msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    server_msg_label.setWordWrap(True)
    server_msg_label.setVisible(False)
    server_msg_label.setStyleSheet(f"""
        font-family: {FONT_BODY};
        font-size: {FONT_SIZE_BODY};
        color: {ACCENT_500};
        padding: 10px;
        background-color: rgba(250, 153, 57, 0.08);
        border-radius: 6px;
    """)
    container_layout.addWidget(server_msg_label)

    # Kontakt
    contact = QLabel(texts.MAINTENANCE_CONTACT)
    contact.setAlignment(Qt.AlignmentFlag.AlignCenter)
    contact.setWordWrap(True)
    contact.setStyleSheet(f"""
        font-family: {FONT_BODY};
        font-size: {FONT_SIZE_CAPTION};
        color: {TEXT_SECONDARY};
        margin-top: 8px;
    """)
    container_layout.addWidget(contact)

    # Recheck-Info
    recheck = QLabel(texts.MAINTENANCE_RECHECK_INFO)
    recheck.setAlignment(Qt.AlignmentFlag.AlignCenter)
    recheck.setStyleSheet(f"""
        font-family: {FONT_BODY};
        font-size: {FONT_SIZE_CAPTION};
        color: {PRIMARY_500};
        margin-top: 4px;
    """)
    container_layout.addWidget(recheck)

    parent_layout.addWidget(container, alignment=Qt.AlignmentFlag.AlignCenter)

    return {'server_msg_label': server_msg_label, 'container': container}


class MaintenanceOverlay(QWidget):
    """Overlay ueber dem MainHub wenn waehrend des Betriebs der Zugang gesperrt wird."""

    access_restored = Signal()

    def __init__(self, api_client, user, parent=None):
        super().__init__(parent)
        self._api_client = api_client
        self._user = user
        self._worker = None

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        refs = _build_maintenance_content(layout)
        self._server_msg_label = refs['server_msg_label']

        # Schliessen-Button
        close_btn = QPushButton(texts.MAINTENANCE_CLOSE_BTN)
        close_btn.setFixedWidth(160)
        close_btn.setStyleSheet(get_button_secondary_style())
        close_btn.clicked.connect(self._on_close_clicked)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Recheck-Timer
        self._recheck_timer = QTimer(self)
        self._recheck_timer.timeout.connect(self._check_status)

    def show_overlay(self, server_message: str = ''):
        """Overlay einblenden."""
        self._update_server_message(server_message)
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.setVisible(True)
        self.raise_()
        self._recheck_timer.start(RECHECK_INTERVAL_MS)

    def hide_overlay(self):
        """Overlay ausblenden."""
        self._recheck_timer.stop()
        self.setVisible(False)

    def _on_close_clicked(self):
        """App schliessen wenn Nutzer den Button klickt."""
        if self.window():
            self.window().close()

    def _check_status(self):
        """Periodischer Re-Check."""
        if self._worker and self._worker.isRunning():
            return
        self._worker = SystemStatusCheckWorker(self._api_client, self)
        self._worker.status_received.connect(self._on_status_received)
        self._worker.start()

    def _on_status_received(self, status: str, message: str):
        """Ergebnis des Re-Checks verarbeiten."""
        from api.system_status import has_access
        from main import is_dev_mode

        if has_access(status, self._user.is_admin, is_dev_mode()):
            self.hide_overlay()
            self.access_restored.emit()
        else:
            self._update_server_message(message)

    def _update_server_message(self, message: str):
        if message:
            self._server_msg_label.setText(f"{texts.MAINTENANCE_SERVER_MSG}\n{message}")
            self._server_msg_label.setVisible(True)
        else:
            self._server_msg_label.setVisible(False)

    def paintEvent(self, event):
        """Halbtransparenter dunkler Hintergrund."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        super().paintEvent(event)


class MaintenanceWindow(QMainWindow):
    """Eigenstaendiges Fenster wenn beim Login kein Zugang besteht.

    Emittiert access_granted wenn der Status sich aendert und der Nutzer Zugang hat.
    """

    access_granted = Signal()

    def __init__(self, api_client, user, server_message: str = '', parent=None):
        super().__init__(parent)
        self._api_client = api_client
        self._user = user
        self._worker = None

        self.setWindowTitle(texts.MAINTENANCE_TITLE)
        self.setMinimumSize(580, 480)
        self.setStyleSheet(f"background-color: {PRIMARY_900};")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        refs = _build_maintenance_content(layout)
        self._server_msg_label = refs['server_msg_label']

        if server_message:
            self._server_msg_label.setText(f"{texts.MAINTENANCE_SERVER_MSG}\n{server_message}")
            self._server_msg_label.setVisible(True)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        close_btn = QPushButton(texts.MAINTENANCE_CLOSE_BTN)
        close_btn.setFixedWidth(160)
        close_btn.setStyleSheet(get_button_secondary_style())
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Recheck-Timer
        self._recheck_timer = QTimer(self)
        self._recheck_timer.timeout.connect(self._check_status)
        self._recheck_timer.start(RECHECK_INTERVAL_MS)

    def _check_status(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = SystemStatusCheckWorker(self._api_client, self)
        self._worker.status_received.connect(self._on_status_received)
        self._worker.start()

    def _on_status_received(self, status: str, message: str):
        from api.system_status import has_access
        from main import is_dev_mode

        if has_access(status, self._user.is_admin, is_dev_mode()):
            self._recheck_timer.stop()
            self.access_granted.emit()
        else:
            if message:
                self._server_msg_label.setText(f"{texts.MAINTENANCE_SERVER_MSG}\n{message}")
                self._server_msg_label.setVisible(True)
            else:
                self._server_msg_label.setVisible(False)
