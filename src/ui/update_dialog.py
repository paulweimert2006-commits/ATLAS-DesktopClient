"""
ACENCIA ATLAS - Update-Dialog

Zeigt verfuegbare Updates an und ermoeglicht Download + Installation.
Drei Modi: optional, mandatory, deprecated.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from services.update_service import UpdateInfo, UpdateService, UpdateDownloadError
from api.client import APIClient
from i18n import de as texts

from ui.styles.tokens import (
    PRIMARY_900, PRIMARY_500, PRIMARY_100, PRIMARY_0,
    ACCENT_500, ACCENT_100,
    FONT_HEADLINE, FONT_BODY,
    FONT_SIZE_H2, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    RADIUS_MD
)

logger = logging.getLogger(__name__)


def _format_file_size(size_bytes: int) -> str:
    """Formatiert Bytes in lesbare Groesse."""
    if size_bytes <= 0:
        return "Unbekannt"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class DownloadWorker(QThread):
    """Worker-Thread fuer den Download des Installers."""
    progress = Signal(int, int)  # bytes_downloaded, total_bytes
    finished = Signal(str)       # Pfad zur heruntergeladenen Datei
    error = Signal(str)          # Fehlermeldung
    
    def __init__(self, update_service: UpdateService, update_info: UpdateInfo):
        super().__init__()
        self._service = update_service
        self._info = update_info
    
    def run(self):
        try:
            path = self._service.download_update(
                self._info,
                progress_callback=self._on_progress
            )
            self.finished.emit(str(path))
        except UpdateDownloadError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))
    
    def _on_progress(self, downloaded: int, total: int):
        self.progress.emit(downloaded, total)


class UpdateDialog(QDialog):
    """
    Dialog fuer App-Updates.
    
    Modi:
    - 'optional': Update verfuegbar, "Spaeter" moeglich
    - 'mandatory': Pflicht-Update, kein Schliessen moeglich
    - 'deprecated': Veraltete Version, nur Warnung
    """
    
    def __init__(self, update_info: UpdateInfo, update_service: UpdateService,
                 mode: str = 'optional', parent=None):
        super().__init__(parent)
        
        self._update_info = update_info
        self._update_service = update_service
        self._mode = mode
        self._download_worker: Optional[DownloadWorker] = None
        self._downloaded_path: Optional[str] = None
        self._is_downloading = False
        
        self._setup_ui()
        self._apply_mode()
    
    def _setup_ui(self):
        """Baut die UI auf."""
        self.setMinimumWidth(500)
        self.setMaximumWidth(600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # === Titel ===
        self._title_label = QLabel()
        self._title_label.setFont(QFont(FONT_HEADLINE, 16, QFont.Bold))
        self._title_label.setStyleSheet(f"color: {PRIMARY_900};")
        layout.addWidget(self._title_label)
        
        # === Versions-Info ===
        version_frame = QFrame()
        version_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {PRIMARY_100};
                border-radius: {RADIUS_MD};
                padding: 12px;
            }}
        """)
        version_layout = QVBoxLayout(version_frame)
        version_layout.setContentsMargins(16, 12, 16, 12)
        
        self._new_version_label = QLabel(
            texts.UPDATE_NEW_VERSION.format(version=self._update_info.latest_version)
        )
        self._new_version_label.setFont(QFont(FONT_BODY, 12, QFont.Bold))
        self._new_version_label.setStyleSheet(f"color: {PRIMARY_900};")
        version_layout.addWidget(self._new_version_label)
        
        self._current_version_label = QLabel(
            texts.UPDATE_CURRENT_VERSION.format(version=self._update_info.current_version)
        )
        self._current_version_label.setStyleSheet(f"color: {PRIMARY_500};")
        version_layout.addWidget(self._current_version_label)
        
        layout.addWidget(version_frame)
        
        # === Release Notes ===
        if self._update_info.release_notes:
            notes_label = QLabel(texts.UPDATE_RELEASE_NOTES)
            notes_label.setFont(QFont(FONT_BODY, 10, QFont.Bold))
            notes_label.setStyleSheet(f"color: {PRIMARY_900};")
            layout.addWidget(notes_label)
            
            self._notes_text = QTextEdit()
            self._notes_text.setReadOnly(True)
            self._notes_text.setPlainText(self._update_info.release_notes)
            self._notes_text.setMaximumHeight(150)
            self._notes_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {PRIMARY_0};
                    border: 1px solid {PRIMARY_100};
                    border-radius: {RADIUS_MD};
                    padding: 8px;
                    font-family: {FONT_BODY};
                    font-size: {FONT_SIZE_BODY};
                    color: {PRIMARY_900};
                }}
            """)
            layout.addWidget(self._notes_text)
        
        # === Dateigroesse ===
        if self._update_info.file_size > 0:
            size_label = QLabel(
                texts.UPDATE_FILE_SIZE.format(
                    size=_format_file_size(self._update_info.file_size)
                )
            )
            size_label.setStyleSheet(f"color: {PRIMARY_500}; font-size: {FONT_SIZE_CAPTION};")
            layout.addWidget(size_label)
        
        # === Progress-Bereich (anfangs versteckt) ===
        self._progress_frame = QFrame()
        progress_layout = QVBoxLayout(self._progress_frame)
        progress_layout.setContentsMargins(0, 8, 0, 8)
        
        self._progress_label = QLabel(texts.UPDATE_DOWNLOADING)
        self._progress_label.setStyleSheet(f"color: {PRIMARY_500};")
        progress_layout.addWidget(self._progress_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {PRIMARY_100};
                border-radius: {RADIUS_MD};
                background-color: {PRIMARY_100};
                text-align: center;
                height: 24px;
                font-size: {FONT_SIZE_CAPTION};
                color: {PRIMARY_900};
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_500};
                border-radius: {RADIUS_MD};
            }}
        """)
        progress_layout.addWidget(self._progress_bar)
        
        self._progress_detail = QLabel("")
        self._progress_detail.setStyleSheet(f"color: {PRIMARY_500}; font-size: {FONT_SIZE_CAPTION};")
        progress_layout.addWidget(self._progress_detail)
        
        self._progress_frame.setVisible(False)
        layout.addWidget(self._progress_frame)
        
        # === Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._later_btn = QPushButton(texts.UPDATE_LATER)
        self._later_btn.setMinimumWidth(120)
        self._later_btn.setMinimumHeight(36)
        self._later_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_100};
                color: {PRIMARY_900};
                border: none;
                border-radius: {RADIUS_MD};
                padding: 8px 20px;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_BODY};
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_500};
                color: {PRIMARY_0};
            }}
        """)
        self._later_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._later_btn)
        
        self._install_btn = QPushButton(texts.UPDATE_INSTALL_NOW)
        self._install_btn.setMinimumWidth(160)
        self._install_btn.setMinimumHeight(36)
        self._install_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_500};
                color: {PRIMARY_0};
                border: none;
                border-radius: {RADIUS_MD};
                padding: 8px 20px;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_BODY};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #e0872f;
            }}
            QPushButton:disabled {{
                background-color: {PRIMARY_100};
                color: {PRIMARY_500};
            }}
        """)
        self._install_btn.clicked.connect(self._start_download)
        button_layout.addWidget(self._install_btn)
        
        layout.addLayout(button_layout)
    
    def _apply_mode(self):
        """Passt die UI an den Modus an."""
        if self._mode == 'mandatory':
            self.setWindowTitle(texts.UPDATE_MANDATORY_TITLE)
            self._title_label.setText(texts.UPDATE_MANDATORY_TITLE)
            self._later_btn.setVisible(False)
            # Kein Schliessen moeglich
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowCloseButtonHint
            )
        elif self._mode == 'deprecated':
            self.setWindowTitle(texts.UPDATE_DEPRECATED_TITLE)
            self._title_label.setText(texts.UPDATE_DEPRECATED_TITLE)
            if not self._update_info.update_available:
                self._install_btn.setVisible(False)
                self._later_btn.setText("OK")
        else:
            self.setWindowTitle(texts.UPDATE_AVAILABLE_TITLE)
            self._title_label.setText(texts.UPDATE_AVAILABLE_TITLE)
    
    def _start_download(self):
        """Startet den Download des Updates."""
        if self._is_downloading:
            return
        
        self._is_downloading = True
        self._install_btn.setEnabled(False)
        self._install_btn.setText(texts.UPDATE_DOWNLOADING)
        self._later_btn.setEnabled(False)
        self._progress_frame.setVisible(True)
        
        self._download_worker = DownloadWorker(self._update_service, self._update_info)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()
    
    def _on_download_progress(self, downloaded: int, total: int):
        """Aktualisiert den Fortschritt."""
        if total > 0:
            percent = int(downloaded / total * 100)
            self._progress_bar.setValue(percent)
            self._progress_detail.setText(
                texts.UPDATE_DOWNLOAD_PROGRESS.format(
                    downloaded=_format_file_size(downloaded),
                    total=_format_file_size(total)
                )
            )
        else:
            self._progress_detail.setText(_format_file_size(downloaded))
    
    def _on_download_finished(self, path: str):
        """Download erfolgreich abgeschlossen - Installation sofort starten."""
        self._downloaded_path = path
        self._progress_label.setText(texts.UPDATE_VERIFYING)
        self._progress_bar.setValue(100)
        
        self._progress_label.setText(texts.UPDATE_INSTALLING)
        
        # Installation direkt starten (kein Dialog)
        try:
            from pathlib import Path
            self._update_service.install_update(Path(path))
            self.accept()
        except UpdateDownloadError as e:
            self._on_download_error(str(e))
    
    def _on_download_error(self, error_msg: str):
        """Download fehlgeschlagen."""
        self._is_downloading = False
        self._progress_frame.setVisible(False)
        self._install_btn.setEnabled(True)
        self._install_btn.setText(texts.UPDATE_INSTALL_NOW)
        
        if self._mode != 'mandatory':
            self._later_btn.setEnabled(True)
        
        # Fehler als Status-Text im Dialog anzeigen (kein modales Popup)
        self._progress_frame.setVisible(True)
        self._progress_bar.setVisible(False)
        self._progress_detail.setVisible(False)
        self._progress_label.setText(texts.UPDATE_ERROR_DOWNLOAD.format(error=error_msg))
        self._progress_label.setStyleSheet("color: #dc2626; font-weight: bold;")
    
    def closeEvent(self, event):
        """Verhindert Schliessen bei Pflicht-Update."""
        if self._mode == 'mandatory' and not self._downloaded_path:
            event.ignore()
            return
        
        # Worker aufraumen
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.quit()
            self._download_worker.wait(3000)
        
        super().closeEvent(event)
    
    def keyPressEvent(self, event):
        """Verhindert Escape bei Pflicht-Update."""
        if self._mode == 'mandatory' and event.key() == Qt.Key_Escape:
            return
        super().keyPressEvent(event)
