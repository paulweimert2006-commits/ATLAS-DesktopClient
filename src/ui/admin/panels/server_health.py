"""
ACENCIA ATLAS - Server-Gesundheit Panel

Umfassender Health-Check des Backends mit visueller Darstellung.
Fuehrt ~35 Einzel-Checks durch, speichert Ergebnisse und vergleicht
mit historischen Durchschnittswerten.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy, QProgressBar,
    QMessageBox, QPlainTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from api.client import APIClient
from api.admin import AdminAPI
from i18n import de as texts

from ui.styles.tokens import (
    PRIMARY_900, PRIMARY_500, PRIMARY_100, PRIMARY_0,
    ACCENT_500, ACCENT_100,
    SUCCESS, SUCCESS_LIGHT, WARNING, WARNING_LIGHT,
    ERROR, ERROR_LIGHT,
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    BORDER_DEFAULT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED, TEXT_INVERSE,
    FONT_HEADLINE, FONT_BODY, FONT_MONO,
    FONT_SIZE_H1, FONT_SIZE_H2, FONT_SIZE_H3, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    FONT_WEIGHT_MEDIUM, FONT_WEIGHT_BOLD,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
    SPACING_SM, SPACING_MD, SPACING_LG,
    get_button_primary_style, get_button_secondary_style,
)
from ui.admin.workers import (
    RunHealthCheckWorker, LoadHealthHistoryWorker,
    LoadMigrationsWorker, ExecuteMigrationWorker,
)

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    "healthy": SUCCESS,
    "degraded": WARNING,
    "critical": ERROR,
    "error": ERROR,
}

STATUS_BG_COLORS = {
    "healthy": SUCCESS_LIGHT,
    "degraded": WARNING_LIGHT,
    "critical": ERROR_LIGHT,
    "error": ERROR_LIGHT,
}

CHECK_STATUS_ICONS = {
    "ok": "\u2714",
    "warning": "\u26A0",
    "critical": "\u2716",
    "error": "\u2716",
}

CATEGORY_LABELS = {
    "connection": texts.HEALTH_CAT_CONNECTION,
    "performance": texts.HEALTH_CAT_PERFORMANCE,
    "storage": texts.HEALTH_CAT_STORAGE,
    "config": texts.HEALTH_CAT_CONFIG,
    "stability": texts.HEALTH_CAT_STABILITY,
}

CATEGORY_ICONS = {
    "connection": "\U0001F50C",
    "performance": "\u26A1",
    "storage": "\U0001F4BE",
    "config": "\u2699",
    "stability": "\U0001F6E1",
}


class ServerHealthPanel(QWidget):
    """Admin-Panel fuer umfassende Server-Gesundheitspruefung."""

    def __init__(self, api_client: APIClient, toast_manager,
                 admin_api: AdminAPI, **kwargs):
        super().__init__()
        self._api_client = api_client
        self._toast_manager = toast_manager
        self._admin_api = admin_api
        self._active_workers: list = []
        self._last_result: Optional[Dict] = None
        self._history: List[Dict] = []
        self._migrations: List[Dict] = []
        self._create_ui()

    def load_data(self):
        """Laedt History und Migrationen beim Panel-Wechsel."""
        self._load_history()
        self._load_migrations()

    # ================================================================
    #  UI-Aufbau
    # ================================================================

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Header ---
        header = QHBoxLayout()

        title = QLabel(texts.HEALTH_TITLE)
        title.setFont(QFont(FONT_HEADLINE, 18))
        title.setStyleSheet(f"color: {PRIMARY_900};")
        header.addWidget(title)

        header.addStretch()

        self._status_label = QLabel(texts.HEALTH_NO_RUNS)
        self._status_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: {FONT_SIZE_BODY};
        """)
        header.addWidget(self._status_label)

        self._run_btn = QPushButton(texts.HEALTH_RUN_CHECK)
        self._run_btn.setStyleSheet(get_button_primary_style())
        self._run_btn.setMinimumWidth(180)
        self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.clicked.connect(self._start_health_check)
        header.addWidget(self._run_btn)

        layout.addLayout(header)

        # --- Overall-Status-Banner ---
        self._banner = QFrame()
        self._banner.setFixedHeight(80)
        self._banner.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border-radius: {RADIUS_LG};
                border: 1px solid {BORDER_DEFAULT};
            }}
        """)
        self._banner_layout = QHBoxLayout(self._banner)
        self._banner_layout.setContentsMargins(24, 12, 24, 12)

        self._banner_status = QLabel("--")
        self._banner_status.setFont(QFont(FONT_HEADLINE, 20))
        self._banner_status.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        self._banner_layout.addWidget(self._banner_status)

        self._banner_layout.addStretch()

        self._banner_stats = QLabel("")
        self._banner_stats.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: {FONT_SIZE_BODY};
            background: transparent;
        """)
        self._banner_stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._banner_layout.addWidget(self._banner_stats)

        layout.addWidget(self._banner)

        # --- Progress Bar (versteckt bis Check laeuft) ---
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.hide()
        layout.addWidget(self._progress)

        # --- Scroll-Bereich fuer Check-Ergebnisse ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._checks_container = QWidget()
        self._checks_container.setStyleSheet("background: transparent;")
        self._checks_layout = QVBoxLayout(self._checks_container)
        self._checks_layout.setContentsMargins(0, 0, 0, 0)
        self._checks_layout.setSpacing(16)
        self._checks_layout.addStretch()

        scroll.setWidget(self._checks_container)
        layout.addWidget(scroll, 1)

        # --- Migrations-Bereich ---
        mig_frame = QFrame()
        mig_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_LG};
            }}
        """)
        mig_layout = QVBoxLayout(mig_frame)
        mig_layout.setContentsMargins(20, 16, 20, 16)
        mig_layout.setSpacing(8)

        mig_header = QHBoxLayout()

        mig_title = QLabel(f"\U0001F4E6  {texts.MIGRATIONS_TITLE}")
        mig_title.setFont(QFont(FONT_HEADLINE, 13))
        mig_title.setStyleSheet(f"color: {PRIMARY_900}; border: none; background: transparent;")
        mig_header.addWidget(mig_title)

        mig_header.addStretch()

        self._mig_summary_label = QLabel("")
        self._mig_summary_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: {FONT_SIZE_CAPTION};
            border: none;
            background: transparent;
        """)
        mig_header.addWidget(self._mig_summary_label)

        self._mig_refresh_btn = QPushButton(texts.MIGRATIONS_REFRESH)
        self._mig_refresh_btn.setStyleSheet(get_button_secondary_style())
        self._mig_refresh_btn.setCursor(Qt.PointingHandCursor)
        self._mig_refresh_btn.clicked.connect(self._load_migrations)
        mig_header.addWidget(self._mig_refresh_btn)

        mig_layout.addLayout(mig_header)

        mig_sep = QFrame()
        mig_sep.setFixedHeight(1)
        mig_sep.setStyleSheet(f"background-color: {BORDER_DEFAULT}; border: none;")
        mig_layout.addWidget(mig_sep)

        self._mig_list_container = QVBoxLayout()
        self._mig_list_container.setSpacing(4)
        mig_layout.addLayout(self._mig_list_container)

        self._mig_empty_label = QLabel(texts.MIGRATIONS_EMPTY)
        self._mig_empty_label.setStyleSheet(f"""
            color: {TEXT_DISABLED};
            font-size: {FONT_SIZE_BODY};
            padding: 12px;
            border: none;
            background: transparent;
        """)
        self._mig_empty_label.setAlignment(Qt.AlignCenter)
        self._mig_list_container.addWidget(self._mig_empty_label)

        layout.addWidget(mig_frame)

    # ================================================================
    #  Health-Check ausfuehren
    # ================================================================

    def _start_health_check(self):
        self._run_btn.setEnabled(False)
        self._run_btn.setText(texts.HEALTH_RUNNING)
        self._progress.show()

        worker = RunHealthCheckWorker(self._admin_api)
        worker.finished.connect(self._on_check_finished)
        worker.error.connect(self._on_check_error)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(lambda: self._cleanup_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def _on_check_finished(self, data: dict):
        self._last_result = data
        self._run_btn.setEnabled(True)
        self._run_btn.setText(texts.HEALTH_RUN_CHECK)
        self._progress.hide()

        now = datetime.now().strftime("%H:%M:%S")
        self._status_label.setText(texts.HEALTH_LAST_RUN.format(time=now))

        self._render_results(data)
        self._load_history()

    def _on_check_error(self, error: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText(texts.HEALTH_RUN_CHECK)
        self._progress.hide()

        if self._toast_manager:
            self._toast_manager.show_error(
                texts.HEALTH_ERROR_LOAD.format(error=error)
            )

    # ================================================================
    #  History laden
    # ================================================================

    def _load_history(self):
        worker = LoadHealthHistoryWorker(self._admin_api, limit=10)
        worker.finished.connect(self._on_history_loaded)
        worker.error.connect(lambda e: logger.warning(f"Health-History Laden: {e}"))
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(lambda: self._cleanup_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def _on_history_loaded(self, runs: list):
        self._history = runs

    # ================================================================
    #  Ergebnisse rendern
    # ================================================================

    def _render_results(self, data: dict):
        self._update_banner(data)
        self._render_checks(data.get("checks", []))

    def _update_banner(self, data: dict):
        status = data.get("overall_status", "healthy")
        color = STATUS_COLORS.get(status, TEXT_SECONDARY)
        bg = STATUS_BG_COLORS.get(status, BG_SECONDARY)

        status_labels = {
            "healthy": texts.HEALTH_OVERALL_HEALTHY,
            "degraded": texts.HEALTH_OVERALL_DEGRADED,
            "critical": texts.HEALTH_OVERALL_CRITICAL,
            "error": texts.HEALTH_OVERALL_ERROR,
        }

        self._banner.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: {RADIUS_LG};
                border: 2px solid {color};
            }}
        """)
        self._banner_status.setText(status_labels.get(status, status))
        self._banner_status.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
            background: transparent;
        """)

        parts = [
            texts.HEALTH_CHECKS_TOTAL.format(total=data.get("total_checks", 0)),
            texts.HEALTH_CHECKS_PASSED.format(count=data.get("passed", 0)),
        ]
        if data.get("warnings", 0) > 0:
            parts.append(texts.HEALTH_CHECKS_WARNINGS.format(count=data["warnings"]))
        if data.get("critical", 0) > 0:
            parts.append(texts.HEALTH_CHECKS_CRITICAL.format(count=data["critical"]))
        if data.get("errors", 0) > 0:
            parts.append(texts.HEALTH_CHECKS_ERRORS.format(count=data["errors"]))
        parts.append(texts.HEALTH_DURATION.format(ms=data.get("total_duration_ms", 0)))

        self._banner_stats.setText("  |  ".join(parts))
        self._banner_stats.setStyleSheet(f"""
            color: {color};
            font-size: {FONT_SIZE_BODY};
            background: transparent;
        """)

    def _render_checks(self, checks: list):
        # Altes Layout leeren
        while self._checks_layout.count():
            item = self._checks_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        categories: Dict[str, list] = {}
        for c in checks:
            cat = c.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(c)

        cat_order = ["connection", "performance", "storage", "config", "stability"]
        for cat in cat_order:
            if cat not in categories:
                continue
            cat_checks = categories[cat]

            cat_widget = self._build_category_section(cat, cat_checks)
            self._checks_layout.addWidget(cat_widget)

        # History-Kompakt am Ende
        if self._history and len(self._history) > 1:
            history_widget = self._build_history_section()
            self._checks_layout.addWidget(history_widget)

        self._checks_layout.addStretch()

    def _build_category_section(self, category: str, checks: list) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_LG};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        icon = CATEGORY_ICONS.get(category, "")
        label = CATEGORY_LABELS.get(category, category.title())

        ok_count = sum(1 for c in checks if c["status"] == "ok")
        total = len(checks)

        header = QHBoxLayout()
        cat_label = QLabel(f"{icon}  {label}")
        cat_label.setFont(QFont(FONT_HEADLINE, 13))
        cat_label.setStyleSheet(f"color: {PRIMARY_900}; border: none; background: transparent;")
        header.addWidget(cat_label)

        header.addStretch()

        ratio_color = SUCCESS if ok_count == total else (WARNING if ok_count >= total - 1 else ERROR)
        ratio = QLabel(f"{ok_count}/{total}")
        ratio.setStyleSheet(f"""
            color: {ratio_color};
            font-weight: bold;
            font-size: {FONT_SIZE_BODY};
            border: none;
            background: transparent;
        """)
        header.addWidget(ratio)

        layout.addLayout(header)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER_DEFAULT}; border: none;")
        layout.addWidget(sep)

        for check in checks:
            row = self._build_check_row(check)
            layout.addWidget(row)

        return frame

    def _build_check_row(self, check: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(12)

        status = check.get("status", "ok")
        icon_char = CHECK_STATUS_ICONS.get(status, "?")
        color_map = {"ok": SUCCESS, "warning": WARNING, "critical": ERROR, "error": ERROR}
        bg_map = {"ok": SUCCESS_LIGHT, "warning": WARNING_LIGHT, "critical": ERROR_LIGHT, "error": ERROR_LIGHT}

        icon = QLabel(icon_char)
        icon.setFixedSize(24, 24)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"""
            color: {color_map.get(status, TEXT_SECONDARY)};
            background-color: {bg_map.get(status, BG_SECONDARY)};
            border-radius: 12px;
            font-size: 11pt;
            font-weight: bold;
        """)
        h.addWidget(icon)

        name = QLabel(check.get("name", ""))
        name.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_BODY};
        """)
        name.setMinimumWidth(280)
        h.addWidget(name)

        detail_text = check.get("detail", "")
        if detail_text:
            detail = QLabel(str(detail_text))
            detail.setStyleSheet(f"""
                color: {TEXT_SECONDARY};
                font-size: {FONT_SIZE_CAPTION};
                font-family: {FONT_MONO};
            """)
            detail.setMaximumWidth(400)
            detail.setWordWrap(True)
            h.addWidget(detail)

        h.addStretch()

        ms = check.get("duration_ms", 0)
        duration = QLabel(f"{ms:.1f}ms")
        duration.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: {FONT_SIZE_CAPTION};
            font-family: {FONT_MONO};
        """)
        duration.setFixedWidth(70)
        duration.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(duration)

        comparison = check.get("comparison")
        if comparison:
            trend = comparison.get("trend", "stable")
            pct = abs(comparison.get("change_pct", 0))

            if trend == "better":
                trend_text = texts.HEALTH_TREND_BETTER.format(pct=pct)
                trend_color = SUCCESS
            elif trend == "worse":
                trend_text = texts.HEALTH_TREND_WORSE.format(pct=pct)
                trend_color = ERROR
            else:
                trend_text = texts.HEALTH_TREND_STABLE
                trend_color = TEXT_SECONDARY

            trend_label = QLabel(trend_text)
            trend_label.setStyleSheet(f"""
                color: {trend_color};
                font-size: {FONT_SIZE_CAPTION};
            """)
            trend_label.setFixedWidth(220)
            h.addWidget(trend_label)
        else:
            spacer = QLabel("")
            spacer.setFixedWidth(220)
            h.addWidget(spacer)

        return row

    def _build_history_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_LG};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title = QLabel(f"\U0001F4CA  {texts.HEALTH_HISTORY_TITLE}")
        title.setFont(QFont(FONT_HEADLINE, 13))
        title.setStyleSheet(f"color: {PRIMARY_900}; border: none; background: transparent;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER_DEFAULT}; border: none;")
        layout.addWidget(sep)

        for run in self._history[:8]:
            row = QWidget()
            row.setStyleSheet("background: transparent; border: none;")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 2, 0, 2)
            h.setSpacing(12)

            status = run.get("overall_status", "healthy")
            color = STATUS_COLORS.get(status, TEXT_SECONDARY)

            dot = QLabel("\u25CF")
            dot.setFixedSize(16, 16)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(f"color: {color}; font-size: 10pt;")
            h.addWidget(dot)

            created = run.get("created_at", "")
            try:
                dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                formatted = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                formatted = created

            date_label = QLabel(formatted)
            date_label.setStyleSheet(f"""
                color: {TEXT_PRIMARY};
                font-size: {FONT_SIZE_BODY};
                font-family: {FONT_MONO};
            """)
            date_label.setFixedWidth(140)
            h.addWidget(date_label)

            status_labels = {
                "healthy": texts.HEALTH_OVERALL_HEALTHY,
                "degraded": texts.HEALTH_OVERALL_DEGRADED,
                "critical": texts.HEALTH_OVERALL_CRITICAL,
                "error": texts.HEALTH_OVERALL_ERROR,
            }
            sl = QLabel(status_labels.get(status, status))
            sl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: {FONT_SIZE_BODY};")
            sl.setFixedWidth(100)
            h.addWidget(sl)

            counts = []
            p = run.get("passed", 0)
            w = run.get("warnings", 0)
            cr = run.get("critical", 0)
            er = run.get("errors", 0)
            if p:
                counts.append(f"{p} OK")
            if w:
                counts.append(f"{w} Warn")
            if cr:
                counts.append(f"{cr} Crit")
            if er:
                counts.append(f"{er} Err")
            counts_label = QLabel(" | ".join(counts))
            counts_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION};")
            h.addWidget(counts_label)

            h.addStretch()

            dur = run.get("total_duration_ms", 0)
            dur_label = QLabel(f"{dur}ms")
            dur_label.setStyleSheet(f"""
                color: {TEXT_SECONDARY};
                font-size: {FONT_SIZE_CAPTION};
                font-family: {FONT_MONO};
            """)
            dur_label.setFixedWidth(80)
            dur_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(dur_label)

            layout.addWidget(row)

        return frame

    # ================================================================
    #  Migrationen
    # ================================================================

    def _load_migrations(self):
        self._mig_refresh_btn.setEnabled(False)
        self._mig_refresh_btn.setText(texts.MIGRATIONS_LOADING)

        worker = LoadMigrationsWorker(self._admin_api)
        worker.finished.connect(self._on_migrations_loaded)
        worker.error.connect(self._on_migrations_error)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(lambda: self._cleanup_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def _on_migrations_loaded(self, data: dict):
        self._mig_refresh_btn.setEnabled(True)
        self._mig_refresh_btn.setText(texts.MIGRATIONS_REFRESH)

        self._migrations = data.get('migrations', [])
        total = data.get('total', 0)
        applied = data.get('applied', 0)
        pending = data.get('pending', 0)
        manual = data.get('manual', 0)

        self._mig_summary_label.setText(
            texts.MIGRATIONS_SUMMARY.format(
                total=total, applied=applied, pending=pending, manual=manual
            )
        )

        self._render_migrations()

    def _on_migrations_error(self, error: str):
        self._mig_refresh_btn.setEnabled(True)
        self._mig_refresh_btn.setText(texts.MIGRATIONS_REFRESH)
        logger.error(f"Migrationen laden fehlgeschlagen: {error}")
        if self._toast_manager:
            self._toast_manager.show_error(
                texts.MIGRATIONS_ERROR.format(error=error)
            )

    def _render_migrations(self):
        while self._mig_list_container.count():
            item = self._mig_list_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self._migrations:
            empty = QLabel(texts.MIGRATIONS_EMPTY)
            empty.setStyleSheet(f"""
                color: {TEXT_DISABLED};
                font-size: {FONT_SIZE_BODY};
                padding: 12px;
                border: none;
                background: transparent;
            """)
            empty.setAlignment(Qt.AlignCenter)
            self._mig_list_container.addWidget(empty)
            return

        for mig in self._migrations:
            row = self._build_migration_row(mig)
            self._mig_list_container.addWidget(row)

    def _build_migration_row(self, mig: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(12)

        status = mig.get('status', 'unknown')
        mig_type = mig.get('type', '?')

        status_colors = {
            'applied': SUCCESS,
            'pending': WARNING,
            'manual': ACCENT_500,
            'unknown': TEXT_DISABLED,
        }
        status_bg_colors = {
            'applied': SUCCESS_LIGHT,
            'pending': WARNING_LIGHT,
            'manual': f"{ACCENT_500}22",
            'unknown': BG_SECONDARY,
        }
        status_labels = {
            'applied': texts.MIGRATIONS_STATUS_APPLIED,
            'pending': texts.MIGRATIONS_STATUS_PENDING,
            'manual': texts.MIGRATIONS_STATUS_MANUAL,
            'unknown': texts.MIGRATIONS_STATUS_UNKNOWN,
        }

        color = status_colors.get(status, TEXT_DISABLED)
        bg = status_bg_colors.get(status, BG_SECONDARY)

        status_pill = QLabel(status_labels.get(status, status))
        status_pill.setFixedWidth(90)
        status_pill.setAlignment(Qt.AlignCenter)
        status_pill.setStyleSheet(f"""
            color: {color};
            background-color: {bg};
            border-radius: 10px;
            font-size: {FONT_SIZE_CAPTION};
            font-weight: bold;
            padding: 3px 8px;
        """)
        h.addWidget(status_pill)

        type_label = QLabel(texts.MIGRATIONS_TYPE_PHP if mig_type == 'php' else texts.MIGRATIONS_TYPE_SQL)
        type_label.setFixedWidth(40)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: {FONT_SIZE_CAPTION};
            font-family: {FONT_MONO};
            font-weight: bold;
            border: none;
            background: transparent;
        """)
        h.addWidget(type_label)

        name_label = QLabel(mig.get('filename', ''))
        name_label.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_BODY};
            font-family: {FONT_MONO};
        """)
        name_label.setMinimumWidth(300)
        h.addWidget(name_label)

        h.addStretch()

        modified = mig.get('modified', '')
        if modified:
            date_label = QLabel(modified)
            date_label.setStyleSheet(f"""
                color: {TEXT_SECONDARY};
                font-size: {FONT_SIZE_CAPTION};
                font-family: {FONT_MONO};
            """)
            date_label.setFixedWidth(140)
            h.addWidget(date_label)

        size_bytes = mig.get('size_bytes', 0)
        size_kb = round(size_bytes / 1024, 1) if size_bytes else 0
        size_label = QLabel(f"{size_kb} KB")
        size_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: {FONT_SIZE_CAPTION};
            font-family: {FONT_MONO};
        """)
        size_label.setFixedWidth(60)
        size_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(size_label)

        exec_btn = QPushButton(texts.MIGRATIONS_EXECUTE)
        exec_btn.setFixedWidth(110)
        exec_btn.setCursor(Qt.PointingHandCursor)
        exec_btn.setStyleSheet(get_button_secondary_style())
        filename = mig.get('filename', '')
        exec_btn.clicked.connect(lambda _, f=filename: self._confirm_execute(f))
        h.addWidget(exec_btn)

        return row

    def _confirm_execute(self, filename: str):
        reply = QMessageBox.warning(
            self,
            texts.MIGRATIONS_CONFIRM_TITLE,
            texts.MIGRATIONS_CONFIRM_TEXT.format(filename=filename),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._execute_migration(filename)

    def _execute_migration(self, filename: str):
        worker = ExecuteMigrationWorker(self._admin_api, filename)
        worker.finished.connect(self._on_migration_executed)
        worker.error.connect(self._on_migration_exec_error)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(lambda: self._cleanup_worker(worker))
        self._active_workers.append(worker)
        worker.start()

    def _on_migration_executed(self, result: dict):
        success = result.get('success', False)
        output = result.get('output', '')
        filename = result.get('filename', '')

        if success:
            if self._toast_manager:
                self._toast_manager.show_success(
                    f"{texts.MIGRATIONS_SUCCESS}: {filename}"
                )
        else:
            if self._toast_manager:
                self._toast_manager.show_error(
                    texts.MIGRATIONS_ERROR.format(error=output[:200])
                )

        if output:
            self._show_output_dialog(filename, output, success)

        self._load_migrations()

    def _on_migration_exec_error(self, error: str):
        logger.error(f"Migration Ausfuehrung fehlgeschlagen: {error}")
        if self._toast_manager:
            self._toast_manager.show_error(
                texts.MIGRATIONS_ERROR.format(error=error)
            )

    def _show_output_dialog(self, filename: str, output: str, success: bool):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(f"{texts.MIGRATIONS_OUTPUT_TITLE}: {filename}")
        dlg.setIcon(QMessageBox.Information if success else QMessageBox.Warning)
        dlg.setText(texts.MIGRATIONS_SUCCESS if success else texts.MIGRATIONS_ERROR.format(error=""))
        dlg.setDetailedText(output)
        dlg.exec()

    # ================================================================
    #  Helpers
    # ================================================================

    def _cleanup_worker(self, worker):
        if worker in self._active_workers:
            self._active_workers.remove(worker)
