"""
ACENCIA ATLAS - Workforce Employees View

Mitarbeiter-Uebersicht mit Arbeitgeber-Auswahl, Suche, Statusfilter,
Pagination und Sync-Funktion.
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QHeaderView,
    QFrame, QAbstractItemView, QSplitter, QScrollArea, QFormLayout,
)
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QFont, QColor

from workforce.api_client import WorkforceApiClient
from workforce.workers import SyncWorker
from ui.styles.tokens import (
    PRIMARY_500, PRIMARY_900, ACCENT_500, ACCENT_100,
    FONT_HEADLINE, FONT_BODY, FONT_SIZE_H2, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    BG_PRIMARY, BG_SECONDARY, BORDER_DEFAULT, RADIUS_MD, RADIUS_SM,
    SUCCESS, ERROR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED, TEXT_INVERSE,
    get_button_primary_style, get_button_secondary_style, get_input_style,
)
from i18n import de as texts

logger = logging.getLogger(__name__)

_STATUS_FILTERS = [
    ("all", None),
    ("active", "active"),
    ("inactive", "inactive"),
]


class EmployeesView(QWidget):
    """Mitarbeiter-Liste mit Sync, Suche, Filter und Pagination."""

    PAGE_SIZE = 50

    def __init__(self, wf_api: WorkforceApiClient, thread_pool: QThreadPool):
        super().__init__()
        self._wf_api = wf_api
        self._thread_pool = thread_pool
        self._toast_manager = None
        self._employers: list[dict] = []
        self._current_page = 1
        self._total_pages = 1
        self._syncing = False
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(400)
        self._search_timer.timeout.connect(self._load_employees)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(texts.WF_EMPLOYEES_TITLE)
        title.setStyleSheet(f"""
            font-family: {FONT_HEADLINE}; font-size: {FONT_SIZE_H2};
            color: {PRIMARY_900}; font-weight: bold;
        """)
        header.addWidget(title)
        header.addStretch()

        self._sync_btn = QPushButton(texts.WF_SYNC_BTN)
        self._sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 6px 16px; font-family: {FONT_BODY};
                background-color: {ACCENT_500}; color: white;
                border: none; border-radius: {RADIUS_MD}; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #e88a2d; }}
            QPushButton:disabled {{ background-color: {BG_SECONDARY}; color: {TEXT_DISABLED}; }}
        """)
        self._sync_btn.clicked.connect(self._on_sync)
        header.addWidget(self._sync_btn)

        layout.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        emp_label = QLabel(texts.WF_EMPLOYER_SELECT)
        emp_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: {FONT_BODY};")
        toolbar.addWidget(emp_label)

        self._employer_combo = QComboBox()
        self._employer_combo.setMinimumWidth(220)
        self._employer_combo.currentIndexChanged.connect(self._on_employer_changed)
        toolbar.addWidget(self._employer_combo)

        toolbar.addSpacing(16)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(texts.WF_EMPLOYEES_SEARCH_PLACEHOLDER)
        self._search_input.setMinimumWidth(200)
        self._search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self._search_input)

        status_label = QLabel(texts.WF_EMPLOYEES_STATUS_FILTER)
        status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: {FONT_BODY};")
        toolbar.addWidget(status_label)

        self._status_combo = QComboBox()
        self._status_combo.addItem(texts.WF_FILTER_ALL, "all")
        self._status_combo.addItem(texts.WF_FILTER_ACTIVE, "active")
        self._status_combo.addItem(texts.WF_FILTER_INACTIVE, "inactive")
        self._status_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._status_combo)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            texts.WF_COL_FIRST_NAME, texts.WF_COL_LAST_NAME,
            texts.WF_COL_EMAIL, texts.WF_COL_DEPARTMENT,
            texts.WF_COL_POSITION, texts.WF_COL_STATUS,
        ])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.currentCellChanged.connect(self._on_row_selected)
        table_layout.addWidget(self._table)

        pag = QHBoxLayout()
        pag.setSpacing(8)
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {PRIMARY_500}; font-size: {FONT_SIZE_CAPTION};")
        pag.addWidget(self._count_label)
        pag.addStretch()

        self._prev_btn = QPushButton(texts.WF_PAGE_PREV)
        self._prev_btn.setFixedWidth(80)
        self._prev_btn.setStyleSheet(get_button_secondary_style())
        self._prev_btn.clicked.connect(self._prev_page)
        pag.addWidget(self._prev_btn)

        self._page_label = QLabel("1 / 1")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setMinimumWidth(60)
        pag.addWidget(self._page_label)

        self._next_btn = QPushButton(texts.WF_PAGE_NEXT)
        self._next_btn.setFixedWidth(80)
        self._next_btn.setStyleSheet(get_button_secondary_style())
        self._next_btn.clicked.connect(self._next_page)
        pag.addWidget(self._next_btn)

        table_layout.addLayout(pag)
        self._splitter.addWidget(table_container)

        self._detail_panel = QScrollArea()
        self._detail_panel.setWidgetResizable(True)
        self._detail_panel.setMinimumWidth(280)
        self._detail_content = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_content)
        self._detail_layout.setContentsMargins(16, 16, 16, 16)
        self._detail_layout.setSpacing(8)
        self._detail_placeholder = QLabel(texts.WF_EMPLOYEES_SELECT_ROW)
        self._detail_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_placeholder.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_BODY};")
        self._detail_layout.addWidget(self._detail_placeholder)
        self._detail_layout.addStretch()
        self._detail_panel.setWidget(self._detail_content)
        self._splitter.addWidget(self._detail_panel)

        self._splitter.setSizes([700, 300])
        layout.addWidget(self._splitter)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet(f"color: {ACCENT_500}; font-size: {FONT_SIZE_CAPTION};")
        layout.addWidget(self._progress_label)

    # ── Data ───────────────────────────────────────────────────

    def refresh(self):
        self._load_employers()

    def _load_employers(self):
        try:
            self._employers = self._wf_api.get_employers()
            current_data = self._employer_combo.currentData()
            self._employer_combo.blockSignals(True)
            self._employer_combo.clear()
            if not self._employers:
                self._employer_combo.addItem(texts.WF_NO_EMPLOYERS, None)
            else:
                for emp in self._employers:
                    self._employer_combo.addItem(emp.get('name', '?'), emp.get('id'))
                if current_data:
                    idx = next(
                        (i for i, e in enumerate(self._employers) if e.get('id') == current_data), 0
                    )
                    self._employer_combo.setCurrentIndex(idx)
            self._employer_combo.blockSignals(False)
            self._load_employees()
        except Exception as e:
            logger.error(f"Arbeitgeber laden: {e}")

    def _on_employer_changed(self):
        self._current_page = 1
        self._load_employees()

    def _on_search_changed(self):
        self._current_page = 1
        self._search_timer.start()

    def _on_filter_changed(self):
        self._current_page = 1
        self._load_employees()

    def _load_employees(self):
        employer_id = self._employer_combo.currentData()
        if not employer_id:
            self._table.setRowCount(0)
            return

        status_val = self._status_combo.currentData()
        status_param = status_val if status_val != 'all' else None
        search = self._search_input.text().strip() or None

        try:
            result = self._wf_api.get_employees(
                employer_id, page=self._current_page,
                per_page=self.PAGE_SIZE, status=status_param, search=search,
            )
            employees = result.get('employees', [])
            pagination = result.get('pagination', {})
            self._total_pages = pagination.get('total_pages', 1)
            total = pagination.get('total', len(employees))

            self._populate_table(employees)
            self._count_label.setText(texts.WF_EMPLOYEES_COUNT.format(count=total))
            self._update_pagination()
        except Exception as e:
            logger.error(f"Mitarbeiter laden: {e}")
            if self._toast_manager:
                self._toast_manager.show_error(texts.WF_EMPLOYEES_LOAD_ERROR.format(error=str(e)))

    def _populate_table(self, employees: list):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            self._table.setItem(row, 0, QTableWidgetItem(emp.get('first_name', '')))
            self._table.setItem(row, 1, QTableWidgetItem(emp.get('last_name', '')))
            self._table.setItem(row, 2, QTableWidgetItem(emp.get('email', '')))
            self._table.setItem(row, 3, QTableWidgetItem(emp.get('department', '')))
            self._table.setItem(row, 4, QTableWidgetItem(emp.get('position', '')))

            status = emp.get('status', 'active')
            status_item = QTableWidgetItem(f"● {status}")
            color = SUCCESS if status == 'active' else TEXT_DISABLED
            status_item.setForeground(QColor(color))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 5, status_item)

            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, emp)

        self._table.setSortingEnabled(True)

    # ── Pagination ─────────────────────────────────────────────

    def _update_pagination(self):
        self._page_label.setText(f"{self._current_page} / {self._total_pages}")
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < self._total_pages)

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load_employees()

    def _next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_employees()

    # ── Detail Panel ───────────────────────────────────────────

    def _on_row_selected(self, row: int, _col: int, _prev_row: int, _prev_col: int):
        if row < 0 or row >= self._table.rowCount():
            return
        item = self._table.item(row, 0)
        if not item:
            return
        emp = item.data(Qt.ItemDataRole.UserRole)
        if emp:
            self._show_detail(emp)

    def _show_detail(self, emp: dict):
        while self._detail_layout.count():
            child = self._detail_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        name_lbl = QLabel(f"{emp.get('first_name', '')} {emp.get('last_name', '')}")
        name_lbl.setStyleSheet(f"""
            font-family: {FONT_HEADLINE}; font-size: 13pt;
            color: {PRIMARY_900}; font-weight: bold;
        """)
        self._detail_layout.addWidget(name_lbl)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER_DEFAULT};")
        self._detail_layout.addWidget(sep)

        fields = [
            (texts.WF_DETAIL_EMAIL, emp.get('email', '-')),
            (texts.WF_DETAIL_DEPARTMENT, emp.get('department', '-')),
            (texts.WF_DETAIL_POSITION, emp.get('position', '-')),
            (texts.WF_DETAIL_STATUS, emp.get('status', '-')),
            (texts.WF_DETAIL_PERSON_ID, emp.get('person_id', '-')),
            (texts.WF_DETAIL_ENTRY_DATE, emp.get('entry_date', '-')),
            (texts.WF_DETAIL_EXIT_DATE, emp.get('exit_date', '-')),
        ]
        for label_text, value in fields:
            row_widget = QWidget()
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 4, 0, 4)
            row_layout.setSpacing(2)

            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION};")
            row_layout.addWidget(lbl)

            val = QLabel(str(value) if value else '-')
            val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_BODY};")
            val.setWordWrap(True)
            row_layout.addWidget(val)

            self._detail_layout.addWidget(row_widget)

        self._detail_layout.addStretch()

    # ── Sync ───────────────────────────────────────────────────

    def _on_sync(self):
        employer_id = self._employer_combo.currentData()
        if not employer_id or self._syncing:
            return

        self._syncing = True
        self._sync_btn.setEnabled(False)
        self._progress_label.setText(texts.WF_SYNC_RUNNING)

        worker = SyncWorker(self._wf_api, employer_id)
        worker.signals.finished.connect(self._on_sync_done)
        worker.signals.error.connect(self._on_sync_error)
        worker.signals.progress.connect(self._on_sync_progress)
        self._thread_pool.start(worker)

    def _on_sync_progress(self, msg: str):
        self._progress_label.setText(msg)

    def _on_sync_done(self, result: dict):
        self._syncing = False
        self._sync_btn.setEnabled(True)
        self._progress_label.setText("")
        synced = result.get('synced_count', 0)
        if self._toast_manager:
            self._toast_manager.show_success(
                texts.WF_SYNC_SUCCESS.format(count=synced)
            )
        self._load_employees()

    def _on_sync_error(self, error: str):
        self._syncing = False
        self._sync_btn.setEnabled(True)
        self._progress_label.setText("")
        logger.error(f"Sync fehlgeschlagen: {error}")
        if self._toast_manager:
            self._toast_manager.show_error(texts.WF_SYNC_ERROR.format(error=error))
