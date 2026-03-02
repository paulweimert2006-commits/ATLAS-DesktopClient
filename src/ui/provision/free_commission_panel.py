"""
Panel: Freie Provisionen / Sonderzahlungen.

Ermoeglicht dem GF das Erfassen, Bearbeiten und Loeschen von
Sonderzahlungen mit freier Verteilung an Berater.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QAbstractItemView,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from typing import List, Optional

from domain.provision.entities import FreeCommission
from ui.styles.tokens import (
    PRIMARY_100, PRIMARY_500, PRIMARY_900, ACCENT_500,
    BG_PRIMARY, BG_SECONDARY, BORDER_DEFAULT,
    SUCCESS, ERROR,
    FONT_BODY, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    get_provision_table_style,
)
from ui.provision.widgets import (
    SectionHeader, ProvisionLoadingOverlay,
    format_eur, get_secondary_button_style,
)
from i18n import de as texts
import logging

logger = logging.getLogger(__name__)


class FreeCommissionPanel(QWidget):
    """Freie Provisionen / Sonderzahlungen - Uebersicht und CRUD.

    Implementiert IFreeCommissionView fuer den FreeCommissionPresenter.
    """

    navigate_to_panel = Signal(int)
    data_changed = Signal()

    def __init__(self):
        super().__init__()
        self._presenter = None
        self._toast_manager = None
        self._items: List[FreeCommission] = []
        self._setup_ui()

    def set_presenter(self, presenter) -> None:
        self._presenter = presenter
        presenter.set_view(self)
        QTimer.singleShot(100, self._load_data)

    # ── IFreeCommissionView ──

    def show_free_commissions(self, items: List[FreeCommission]) -> None:
        self._items = items
        self._populate_table()

    def show_loading(self, loading: bool) -> None:
        self._loading_overlay.setVisible(loading)
        if loading:
            self._loading_overlay.raise_()

    def show_error(self, message: str) -> None:
        if self._toast_manager:
            self._toast_manager.show_error(message)

    def show_success(self, message: str) -> None:
        if self._toast_manager:
            self._toast_manager.show_success(message)
        self.data_changed.emit()

    def refresh(self) -> None:
        self._load_data()

    # ── UI-Setup ──

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = SectionHeader(texts.PM_FREE_PANEL_TITLE, texts.PM_FREE_PANEL_DESC)
        self._create_btn = QPushButton(f"  +  {texts.PM_FREE_BTN_CREATE}")
        self._create_btn.setCursor(Qt.PointingHandCursor)
        self._create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_500};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_BODY};
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #1a6fb5; }}
            QPushButton:pressed {{ background-color: #155a93; }}
        """)
        self._create_btn.clicked.connect(self._on_create)
        header._action_area.addWidget(self._create_btn)
        layout.addWidget(header)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(get_provision_table_style())

        cols = [
            texts.PM_FREE_COL_DATUM,
            texts.PM_FREE_COL_BETRAG,
            texts.PM_FREE_COL_BESCHREIBUNG,
            texts.PM_FREE_COL_KOSTENSTELLE,
            texts.PM_FREE_COL_VERTEILUNG,
            texts.PM_FREE_COL_ERSTELLT_VON,
            texts.PM_FREE_COL_AKTIONEN,
        ]
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.Fixed)
        hh.resizeSection(6, 240)

        layout.addWidget(self._table)

        self._empty_label = QLabel(texts.PM_FREE_EMPTY)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {PRIMARY_500}; font-size: 12pt; font-family: {FONT_BODY}; padding: 40px;"
        )
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        self._loading_overlay = ProvisionLoadingOverlay(self)
        self._loading_overlay.setVisible(False)

    def _populate_table(self):
        self._table.setRowCount(0)
        has_data = bool(self._items)
        self._table.setVisible(has_data)
        self._empty_label.setVisible(not has_data)
        if not has_data:
            return

        self._table.setRowCount(len(self._items))
        for row, fc in enumerate(self._items):
            datum_str = fc.datum[:10] if fc.datum else ''
            self._table.setItem(row, 0, QTableWidgetItem(datum_str))

            betrag_item = QTableWidgetItem(format_eur(fc.gesamtbetrag))
            betrag_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 1, betrag_item)

            self._table.setItem(row, 2, QTableWidgetItem(fc.beschreibung))
            self._table.setItem(row, 3, QTableWidgetItem(fc.kostenstelle or ''))
            self._table.setItem(row, 4, QTableWidgetItem(fc.verteilung_text or ''))
            self._table.setItem(row, 5, QTableWidgetItem(fc.created_by_name or ''))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            if fc.can_edit:
                edit_btn = QPushButton(texts.PM_FREE_DIALOG_TITLE_EDIT.split()[0])
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setStyleSheet(get_secondary_button_style())
                edit_btn.setFixedHeight(28)
                edit_btn.clicked.connect(lambda checked, r=row: self._on_edit(r))
                actions_layout.addWidget(edit_btn)

                del_btn = QPushButton("\u2716")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setToolTip(texts.PM_FREE_DELETE_CONFIRM.format(beschreibung=''))
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent; color: {ERROR};
                        border: 1px solid {ERROR}; border-radius: 4px;
                        padding: 2px 8px; font-size: {FONT_SIZE_CAPTION};
                    }}
                    QPushButton:hover {{ background-color: #fde8e8; }}
                """)
                del_btn.setFixedHeight(28)
                del_btn.clicked.connect(lambda checked, r=row: self._on_delete(r))
                actions_layout.addWidget(del_btn)
            else:
                lock_lbl = QLabel("\U0001F512")
                lock_lbl.setToolTip(texts.PM_FREE_EDIT_LOCKED)
                actions_layout.addWidget(lock_lbl)

            actions_layout.addStretch()
            self._table.setCellWidget(row, 6, actions_widget)

        self._table.resizeRowsToContents()

    # ── Actions ──

    def _load_data(self):
        if self._presenter:
            self._presenter.load_free_commissions()

    def _on_create(self):
        from ui.provision.free_commission_dialog import FreeCommissionDialog
        employees = self._presenter.get_employees() if self._presenter else []
        dlg = FreeCommissionDialog(employees, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if self._presenter:
                self._presenter.save_free_commission(data)

    def _on_edit(self, row: int):
        if row < 0 or row >= len(self._items):
            return
        fc = self._items[row]
        if not fc.can_edit:
            if self._toast_manager:
                self._toast_manager.show_error(texts.PM_FREE_EDIT_LOCKED)
            return

        from ui.provision.free_commission_dialog import FreeCommissionDialog
        employees = self._presenter.get_employees() if self._presenter else []
        detail = {}
        if self._presenter:
            detail = self._presenter._repo.get_free_commission(fc.id)
        if detail:
            fc_detail = FreeCommission.from_dict(detail)
        else:
            fc_detail = fc

        dlg = FreeCommissionDialog(employees, fc=fc_detail, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if self._presenter:
                self._presenter.save_free_commission(data, fc_id=fc.id)

    def _on_delete(self, row: int):
        if row < 0 or row >= len(self._items):
            return
        fc = self._items[row]
        if not fc.can_edit:
            if self._toast_manager:
                self._toast_manager.show_error(texts.PM_FREE_DELETE_LOCKED)
            return

        msg = texts.PM_FREE_DELETE_CONFIRM.format(beschreibung=fc.beschreibung)
        reply = QMessageBox.question(self, texts.PM_FREE_PANEL_TITLE, msg,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes and self._presenter:
            self._presenter.delete_free_commission(fc.id)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._loading_overlay.setGeometry(self.rect())
