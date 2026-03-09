# -*- coding: utf-8 -*-
"""
Contact Detail Overlay - Modales Vollbild-Overlay fuer Kontaktdetails.

Alle Sektionen untereinander in einem scrollbaren Panel.
Speichern-Button immer sichtbar am unteren Rand.
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFormLayout, QLineEdit, QDateEdit, QComboBox,
    QTextEdit, QScrollArea, QGraphicsOpacityEffect,
    QDialog, QDialogButtonBox, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QThread, QDate, QTimer
from PySide6.QtGui import QColor, QPainter

from contact.api_client import ContactApiClient
from api.auth import AuthAPI
from ui.styles.tokens import (
    PRIMARY_500, PRIMARY_900, ACCENT_500, FONT_BODY,
    FONT_SIZE_BODY, FONT_SIZE_CAPTION, FONT_SIZE_H2,
    BG_PRIMARY, BG_SECONDARY, BORDER_DEFAULT, RADIUS_MD,
    PRIMARY_0, PRIMARY_100, FONT_WEIGHT_BOLD,
    get_button_primary_style, get_button_secondary_style,
)
from i18n import de as texts
from ui.contact.contact_card_widget import _format_date, _format_datetime

logger = logging.getLogger(__name__)

_SECTION_STYLE = (
    f"font-family: {FONT_BODY}; font-size: 11pt; font-weight: {FONT_WEIGHT_BOLD}; "
    f"color: {PRIMARY_900}; background: transparent; border: none; padding-top: 12px;"
)
_ROW_STYLE = (
    f"background-color: {BG_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; "
    f"border-radius: 6px; padding: 6px 10px;"
)
_LBL_STYLE = (
    f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY}; "
    f"color: {PRIMARY_900}; border: none; background: transparent;"
)


class _LoadWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, api: ContactApiClient, cid: int):
        super().__init__()
        self._api, self._cid = api, cid

    def run(self):
        try:
            self.finished.emit(self._api.get_contact(self._cid))
        except Exception as e:
            self.error.emit(str(e))


class ContactDetailOverlay(QWidget):
    contact_updated = Signal()
    close_requested = Signal()

    def __init__(self, contact_api: ContactApiClient, auth_api: AuthAPI, parent=None):
        super().__init__(parent)
        self._api = contact_api
        self._auth = auth_api
        self._cid: int | None = None
        self._data: dict = {}
        self._is_new = False
        self._worker = None
        self._anim = None
        self._open_call_dialog_pending = False

        self.setVisible(False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignCenter)

        self._panels_row = QHBoxLayout()
        self._panels_row.setSpacing(12)
        self._panels_row.setAlignment(Qt.AlignCenter)

        self._panel = QFrame()
        self._panel.setObjectName("cdPanel")
        self._panel.setMinimumSize(680, 500)
        self._panel.setMaximumSize(760, 900)
        self._panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._panel.setStyleSheet(f"""
            QFrame#cdPanel {{
                background-color: {PRIMARY_0};
                border-radius: {RADIUS_MD};
                border: 1px solid {BORDER_DEFAULT};
            }}
        """)

        pl = QVBoxLayout(self._panel)
        pl.setContentsMargins(28, 20, 28, 16)
        pl.setSpacing(0)

        # ── Header ──
        hdr = QHBoxLayout()
        self._name_lbl = QLabel()
        self._name_lbl.setStyleSheet(
            f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_H2}; "
            f"font-weight: {FONT_WEIGHT_BOLD}; color: {PRIMARY_900}; "
            f"background: transparent; border: none;"
        )
        self._name_lbl.setWordWrap(True)
        hdr.addWidget(self._name_lbl, 1)

        self._fav_btn = QPushButton("\u2606")
        self._fav_btn.setCursor(Qt.PointingHandCursor)
        self._fav_btn.setFixedSize(44, 44)
        self._fav_btn.setMinimumSize(44, 44)
        self._fav_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY_100}; border: 1px solid {BORDER_DEFAULT}; "
            f"border-radius: 22px; font-size: 22pt; color: {PRIMARY_500}; min-width: 44px; min-height: 44px; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_100}; color: {ACCENT_500}; border-color: {ACCENT_500}; }}"
        )
        self._fav_btn.clicked.connect(self._toggle_favorite)
        hdr.addWidget(self._fav_btn)

        close_btn = QPushButton("\u2715")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(44, 44)
        close_btn.setMinimumSize(44, 44)
        close_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY_100}; border: 1px solid {BORDER_DEFAULT}; "
            f"border-radius: 22px; font-size: 20pt; font-weight: bold; "
            f"color: {PRIMARY_900}; min-width: 44px; min-height: 44px; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_100}; color: {ACCENT_500}; border-color: {ACCENT_500}; }}"
        )
        close_btn.clicked.connect(self._close)
        hdr.addWidget(close_btn)
        pl.addLayout(hdr)
        pl.addSpacing(8)

        # ── Scrollbarer Inhalt ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll_content = QWidget()
        self._scroll_content.setStyleSheet("background: transparent;")
        self._cl = QVBoxLayout(self._scroll_content)
        self._cl.setContentsMargins(0, 0, 12, 0)
        self._cl.setSpacing(6)

        # Sektion: Stammdaten
        self._cl.addWidget(self._heading(texts.CONTACT_DETAIL_TAB_DATA))
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._edit_fn = QLineEdit()
        self._edit_fn.setPlaceholderText(texts.CONTACT_FIRST_NAME)
        form.addRow(texts.CONTACT_FIRST_NAME + ":", self._edit_fn)
        self._edit_ln = QLineEdit()
        self._edit_ln.setPlaceholderText(texts.CONTACT_LAST_NAME)
        form.addRow(texts.CONTACT_LAST_NAME + ":", self._edit_ln)
        self._edit_dob = QDateEdit()
        self._edit_dob.setCalendarPopup(True)
        self._edit_dob.setDisplayFormat("dd.MM.yyyy")
        form.addRow(texts.CONTACT_DATE_OF_BIRTH + ":", self._edit_dob)
        self._edit_pnr = QLineEdit()
        self._edit_pnr.setPlaceholderText(texts.CONTACT_PERSONNEL_NUMBER)
        form.addRow(texts.CONTACT_PERSONNEL_NUMBER + ":", self._edit_pnr)
        self._combo_type = QComboBox()
        self._combo_type.addItem(texts.CONTACT_NO_RESULTS_CREATE_PERSON, "person")
        self._combo_type.addItem(texts.CONTACT_NO_RESULTS_TEMP_NOTE, "temporary")
        form.addRow(texts.CONTACT_TYPE + ":", self._combo_type)
        self._cl.addLayout(form)

        # Sektion: Telefonnummern
        self._cl.addWidget(self._heading(texts.CONTACT_DETAIL_TAB_PHONES))
        self._phones_box = QVBoxLayout()
        self._phones_box.setSpacing(4)
        self._cl.addLayout(self._phones_box)
        self._cl.addWidget(self._action_btn(texts.CONTACT_PHONE_ADD, self._add_phone))

        # Sektion: E-Mails
        self._cl.addWidget(self._heading(texts.CONTACT_DETAIL_TAB_EMAILS))
        self._emails_box = QVBoxLayout()
        self._emails_box.setSpacing(4)
        self._cl.addLayout(self._emails_box)
        self._cl.addWidget(self._action_btn(texts.CONTACT_EMAIL_ADD, self._add_email))

        # Sektion: Weitere Felder
        self._cl.addWidget(self._heading(texts.CONTACT_DETAIL_TAB_CUSTOM))
        self._custom_box = QVBoxLayout()
        self._custom_box.setSpacing(4)
        self._cl.addLayout(self._custom_box)
        self._cl.addWidget(self._action_btn(texts.CONTACT_CUSTOM_FIELD_ADD, self._add_custom_field))

        # Sektion: Gespraechsjournal
        self._cl.addWidget(self._heading(texts.CONTACT_DETAIL_TAB_CALLS))
        self._calls_box = QVBoxLayout()
        self._calls_box.setSpacing(4)
        self._cl.addLayout(self._calls_box)
        self._cl.addWidget(self._action_btn(texts.CONTACT_CALL_NEW, self._open_call_dialog, primary=True))

        # Sektion: Notizen
        self._cl.addWidget(self._heading(texts.CONTACT_DETAIL_TAB_NOTES))
        self._notes_box = QVBoxLayout()
        self._notes_box.setSpacing(4)
        self._cl.addLayout(self._notes_box)
        self._cl.addWidget(self._action_btn(texts.CONTACT_NOTE_NEW, self._add_note, primary=True))

        self._cl.addStretch()
        scroll.setWidget(self._scroll_content)
        pl.addWidget(scroll, 1)

        # ── Speichern-Button (immer sichtbar) ──
        pl.addSpacing(8)
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        self._save_btn = QPushButton(texts.SAVE)
        self._save_btn.setStyleSheet(get_button_primary_style())
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setMinimumWidth(140)
        self._save_btn.setMinimumHeight(36)
        self._save_btn.clicked.connect(self._save_stammdaten)
        btn_bar.addWidget(self._save_btn)
        pl.addLayout(btn_bar)

        self._panels_row.addWidget(self._panel)

        # ── Rueckruf-Seitenpanel ──
        self._cb_panel = QFrame()
        self._cb_panel.setObjectName("cdCbPanel")
        self._cb_panel.setFixedWidth(260)
        self._cb_panel.setMaximumHeight(900)
        self._cb_panel.setStyleSheet(f"""
            QFrame#cdCbPanel {{
                background-color: {PRIMARY_0};
                border-radius: {RADIUS_MD};
                border: 1px solid #D32F2F;
            }}
        """)
        cb_layout = QVBoxLayout(self._cb_panel)
        cb_layout.setContentsMargins(16, 16, 16, 16)
        cb_layout.setSpacing(8)
        cb_title = QLabel(f"\U0001F514 {texts.CONTACT_CALLBACK_OPEN}")
        cb_title.setStyleSheet(
            f"font-family: {FONT_BODY}; font-size: 11pt; font-weight: {FONT_WEIGHT_BOLD}; "
            f"color: #D32F2F; background: transparent; border: none;"
        )
        cb_layout.addWidget(cb_title)
        self._cb_scroll = QScrollArea()
        self._cb_scroll.setWidgetResizable(True)
        self._cb_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cb_scroll.setStyleSheet("background: transparent; border: none;")
        self._cb_content = QWidget()
        self._cb_content.setStyleSheet("background: transparent;")
        self._cb_box = QVBoxLayout(self._cb_content)
        self._cb_box.setContentsMargins(0, 0, 0, 0)
        self._cb_box.setSpacing(6)
        self._cb_scroll.setWidget(self._cb_content)
        cb_layout.addWidget(self._cb_scroll)
        self._cb_panel.setVisible(False)

        self._panels_row.addWidget(self._cb_panel)

        outer_wrapper = QWidget()
        outer_wrapper.setStyleSheet("background: transparent;")
        outer_wrapper.setLayout(self._panels_row)
        outer.addWidget(outer_wrapper)

    # ── Helpers ──

    def _heading(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_SECTION_STYLE)
        return lbl

    def _action_btn(self, text: str, handler, primary: bool = False) -> QPushButton:
        btn = QPushButton(f"  +  {text}")
        btn.setStyleSheet(get_button_primary_style() if primary else get_button_secondary_style())
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMaximumWidth(300)
        btn.clicked.connect(handler)
        return btn

    def _row(self, text: str, on_delete=None) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ {_ROW_STYLE} }}")
        r = QHBoxLayout(f)
        r.setContentsMargins(4, 2, 4, 2)
        r.setSpacing(8)
        lbl = QLabel(text)
        lbl.setStyleSheet(_LBL_STYLE)
        lbl.setWordWrap(True)
        r.addWidget(lbl, 1)
        if on_delete:
            d = QPushButton("\u2715")
            d.setFixedSize(22, 22)
            d.setCursor(Qt.PointingHandCursor)
            d.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {PRIMARY_500}; font-size: 11pt; }} "
                f"QPushButton:hover {{ color: red; }}"
            )
            d.clicked.connect(on_delete)
            r.addWidget(d)
        return f

    def _clear_box(self, box):
        while box.count():
            item = box.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_box(item.layout())

    # ── Show / Close ──

    def show_contact(self, contact_id: int):
        self._cid = contact_id
        self._is_new = False
        self._worker = _LoadWorker(self._api, contact_id)
        self._worker.finished.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def show_new_contact(self, prefill_phone: str = '', prefill_name: str = '',
                         open_call_dialog_immediately: bool = False):
        self._open_call_dialog_pending = open_call_dialog_immediately
        fn, ln = '', ''
        if prefill_name:
            parts = prefill_name.strip().split(' ', 1)
            fn, ln = parts[0], parts[1] if len(parts) > 1 else ''
        try:
            d = {'first_name': fn or None, 'last_name': ln or None, 'contact_type': 'person'}
            if prefill_phone:
                d['phones'] = [{'phone_raw': prefill_phone, 'phone_type': 'mobile', 'is_preferred': 1}]
            res = self._api.create_contact(d)
            nid = res.get('id')
            if nid:
                self._is_new = True
                self.contact_updated.emit()
                self.show_contact(nid)
        except Exception as e:
            self._open_call_dialog_pending = False
            logger.error("Kontakt anlegen: %s", e)

    def _on_loaded(self, data: dict):
        self._data = data
        self._fill()
        self._fade_in()
        if self._open_call_dialog_pending:
            self._open_call_dialog_pending = False
            QTimer.singleShot(150, self._open_call_dialog)

    def _on_loaded_silent(self, data: dict):
        self._data = data
        self._fill()
        self.contact_updated.emit()

    def _on_error(self, msg: str):
        logger.error("Kontakt laden: %s", msg)

    def _fade_in(self):
        if self.parent():
            self.resize(self.parent().size())
            self.move(0, 0)
        self.setVisible(True)
        self.raise_()
        self.setFocus()
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def _close(self):
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(150)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._on_fade_out)
        self._anim.start()

    def _on_fade_out(self):
        self.setVisible(False)
        self.close_requested.emit()

    # ── Populate ──

    def _fill(self):
        d = self._data
        name = d.get('display_name') or f"{d.get('first_name', '')} {d.get('last_name', '')}".strip() or texts.CONTACT_NEW
        self._name_lbl.setText(name)
        self._fav_btn.setVisible(self._cid is not None)
        is_fav = d.get('is_favorite', False)
        self._fav_btn.setText("\u2605" if is_fav else "\u2606")
        c = ACCENT_500 if is_fav else PRIMARY_500
        self._fav_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY_100}; border: 1px solid {BORDER_DEFAULT}; "
            f"border-radius: 22px; font-size: 22pt; color: {c}; min-width: 44px; min-height: 44px; }} "
            f"QPushButton:hover {{ background-color: {PRIMARY_100}; color: {ACCENT_500}; border-color: {ACCENT_500}; }}"
        )

        self._edit_fn.setText(d.get('first_name') or '')
        self._edit_ln.setText(d.get('last_name') or '')
        dob = d.get('date_of_birth')
        if dob:
            p = str(dob)[:10].split('-')
            if len(p) == 3:
                self._edit_dob.setDate(QDate(int(p[0]), int(p[1]), int(p[2])))
        else:
            self._edit_dob.setDate(QDate(1900, 1, 1))
        self._edit_pnr.setText(str(d.get('personnel_number') or ''))
        idx = self._combo_type.findData(d.get('contact_type', 'person'))
        if idx >= 0:
            self._combo_type.setCurrentIndex(idx)

        self._fill_phones()
        self._fill_emails()
        self._fill_custom()
        self._fill_calls()
        self._fill_notes()
        self._fill_callbacks()

    def _fill_phones(self):
        self._clear_box(self._phones_box)
        for p in self._data.get('phones', []):
            raw = p.get('phone_raw', '')
            pt = p.get('phone_type', '')
            pref = "\u2605 " if p.get('is_preferred') else ""
            lbl = p.get('label', '')
            txt = f"{pref}{pt}: {raw}" + (f" ({lbl})" if lbl else "")
            pid = p.get('id')
            fn = (lambda chk=False, i=pid: self._del_phone(i)) if pid else None
            self._phones_box.addWidget(self._row(txt, on_delete=fn))

    def _fill_emails(self):
        self._clear_box(self._emails_box)
        for e in self._data.get('emails', []):
            addr = e.get('email', '')
            et = e.get('email_type', '')
            pref = "\u2605 " if e.get('is_preferred') else ""
            txt = f"{pref}{et}: {addr}"
            eid = e.get('id')
            fn = (lambda chk=False, i=eid: self._del_email(i)) if eid else None
            self._emails_box.addWidget(self._row(txt, on_delete=fn))

    def _fill_custom(self):
        self._clear_box(self._custom_box)
        for cv in self._data.get('custom_values', []):
            n, v = cv.get('field_name', ''), cv.get('field_value', '')
            cid = cv.get('id')
            fn = (lambda chk=False, i=cid: self._del_custom(i)) if cid else None
            self._custom_box.addWidget(self._row(f"{n}: {v}", on_delete=fn))

    def _fill_calls(self):
        self._clear_box(self._calls_box)
        calls = sorted(self._data.get('calls', []), key=lambda x: x.get('created_at', ''), reverse=True)
        for c in calls:
            dt = _format_datetime(c.get('created_at'))
            subj = c.get('subject', '') or ''
            by = c.get('created_by', '')
            d = "\u2190" if c.get('direction') == 'inbound' else "\u2192"
            cb_at = _format_datetime(c.get('callback_at')) if c.get('callback_needed') and c.get('status') == 'open' else ""
            cb = f" \U0001F514 {cb_at}" if cb_at else ""
            txt = f"{dt}  {d}  {subj}" + (f"  ({by})" if by else "") + cb
            note = c.get('note', '')
            if note:
                txt += f"\n{note[:120]}"
            self._calls_box.addWidget(self._row(txt))

    def _fill_notes(self):
        self._clear_box(self._notes_box)
        for n in self._data.get('notes', []):
            body = (n.get('content', '') or '')[:200]
            vis = n.get('visibility', 'shared')
            badge = "\U0001F512 " if vis == 'private' else ""
            by = n.get('created_by', '')
            dt = _format_datetime(n.get('created_at'))
            txt = f"{badge}{dt} ({by}): {body}"
            nid = n.get('id')
            fn = (lambda chk=False, i=nid: self._del_note(i)) if nid else None
            self._notes_box.addWidget(self._row(txt, on_delete=fn))

    def _fill_callbacks(self):
        self._clear_box(self._cb_box)
        open_cbs = [
            c for c in self._data.get('calls', [])
            if isinstance(c, dict) and c.get('callback_needed') and c.get('status') == 'open'
        ]
        self._cb_panel.setVisible(len(open_cbs) > 0)
        for c in sorted(open_cbs, key=lambda x: x.get('callback_at') or x.get('created_at') or '', reverse=False):
            subj = c.get('subject', '') or ''
            cb_at = _format_datetime(c.get('callback_at')) if c.get('callback_at') else _format_datetime(c.get('created_at'))
            by = c.get('created_by', '')
            txt = f"{cb_at}\n{subj}" + (f" ({by})" if by else "")

            f = QFrame()
            f.setStyleSheet(f"QFrame {{ {_ROW_STYLE} }}")
            r = QVBoxLayout(f)
            r.setContentsMargins(6, 4, 6, 4)
            r.setSpacing(4)
            lbl = QLabel(txt)
            lbl.setStyleSheet(
                f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_BODY}; "
                f"color: #D32F2F; border: none; background: transparent;"
            )
            lbl.setWordWrap(True)
            r.addWidget(lbl)
            cid = c.get('id')
            done_btn = QPushButton(f"\u2714 {texts.CONTACT_CALLBACK_MARK_DONE}")
            done_btn.setCursor(Qt.PointingHandCursor)
            done_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: 1px solid #4CAF50; "
                f"border-radius: 4px; padding: 4px 8px; color: #4CAF50; "
                f"font-family: {FONT_BODY}; font-size: {FONT_SIZE_CAPTION}; }} "
                f"QPushButton:hover {{ background: #4CAF50; color: white; }}"
            )
            done_btn.clicked.connect(lambda chk=False, i=cid: self._mark_done(i))
            r.addWidget(done_btn)
            self._cb_box.addWidget(f)
        self._cb_box.addStretch()

    def _mark_done(self, call_id: int):
        try:
            self._api.update_call(call_id, {'status': 'done', 'callback_needed': 0})
            self._reload()
            self.contact_updated.emit()
        except Exception as e:
            logger.error("Rueckruf erledigen: %s", e)

    # ── Actions ──

    def _save_stammdaten(self):
        d = {
            'first_name': self._edit_fn.text().strip(),
            'last_name': self._edit_ln.text().strip(),
            'personnel_number': self._edit_pnr.text().strip(),
            'contact_type': self._combo_type.currentData() or 'person',
        }
        dob = self._edit_dob.date()
        if dob.year() > 1900:
            d['date_of_birth'] = dob.toString('yyyy-MM-dd')
        try:
            if self._cid:
                self._api.update_contact(self._cid, d)
            else:
                ph = self._data.get('phones', [])
                if ph:
                    d['phones'] = [{'phone_raw': p['phone_raw'], 'phone_type': p.get('phone_type', 'other'),
                                    'is_preferred': p.get('is_preferred', 0)} for p in ph if p.get('phone_raw')]
                res = self._api.create_contact(d)
                nid = res.get('id')
                if nid:
                    self._cid = nid
                    self._is_new = False
            self.contact_updated.emit()
            if self._cid:
                self._reload()
        except Exception as e:
            logger.error("Speichern: %s", e)

    def _toggle_favorite(self):
        if not self._cid:
            return
        try:
            if self._data.get('is_favorite'):
                self._api.remove_favorite(self._cid)
                self._data['is_favorite'] = False
            else:
                self._api.set_favorite(self._cid)
                self._data['is_favorite'] = True
            self._fill()
            self.contact_updated.emit()
        except Exception:
            pass

    def _add_phone(self):
        if not self._cid:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(texts.CONTACT_PHONE_ADD)
        dlg.setMinimumWidth(380)
        f = QFormLayout(dlg)
        f.setSpacing(10)
        pe = QLineEdit()
        pe.setPlaceholderText("+49 171 1234567")
        f.addRow(texts.CONTACT_DETAIL_TAB_PHONES + ":", pe)
        tc = QComboBox()
        for l, v in [(texts.CONTACT_PHONE_TYPE_MOBILE, 'mobile'), (texts.CONTACT_PHONE_TYPE_LANDLINE, 'landline'),
                     (texts.CONTACT_PHONE_TYPE_BUSINESS, 'business_direct'), (texts.CONTACT_PHONE_TYPE_CENTRAL, 'central'),
                     (texts.CONTACT_PHONE_TYPE_WHATSAPP, 'whatsapp'), (texts.CONTACT_PHONE_TYPE_OTHER, 'other')]:
            tc.addItem(l, v)
        f.addRow(texts.CONTACT_TYPE + ":", tc)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.DialogCode.Accepted and pe.text().strip():
            try:
                self._api.add_phone(self._cid, {'phone_raw': pe.text().strip(), 'phone_type': tc.currentData()})
                self._reload()
                self.contact_updated.emit()
            except Exception as e:
                logger.error("Telefon: %s", e)

    def _del_phone(self, pid):
        try:
            self._api.delete_phone(pid)
            self._reload()
            self.contact_updated.emit()
        except Exception:
            pass

    def _add_email(self):
        if not self._cid:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(texts.CONTACT_EMAIL_ADD)
        dlg.setMinimumWidth(380)
        f = QFormLayout(dlg)
        f.setSpacing(10)
        ee = QLineEdit()
        ee.setPlaceholderText("name@beispiel.de")
        f.addRow(texts.CONTACT_DETAIL_TAB_EMAILS + ":", ee)
        tc = QComboBox()
        tc.addItem(texts.CONTACT_NOTE_VISIBILITY_PRIVATE, "personal")
        tc.addItem(texts.CONTACT_PHONE_TYPE_BUSINESS, "business")
        tc.addItem(texts.CONTACT_PHONE_TYPE_OTHER, "other")
        f.addRow(texts.CONTACT_TYPE + ":", tc)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.DialogCode.Accepted and ee.text().strip():
            try:
                self._api.add_email(self._cid, {'email': ee.text().strip(), 'email_type': tc.currentData()})
                self._reload()
                self.contact_updated.emit()
            except Exception as e:
                logger.error("E-Mail: %s", e)

    def _del_email(self, eid):
        try:
            self._api.delete_email(eid)
            self._reload()
            self.contact_updated.emit()
        except Exception:
            pass

    def _add_custom_field(self):
        if not self._cid:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(texts.CONTACT_CUSTOM_FIELD_ADD)
        dlg.setMinimumWidth(380)
        f = QFormLayout(dlg)
        f.setSpacing(10)
        ne = QLineEdit()
        ne.setPlaceholderText(texts.CONTACT_CUSTOM_FIELD_NAME)
        f.addRow(texts.CONTACT_CUSTOM_FIELD_NAME + ":", ne)
        ve = QLineEdit()
        ve.setPlaceholderText(texts.CONTACT_CUSTOM_FIELD_VALUE)
        f.addRow(texts.CONTACT_CUSTOM_FIELD_VALUE + ":", ve)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.DialogCode.Accepted and ne.text().strip():
            try:
                self._api.add_custom_value(self._cid, ne.text().strip(), ve.text().strip())
                self._reload()
                self.contact_updated.emit()
            except Exception as e:
                logger.error("Feld: %s", e)

    def _del_custom(self, cid):
        try:
            self._api.delete_custom_value(cid)
            self._reload()
            self.contact_updated.emit()
        except Exception:
            pass

    def _open_call_dialog(self):
        if not self._cid:
            return
        from ui.contact.contact_call_dialog import ContactCallDialog
        dlg = ContactCallDialog(self._api, self._cid, self)
        dlg.call_saved.connect(self._on_call_saved)
        dlg.exec()

    def _on_call_saved(self):
        self._reload()
        self.contact_updated.emit()

    def _add_note(self):
        if not self._cid:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(texts.CONTACT_NOTE_NEW)
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        ce = QTextEdit()
        ce.setPlaceholderText(texts.CONTACT_CALL_NOTE)
        ce.setMinimumHeight(100)
        lay.addWidget(ce)
        vc = QComboBox()
        vc.addItem(texts.CONTACT_NOTE_VISIBILITY_SHARED, "shared")
        vc.addItem(texts.CONTACT_NOTE_VISIBILITY_PRIVATE, "private")
        lay.addWidget(vc)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() == QDialog.DialogCode.Accepted and ce.toPlainText().strip():
            try:
                self._api.create_note(self._cid, {'content': ce.toPlainText().strip(), 'visibility': vc.currentData()})
                self._reload()
                self.contact_updated.emit()
            except Exception as e:
                logger.error("Notiz: %s", e)

    def _del_note(self, nid):
        try:
            self._api.delete_note(nid)
            self._reload()
            self.contact_updated.emit()
        except Exception:
            pass

    def _reload(self):
        if not self._cid:
            return
        self._worker = _LoadWorker(self._api, self._cid)
        self._worker.finished.connect(self._on_loaded_silent)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # ── Events ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 15, 30, 100))

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        in_main = self._panel.geometry().contains(event.pos())
        in_cb = self._cb_panel.isVisible() and self._cb_panel.geometry().contains(event.pos())
        if not in_main and not in_cb:
            self._close()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._close()
        else:
            super().keyPressEvent(event)
