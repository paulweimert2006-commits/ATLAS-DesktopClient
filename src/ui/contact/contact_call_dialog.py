# -*- coding: utf-8 -*-
"""
Contact Call Dialog - Dialog zum Anlegen eines neuen Telefonat-Eintrags.
"""

import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QTextEdit, QCheckBox, QDateEdit, QTimeEdit, QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Signal, Qt, QDate, QTime

from contact.api_client import ContactApiClient
from ui.styles.tokens import (
    FONT_BODY, FONT_SIZE_BODY,
    BG_PRIMARY, BORDER_DEFAULT, RADIUS_MD, PRIMARY_900,
    get_button_primary_style, get_button_secondary_style,
)
from i18n import de as texts

logger = logging.getLogger(__name__)

_INPUT = (
    f"background-color: {BG_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; "
    f"border-radius: {RADIUS_MD}; padding: 8px 12px; "
    f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY};"
)


class ContactCallDialog(QDialog):
    """Dialog zum Anlegen eines neuen Telefonat-Eintrags."""

    call_saved = Signal()

    def __init__(self, contact_api: ContactApiClient, contact_id: int, parent=None):
        super().__init__(parent)
        self._api = contact_api
        self._cid = contact_id

        self.setWindowTitle(texts.CONTACT_CALL_NEW)
        self.setMinimumWidth(460)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_PRIMARY}; }}
            QLabel {{ font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY}; color: {PRIMARY_900}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        form = QFormLayout()
        form.setSpacing(8)

        self._combo_dir = QComboBox()
        self._combo_dir.addItem(texts.CONTACT_CALL_INBOUND, "inbound")
        self._combo_dir.addItem(texts.CONTACT_CALL_OUTBOUND, "outbound")
        self._combo_dir.setStyleSheet(f"QComboBox {{ {_INPUT} }}")
        form.addRow(texts.CONTACT_CALL_DIRECTION + ":", self._combo_dir)

        self._edit_subject = QLineEdit()
        self._edit_subject.setPlaceholderText(texts.CONTACT_CALL_SUBJECT)
        self._edit_subject.setStyleSheet(f"QLineEdit {{ {_INPUT} }}")
        form.addRow(texts.CONTACT_CALL_SUBJECT + ":", self._edit_subject)

        self._edit_note = QTextEdit()
        self._edit_note.setPlaceholderText(texts.CONTACT_CALL_NOTE)
        self._edit_note.setMaximumHeight(80)
        self._edit_note.setStyleSheet(f"QTextEdit {{ {_INPUT} }}")
        form.addRow(texts.CONTACT_CALL_NOTE + ":", self._edit_note)

        self._chk_cb = QCheckBox(texts.CONTACT_CALL_CALLBACK_NEEDED)
        self._chk_cb.setStyleSheet(
            f"QCheckBox {{ font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY}; color: {PRIMARY_900}; }}"
        )
        self._chk_cb.toggled.connect(self._toggle_cb_fields)
        form.addRow(self._chk_cb)

        self._de = QDateEdit()
        self._de.setCalendarPopup(True)
        self._de.setDate(QDate.currentDate())
        self._de.setDisplayFormat("dd.MM.yyyy")
        self._de.setStyleSheet(f"QDateEdit {{ {_INPUT} }}")
        self._de.setVisible(False)
        form.addRow(texts.CONTACT_CALL_CALLBACK_DATE + ":", self._de)

        self._te = QTimeEdit()
        self._te.setTime(QTime(9, 0))
        self._te.setDisplayFormat("HH:mm")
        self._te.setStyleSheet(f"QTimeEdit {{ {_INPUT} }}")
        self._te.setVisible(False)
        form.addRow(texts.CONTACT_CALL_CALLBACK_TIME + ":", self._te)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(texts.CANCEL)
        cancel_btn.setStyleSheet(get_button_secondary_style())
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        self._save_btn = QPushButton(texts.SAVE)
        self._save_btn.setStyleSheet(get_button_primary_style())
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        btn_row.addWidget(self._save_btn)
        layout.addLayout(btn_row)

    def _toggle_cb_fields(self, checked: bool):
        self._de.setVisible(checked)
        self._te.setVisible(checked)

    def _save(self):
        self._save_btn.setEnabled(False)
        self._save_btn.setText("...")

        data = {
            "direction": self._combo_dir.currentData() or "inbound",
            "subject": self._edit_subject.text().strip(),
            "note": self._edit_note.toPlainText().strip(),
            "callback_needed": 1 if self._chk_cb.isChecked() else 0,
            "status": "open",
        }

        if self._chk_cb.isChecked():
            d = self._de.date().toString("yyyy-MM-dd")
            t = self._te.time().toString("HH:mm")
            data["callback_at"] = f"{d} {t}:00"

        try:
            self._api.create_call(self._cid, data)
            self.call_saved.emit()
            self.accept()
        except Exception as e:
            logger.error("Telefonat speichern: %s", e)
            self._save_btn.setEnabled(True)
            self._save_btn.setText(texts.SAVE)
