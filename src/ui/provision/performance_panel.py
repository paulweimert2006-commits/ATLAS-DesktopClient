"""
Erfolgsauswertung-Panel (Performance) mit 3 rollenbasierten Tabs.

Tab 1 – Mitarbeiter: eigene Provision, YTD, Stornoquoten
Tab 2 – ACENCIA: AG-Anteil, Ueberschuss (Eingang - Berater - TL)
Tab 3 – Fuehrungskraft: Team-Umsatz, Team-AG-Anteil, Berater-Tabelle
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QTabWidget, QComboBox, QTableView,
    QHeaderView, QFrame, QScrollArea, QSizePolicy, QDateEdit,
)
from PySide6.QtCore import Qt, Signal, QDate
from typing import Optional
from datetime import date
import calendar
import logging

from domain.provision.entities import (
    PerformanceData, PerformanceMitarbeiter,
    PerformanceAcencia, PerformanceFuehrungskraft,
)
from ui.styles.tokens import (
    PRIMARY_0, PRIMARY_100, PRIMARY_500, PRIMARY_900,
    ACCENT_500, BG_TERTIARY, BORDER_DEFAULT,
    SUCCESS, ERROR, WARNING,
    FONT_BODY, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    get_provision_table_style,
)
from ui.provision.widgets import KpiCard, SectionHeader, format_eur, get_combo_style
from ui.provision.models import FuehrungskraftModel
from i18n import de as texts

logger = logging.getLogger(__name__)


class PerformancePanel(QWidget):
    """Erfolgsauswertung mit 3 rollenbasierten Ebenen."""

    navigate_to_panel = Signal(int)
    data_changed = Signal()

    def __init__(self):
        super().__init__()
        self._presenter = None
        self._toast_manager = None
        self._data: Optional[PerformanceData] = None
        self._setup_ui()

    def set_presenter(self, presenter) -> None:
        self._presenter = presenter
        presenter.set_view(self)
        von, bis = self._get_date_range()
        self._presenter.load_performance(von=von, bis=bis)

    # ── IPerformanceView ──

    def show_performance(self, data: PerformanceData) -> None:
        self._data = data
        self._status_label.setText('')
        self._configure_tabs(data)

    def show_loading(self, loading: bool) -> None:
        if loading:
            self._status_label.setText(texts.PM_PERF_LOADING)
        else:
            self._status_label.setText('')

    def show_error(self, message: str) -> None:
        self._status_label.setText(texts.PM_PERF_ERROR)

    def refresh(self) -> None:
        if self._presenter:
            von, bis = self._get_date_range()
            self._presenter.load_performance(von=von, bis=bis)

    # ── UI Setup ──

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)

        header = SectionHeader(texts.PM_PERF_PANEL_TITLE, texts.PM_PERF_PANEL_DESC)
        root.addWidget(header)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        ctrl_row.addWidget(QLabel(texts.PROVISION_DASH_MONAT))
        self._month_combo = QComboBox()
        self._month_combo.setStyleSheet(get_combo_style())
        self._month_combo.setMinimumWidth(160)
        self._populate_month_combo()
        self._month_combo.currentIndexChanged.connect(self._on_month_changed)
        ctrl_row.addWidget(self._month_combo)

        ctrl_row.addStretch()
        self._status_label = QLabel('')
        self._status_label.setStyleSheet(
            f"color: {PRIMARY_500}; font-family: {FONT_BODY}; font-size: {FONT_SIZE_CAPTION};"
        )
        ctrl_row.addWidget(self._status_label)
        root.addLayout(ctrl_row)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_DEFAULT};
                border-radius: 6px;
                background: {PRIMARY_0};
            }}
            QTabBar::tab {{
                background: {BG_TERTIARY};
                border: 1px solid {BORDER_DEFAULT};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 20px;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_BODY};
                color: {PRIMARY_500};
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {PRIMARY_0};
                color: {PRIMARY_900};
                font-weight: 600;
            }}
        """)

        self._tab_ma = self._build_mitarbeiter_tab()
        self._tab_ac = self._build_acencia_tab()
        self._tab_fk = self._build_fuehrungskraft_tab()

        root.addWidget(self._tabs, 1)

    def _populate_month_combo(self):
        today = date.today()
        for i in range(12):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            label = f"{m:02d}/{y}"
            self._month_combo.addItem(label, f"{y}-{m:02d}")
        self._month_combo.setCurrentIndex(0)

    def _get_date_range(self):
        monat = self._month_combo.currentData()
        if not monat:
            monat = date.today().strftime('%Y-%m')
        y, m = monat.split('-')
        y, m = int(y), int(m)
        von = f"{y}-{m:02d}-01"
        last_day = calendar.monthrange(y, m)[1]
        bis = f"{y}-{m:02d}-{last_day:02d}"
        return von, bis

    def _on_month_changed(self):
        self.refresh()

    # ── Tabs aufbauen ──

    def _configure_tabs(self, data: PerformanceData):
        self._tabs.clear()
        if 'mitarbeiter' in data.levels and data.mitarbeiter:
            self._tabs.addTab(self._tab_ma, texts.PM_PERF_TAB_MITARBEITER)
            self._render_mitarbeiter(data.mitarbeiter)
        if 'acencia' in data.levels and data.acencia:
            self._tabs.addTab(self._tab_ac, texts.PM_PERF_TAB_ACENCIA)
            self._render_acencia(data.acencia)
        if 'fuehrungskraft' in data.levels and data.fuehrungskraft:
            self._tabs.addTab(self._tab_fk, texts.PM_PERF_TAB_FUEHRUNGSKRAFT)
            self._render_fuehrungskraft(data.fuehrungskraft)
        if not data.levels:
            self._status_label.setText(texts.PM_PERF_NO_EMPLOYEE)

    # ── Tab 1: Mitarbeiter ──

    def _build_mitarbeiter_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(12)

        self._ma_provision_monat = KpiCard(texts.PM_PERF_PROVISION_MONAT, accent_color=SUCCESS)
        self._ma_provision_ytd = KpiCard(texts.PM_PERF_PROVISION_YTD, accent_color=SUCCESS)
        self._ma_rueck_monat = KpiCard(texts.PM_PERF_RUECKBELASTUNG_MONAT, accent_color=ERROR)
        self._ma_rueck_ytd = KpiCard(texts.PM_PERF_RUECKBELASTUNG_YTD, accent_color=ERROR)
        self._ma_storno_betrag = KpiCard(texts.PM_PERF_STORNOQUOTE_BETRAG, accent_color=WARNING)
        self._ma_storno_betrag.setToolTip(texts.PM_PERF_STORNOQUOTE_BETRAG_TIP)
        self._ma_storno_vtr = KpiCard(texts.PM_PERF_STORNOQUOTE_VERTRAEGE, accent_color=WARNING)
        self._ma_storno_vtr.setToolTip(texts.PM_PERF_STORNOQUOTE_VERTRAEGE_TIP)
        self._ma_positionen_monat = KpiCard(texts.PM_PERF_POSITIONEN_MONAT, accent_color=PRIMARY_900)
        self._ma_positionen_ytd = KpiCard(texts.PM_PERF_POSITIONEN_YTD, accent_color=PRIMARY_900)

        grid.addWidget(self._ma_provision_monat, 0, 0)
        grid.addWidget(self._ma_provision_ytd, 0, 1)
        grid.addWidget(self._ma_rueck_monat, 0, 2)
        grid.addWidget(self._ma_rueck_ytd, 0, 3)
        grid.addWidget(self._ma_storno_betrag, 1, 0)
        grid.addWidget(self._ma_storno_vtr, 1, 1)
        grid.addWidget(self._ma_positionen_monat, 1, 2)
        grid.addWidget(self._ma_positionen_ytd, 1, 3)

        layout.addLayout(grid)
        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _render_mitarbeiter(self, ma: PerformanceMitarbeiter):
        self._ma_provision_monat.set_value(format_eur(ma.provision_monat))
        self._ma_provision_ytd.set_value(format_eur(ma.provision_ytd))

        self._ma_rueck_monat.set_value(format_eur(ma.rueckbelastung_monat))
        self._ma_rueck_ytd.set_value(format_eur(ma.rueckbelastung_ytd))

        self._ma_storno_betrag.set_value(f"{ma.stornoquote_betrag:.1f} %")
        self._ma_storno_betrag.set_subline(
            f"{texts.PM_PERF_RUECKBELASTUNG_YTD}: {format_eur(abs(ma.rueckbelastung_ytd))}"
        )
        self._ma_storno_vtr.set_value(f"{ma.stornoquote_vertraege:.1f} %")
        self._ma_storno_vtr.set_subline(
            f"{ma.stornierte_contracts} / {ma.total_contracts} {texts.PM_PERF_TOTAL_CONTRACTS}"
        )

        self._ma_positionen_monat.set_value(str(ma.positionen_monat))
        self._ma_positionen_ytd.set_value(str(ma.positionen_ytd))

    # ── Tab 2: ACENCIA ──

    def _build_acencia_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(12)

        self._ac_ag_monat = KpiCard(texts.PM_PERF_AG_ANTEIL_MONAT, accent_color=ACCENT_500)
        self._ac_ag_ytd = KpiCard(texts.PM_PERF_AG_ANTEIL_YTD, accent_color=ACCENT_500)
        self._ac_ueber_monat = KpiCard(texts.PM_PERF_UEBERSCHUSS_MONAT, accent_color=SUCCESS)
        self._ac_ueber_monat.setToolTip(texts.PM_PERF_UEBERSCHUSS_TIP)
        self._ac_ueber_ytd = KpiCard(texts.PM_PERF_UEBERSCHUSS_YTD, accent_color=SUCCESS)
        self._ac_ueber_ytd.setToolTip(texts.PM_PERF_UEBERSCHUSS_TIP)
        self._ac_eingang_monat = KpiCard(texts.PM_PERF_EINGANG_MONAT, accent_color=PRIMARY_900)
        self._ac_eingang_ytd = KpiCard(texts.PM_PERF_EINGANG_YTD, accent_color=PRIMARY_900)
        self._ac_berater_monat = KpiCard(texts.PM_PERF_AUSZAHLUNG_BERATER_MONAT, accent_color=PRIMARY_500)
        self._ac_berater_ytd = KpiCard(texts.PM_PERF_AUSZAHLUNG_BERATER_YTD, accent_color=PRIMARY_500)
        self._ac_tl_monat = KpiCard(texts.PM_PERF_TL_ANTEIL_MONAT, accent_color=PRIMARY_500)
        self._ac_tl_ytd = KpiCard(texts.PM_PERF_TL_ANTEIL_YTD, accent_color=PRIMARY_500)

        grid.addWidget(self._ac_ag_monat, 0, 0)
        grid.addWidget(self._ac_ag_ytd, 0, 1)
        grid.addWidget(self._ac_ueber_monat, 0, 2)
        grid.addWidget(self._ac_ueber_ytd, 0, 3)
        grid.addWidget(self._ac_eingang_monat, 1, 0)
        grid.addWidget(self._ac_eingang_ytd, 1, 1)
        grid.addWidget(self._ac_berater_monat, 1, 2)
        grid.addWidget(self._ac_berater_ytd, 1, 3)
        grid.addWidget(self._ac_tl_monat, 2, 0)
        grid.addWidget(self._ac_tl_ytd, 2, 1)

        layout.addLayout(grid)
        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _render_acencia(self, ac: PerformanceAcencia):
        self._ac_ag_monat.set_value(format_eur(ac.ag_anteil_monat))
        self._ac_ag_ytd.set_value(format_eur(ac.ag_anteil_ytd))
        self._ac_ueber_monat.set_value(format_eur(ac.ueberschuss_monat))
        self._ac_ueber_ytd.set_value(format_eur(ac.ueberschuss_ytd))
        self._ac_eingang_monat.set_value(format_eur(ac.eingang_monat))
        self._ac_eingang_ytd.set_value(format_eur(ac.eingang_ytd))
        self._ac_berater_monat.set_value(format_eur(ac.auszahlung_berater_monat))
        self._ac_berater_ytd.set_value(format_eur(ac.auszahlung_berater_ytd))
        self._ac_tl_monat.set_value(format_eur(ac.tl_anteil_monat))
        self._ac_tl_ytd.set_value(format_eur(ac.tl_anteil_ytd))

    # ── Tab 3: Fuehrungskraft ──

    def _build_fuehrungskraft_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(12)

        self._fk_umsatz_monat = KpiCard(texts.PM_PERF_TEAM_UMSATZ_MONAT, accent_color=SUCCESS)
        self._fk_umsatz_ytd = KpiCard(texts.PM_PERF_TEAM_UMSATZ_YTD, accent_color=SUCCESS)
        self._fk_ag_monat = KpiCard(texts.PM_PERF_TEAM_AG_ANTEIL_MONAT, accent_color=ACCENT_500)
        self._fk_ag_ytd = KpiCard(texts.PM_PERF_TEAM_AG_ANTEIL_YTD, accent_color=ACCENT_500)
        self._fk_rueck_monat = KpiCard(texts.PM_PERF_TEAM_RUECKBELASTUNG_MONAT, accent_color=ERROR)
        self._fk_rueck_ytd = KpiCard(texts.PM_PERF_TEAM_RUECKBELASTUNG_YTD, accent_color=ERROR)

        grid.addWidget(self._fk_umsatz_monat, 0, 0)
        grid.addWidget(self._fk_umsatz_ytd, 0, 1)
        grid.addWidget(self._fk_ag_monat, 0, 2)
        grid.addWidget(self._fk_ag_ytd, 0, 3)
        grid.addWidget(self._fk_rueck_monat, 1, 0)
        grid.addWidget(self._fk_rueck_ytd, 1, 1)

        layout.addLayout(grid)

        self._team_model = FuehrungskraftModel()
        self._team_table = QTableView()
        self._team_table.setModel(self._team_model)
        self._team_table.setStyleSheet(get_provision_table_style())
        self._team_table.setEditTriggers(QTableView.NoEditTriggers)
        self._team_table.setSelectionBehavior(QTableView.SelectRows)
        self._team_table.setAlternatingRowColors(True)
        self._team_table.verticalHeader().setVisible(False)
        hh = self._team_table.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self._team_empty = QLabel(texts.PM_PERF_NO_TEAM)
        self._team_empty.setAlignment(Qt.AlignCenter)
        self._team_empty.setStyleSheet(
            f"color: {PRIMARY_500}; font-size: {FONT_SIZE_CAPTION}; padding: 20px;")
        self._team_empty.setVisible(False)

        layout.addWidget(self._team_table, 1)
        layout.addWidget(self._team_empty)
        scroll.setWidget(inner)
        return scroll

    def _render_fuehrungskraft(self, fk: PerformanceFuehrungskraft):
        self._fk_umsatz_monat.set_value(format_eur(fk.team_umsatz_monat))
        self._fk_umsatz_ytd.set_value(format_eur(fk.team_umsatz_ytd))
        self._fk_ag_monat.set_value(format_eur(fk.team_ag_anteil_monat))
        self._fk_ag_ytd.set_value(format_eur(fk.team_ag_anteil_ytd))
        self._fk_rueck_monat.set_value(format_eur(fk.team_rueckbelastung_monat))
        self._fk_rueck_ytd.set_value(format_eur(fk.team_rueckbelastung_ytd))

        members = fk.team_members
        self._team_model.set_data(members)
        has_data = bool(members)
        self._team_table.setVisible(has_data)
        self._team_empty.setVisible(not has_data)
