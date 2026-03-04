"""
Workforce Stats View - Statistik-Panel mit Standard- und Langzeit-Modus.

Zeigt Mitarbeiterstatistiken pro Arbeitgeber an. Standard-Modus: Status,
Geschlecht, Abteilung, Betriebszugehoerigkeit, Fluktuation, Trends.
Langzeit-Modus: Ein-/Austritte pro Jahr, durchschnittliche Beschaeftigungsdauer.
"""

import logging
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QFrame, QProgressBar, QScrollArea, QFileDialog,
)
from PySide6.QtCore import Qt, QThreadPool

from workforce.api_client import WorkforceApiClient
from workforce.workers import StatsWorker
from ui.styles.tokens import (
    PRIMARY_500, PRIMARY_900, ACCENT_500, FONT_BODY,
    FONT_SIZE_BODY, FONT_SIZE_CAPTION, FONT_SIZE_H2,
    BG_PRIMARY, BG_SECONDARY, BORDER_DEFAULT, RADIUS_MD,
    get_button_primary_style, get_button_secondary_style, get_table_style,
)
from i18n import de as texts

logger = logging.getLogger(__name__)


class StatsView(QWidget):
    """Statistik-Panel fuer das Workforce-Modul."""

    def __init__(self, wf_api: WorkforceApiClient, thread_pool: QThreadPool):
        super().__init__()
        self._wf_api = wf_api
        self._thread_pool = thread_pool
        self._toast_manager = None
        self._employers: list[dict] = []
        self._current_stats: dict = {}
        self._loading = False

        self._setup_ui()
        self._load_employers()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(texts.WF_STATS_TITLE)
        title.setStyleSheet(f"""
            font-family: {FONT_BODY}; font-size: {FONT_SIZE_H2};
            color: {PRIMARY_900}; font-weight: 600;
        """)
        header.addWidget(title)
        header.addStretch()

        self._export_btn = QPushButton(texts.WF_STATS_EXPORT_TXT)
        self._export_btn.setStyleSheet(get_button_secondary_style())
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_stats)
        header.addWidget(self._export_btn)
        root.addLayout(header)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        emp_label = QLabel(texts.WF_STATS_EMPLOYER)
        emp_label.setStyleSheet(f"color: {PRIMARY_900}; font-family: {FONT_BODY};")
        controls.addWidget(emp_label)

        self._employer_combo = QComboBox()
        self._employer_combo.setMinimumWidth(250)
        self._employer_combo.currentIndexChanged.connect(self._on_employer_changed)
        controls.addWidget(self._employer_combo)

        controls.addSpacing(24)

        mode_label = QLabel(texts.WF_STATS_MODE)
        mode_label.setStyleSheet(f"color: {PRIMARY_900}; font-family: {FONT_BODY};")
        controls.addWidget(mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem(texts.WF_STATS_STANDARD, "standard")
        self._mode_combo.addItem(texts.WF_STATS_LONGTERM, "longterm")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        controls.addWidget(self._mode_combo)

        controls.addStretch()

        self._calc_btn = QPushButton(texts.WF_STATS_CALCULATE)
        self._calc_btn.setStyleSheet(get_button_primary_style())
        self._calc_btn.setCursor(Qt.PointingHandCursor)
        self._calc_btn.clicked.connect(self._calculate_stats)
        controls.addWidget(self._calc_btn)
        root.addLayout(controls)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._progress_label = QLabel()
        self._progress_label.setStyleSheet(
            f"color: {PRIMARY_500}; font-size: {FONT_SIZE_CAPTION}; font-family: {FONT_BODY};"
        )
        self._progress_label.setVisible(False)
        root.addWidget(self._progress_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(16)
        scroll.setWidget(self._results_widget)
        root.addWidget(scroll, 1)

        placeholder = QLabel(texts.WF_STATS_PLACEHOLDER)
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(
            f"color: {PRIMARY_500}; font-size: {FONT_SIZE_BODY}; font-family: {FONT_BODY}; padding: 48px;"
        )
        self._results_layout.addWidget(placeholder)

    def _load_employers(self):
        try:
            self._employers = self._wf_api.get_employers()
            self._employer_combo.clear()
            for emp in self._employers:
                self._employer_combo.addItem(emp.get('name', '?'), emp.get('id'))
        except Exception as e:
            logger.error(f"Fehler beim Laden der Arbeitgeber: {e}")

    def _on_employer_changed(self, _index: int):
        self._clear_results()

    def _on_mode_changed(self, _index: int):
        self._clear_results()

    def _clear_results(self):
        self._current_stats = {}
        self._export_btn.setEnabled(False)
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _calculate_stats(self):
        if self._loading:
            return
        employer_id = self._employer_combo.currentData()
        if not employer_id:
            return
        stats_type = self._mode_combo.currentData()

        self._loading = True
        self._calc_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_label.setText(texts.WF_STATS_LOADING)
        self._clear_results()

        worker = StatsWorker(self._wf_api, employer_id, stats_type)
        worker.signals.finished.connect(self._on_stats_done)
        worker.signals.error.connect(self._on_stats_error)
        worker.signals.progress.connect(self._on_progress)
        self._thread_pool.start(worker)

    def _on_progress(self, msg: str):
        self._progress_label.setText(msg)

    def _on_stats_done(self, result: dict):
        self._loading = False
        self._calc_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._current_stats = result
        self._export_btn.setEnabled(True)

        stats_type = result.get('stats_type', 'standard')
        stats = result.get('stats', {})

        if not stats:
            lbl = QLabel(texts.WF_STATS_NO_DATA)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {PRIMARY_500}; padding: 32px;")
            self._results_layout.addWidget(lbl)
            return

        if stats_type == 'standard':
            self._render_standard(stats)
        else:
            self._render_longterm(stats)

    def _on_stats_error(self, error: str):
        self._loading = False
        self._calc_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        logger.error(f"Statistik-Fehler: {error}")
        if self._toast_manager:
            self._toast_manager.show_error(f"{texts.WF_STATS_ERROR}: {error}")

    def _make_section(self, title_text: str) -> QVBoxLayout:
        section = QVBoxLayout()
        section.setSpacing(8)
        lbl = QLabel(title_text)
        lbl.setStyleSheet(f"""
            font-family: {FONT_BODY}; font-size: 11pt; color: {PRIMARY_900};
            font-weight: 600; padding-bottom: 4px;
            border-bottom: 2px solid {ACCENT_500};
        """)
        section.addWidget(lbl)
        return section

    def _make_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD};
                padding: 12px 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)
        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(f"font-size: 16pt; font-weight: 700; color: {PRIMARY_900};")
        val_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(val_lbl)
        cap_lbl = QLabel(label)
        cap_lbl.setStyleSheet(f"font-size: {FONT_SIZE_CAPTION}; color: {PRIMARY_500};")
        cap_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(cap_lbl)
        return card

    def _make_kv_table(self, data: dict, headers: tuple[str, str]) -> QTableWidget:
        table = QTableWidget(len(data), 2)
        table.setHorizontalHeaderLabels(list(headers))
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setMaximumHeight(max(150, 36 * (len(data) + 1)))
        for row, (k, v) in enumerate(data.items()):
            table.setItem(row, 0, QTableWidgetItem(str(k)))
            table.setItem(row, 1, QTableWidgetItem(str(v)))
        return table

    def _render_standard(self, stats: dict):
        sc = stats.get('status_counts', {})
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.addWidget(self._make_card(texts.WF_STATS_TOTAL, str(sc.get('total', 0))))
        cards_row.addWidget(self._make_card(texts.WF_STATS_ACTIVE, str(sc.get('active', 0))))
        cards_row.addWidget(self._make_card(texts.WF_STATS_INACTIVE, str(sc.get('inactive', 0))))

        avgs = stats.get('averages', {})
        cards_row.addWidget(self._make_card(
            texts.WF_STATS_AVG_TENURE,
            f"{avgs.get('tenure_years', 0)} {texts.WF_STATS_YEARS}"
        ))
        cards_row.addWidget(self._make_card(
            texts.WF_STATS_AVG_HOURS,
            str(stats.get('average_weekly_hours', 0))
        ))
        turnover = stats.get('turnover', {})
        cards_row.addWidget(self._make_card(
            texts.WF_STATS_TURNOVER,
            f"{turnover.get('rate_percent', 0)} %"
        ))
        cards_w = QWidget()
        cards_w.setLayout(cards_row)
        self._results_layout.addWidget(cards_w)

        gd = stats.get('gender_distribution', {})
        if gd.get('labels'):
            sec = self._make_section(texts.WF_STATS_GENDER)
            gender_data = dict(zip(gd['labels'], gd['data']))
            sec.addWidget(self._make_kv_table(
                gender_data, (texts.WF_STATS_GENDER, texts.WF_STATS_COUNT)
            ))
            w = QWidget()
            w.setLayout(sec)
            self._results_layout.addWidget(w)

        dd = stats.get('department_distribution', {})
        if dd.get('labels'):
            sec = self._make_section(texts.WF_STATS_DEPARTMENTS)
            dept_data = dict(zip(dd['labels'], dd['data']))
            sec.addWidget(self._make_kv_table(
                dept_data, (texts.WF_STATS_DEPARTMENT, texts.WF_STATS_COUNT)
            ))
            w = QWidget()
            w.setLayout(sec)
            self._results_layout.addWidget(w)

        etd = stats.get('employment_type_distribution', {})
        if etd.get('labels'):
            sec = self._make_section(texts.WF_STATS_EMPLOYMENT_TYPES)
            et_data = dict(zip(etd['labels'], etd['data']))
            sec.addWidget(self._make_kv_table(
                et_data, (texts.WF_STATS_TYPE, texts.WF_STATS_COUNT)
            ))
            w = QWidget()
            w.setLayout(sec)
            self._results_layout.addWidget(w)

        jlt = stats.get('join_leave_trends', {})
        if jlt.get('labels'):
            sec = self._make_section(texts.WF_STATS_TRENDS)
            trends_table = QTableWidget(len(jlt['labels']), 3)
            trends_table.setHorizontalHeaderLabels([
                texts.WF_STATS_MONTH, texts.WF_STATS_JOINS, texts.WF_STATS_LEAVES
            ])
            trends_table.horizontalHeader().setStretchLastSection(True)
            trends_table.verticalHeader().setVisible(False)
            trends_table.setEditTriggers(QTableWidget.NoEditTriggers)
            trends_table.setAlternatingRowColors(True)
            trends_table.setMaximumHeight(max(200, 36 * (len(jlt['labels']) + 1)))
            for row, label in enumerate(jlt['labels']):
                trends_table.setItem(row, 0, QTableWidgetItem(label))
                trends_table.setItem(row, 1, QTableWidgetItem(str(jlt['joins'][row])))
                trends_table.setItem(row, 2, QTableWidgetItem(str(jlt['leaves'][row])))
            sec.addWidget(trends_table)
            w = QWidget()
            w.setLayout(sec)
            self._results_layout.addWidget(w)

        self._results_layout.addStretch()

    def _render_longterm(self, stats: dict):
        ee = stats.get('entries_exits', {})
        ad = stats.get('average_duration', {})

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.addWidget(self._make_card(
            texts.WF_STATS_AVG_DURATION,
            f"{ad.get('years', 0)} {texts.WF_STATS_YEARS}"
        ))
        cards_row.addWidget(self._make_card(
            texts.WF_STATS_EMPLOYEES_INCLUDED,
            str(ad.get('total_employees_included', 0))
        ))
        cards_row.addStretch()
        cards_w = QWidget()
        cards_w.setLayout(cards_row)
        self._results_layout.addWidget(cards_w)

        if ee.get('labels'):
            sec = self._make_section(texts.WF_STATS_ENTRIES_EXITS)
            ee_table = QTableWidget(len(ee['labels']), 3)
            ee_table.setHorizontalHeaderLabels([
                texts.WF_STATS_YEAR, texts.WF_STATS_ENTRIES, texts.WF_STATS_EXITS
            ])
            ee_table.horizontalHeader().setStretchLastSection(True)
            ee_table.verticalHeader().setVisible(False)
            ee_table.setEditTriggers(QTableWidget.NoEditTriggers)
            ee_table.setAlternatingRowColors(True)
            for row, label in enumerate(ee['labels']):
                ee_table.setItem(row, 0, QTableWidgetItem(str(label)))
                ee_table.setItem(row, 1, QTableWidgetItem(str(ee['entries'][row])))
                ee_table.setItem(row, 2, QTableWidgetItem(str(ee['exits'][row])))
            sec.addWidget(ee_table)
            w = QWidget()
            w.setLayout(sec)
            self._results_layout.addWidget(w)

        self._results_layout.addStretch()

    def _export_stats(self):
        if not self._current_stats:
            return
        stats = self._current_stats.get('stats', {})
        stats_type = self._current_stats.get('stats_type', 'standard')
        employer_name = self._employer_combo.currentText()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"workforce_stats_{stats_type}_{timestamp}.txt"

        path, _ = QFileDialog.getSaveFileName(
            self, texts.WF_STATS_EXPORT_TITLE, default_name, "Text (*.txt)"
        )
        if not path:
            return

        try:
            lines = [
                f"{texts.WF_STATS_TITLE} - {employer_name}",
                f"{texts.WF_STATS_MODE}: {texts.WF_STATS_STANDARD if stats_type == 'standard' else texts.WF_STATS_LONGTERM}",
                f"{texts.WF_STATS_EXPORT_DATE}: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                "=" * 60, "",
            ]

            if stats_type == 'standard':
                sc = stats.get('status_counts', {})
                lines.append(f"{texts.WF_STATS_TOTAL}: {sc.get('total', 0)}")
                lines.append(f"{texts.WF_STATS_ACTIVE}: {sc.get('active', 0)}")
                lines.append(f"{texts.WF_STATS_INACTIVE}: {sc.get('inactive', 0)}")
                avgs = stats.get('averages', {})
                lines.append(f"{texts.WF_STATS_AVG_TENURE}: {avgs.get('tenure_years', 0)} {texts.WF_STATS_YEARS}")
                lines.append(f"{texts.WF_STATS_AVG_HOURS}: {stats.get('average_weekly_hours', 0)}")
                to = stats.get('turnover', {})
                lines.append(f"{texts.WF_STATS_TURNOVER}: {to.get('rate_percent', 0)} %")
                lines.append("")

                gd = stats.get('gender_distribution', {})
                if gd.get('labels'):
                    lines.append(f"--- {texts.WF_STATS_GENDER} ---")
                    for lbl, val in zip(gd['labels'], gd['data']):
                        lines.append(f"  {lbl}: {val}")
                    lines.append("")

                dd = stats.get('department_distribution', {})
                if dd.get('labels'):
                    lines.append(f"--- {texts.WF_STATS_DEPARTMENTS} ---")
                    for lbl, val in zip(dd['labels'], dd['data']):
                        lines.append(f"  {lbl}: {val}")
                    lines.append("")

                jlt = stats.get('join_leave_trends', {})
                if jlt.get('labels'):
                    lines.append(f"--- {texts.WF_STATS_TRENDS} ---")
                    for i, lbl in enumerate(jlt['labels']):
                        lines.append(f"  {lbl}: +{jlt['joins'][i]} / -{jlt['leaves'][i]}")
            else:
                ad = stats.get('average_duration', {})
                lines.append(f"{texts.WF_STATS_AVG_DURATION}: {ad.get('years', 0)} {texts.WF_STATS_YEARS}")
                lines.append(f"{texts.WF_STATS_EMPLOYEES_INCLUDED}: {ad.get('total_employees_included', 0)}")
                lines.append("")
                ee = stats.get('entries_exits', {})
                if ee.get('labels'):
                    lines.append(f"--- {texts.WF_STATS_ENTRIES_EXITS} ---")
                    for i, lbl in enumerate(ee['labels']):
                        lines.append(f"  {lbl}: +{ee['entries'][i]} / -{ee['exits'][i]}")

            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            if self._toast_manager:
                self._toast_manager.show_success(texts.WF_STATS_EXPORTED)
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            if self._toast_manager:
                self._toast_manager.show_error(f"{texts.WF_STATS_EXPORT_ERROR}: {e}")

    def refresh(self):
        self._load_employers()
        self._clear_results()
