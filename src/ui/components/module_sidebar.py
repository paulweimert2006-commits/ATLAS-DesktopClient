# -*- coding: utf-8 -*-
"""
ACENCIA ATLAS - Gemeinsame Modul-Sidebar-Basisklasse

Stellt die einheitliche Sidebar-Struktur fuer alle Module bereit:
- Back-Button (← Startseite)
- Section-Labels
- NavButtons (checkable, mit border-left Accent)
- Separator-Linien
- Optionaler Refresh-Button am unteren Rand
- Slide+Fade Eingangsanimation (steuerbar vom AppRouter)

Alle Modul-Hubs nutzen diese Klasse, um das Sidebar-Verhalten
zentral zu steuern, anstatt es in jedem Modul einzeln zu implementieren.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton,
    QSizePolicy, QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Signal, Qt, QTimeLine, QEasingCurve,
)

from i18n import de as texts
from ui.styles.tokens import (
    SIDEBAR_BG, SIDEBAR_TEXT, SIDEBAR_HOVER, SIDEBAR_WIDTH_INT,
    ACCENT_500, PRIMARY_500,
    FONT_BODY, FONT_SIZE_BODY, FONT_SIZE_CAPTION,
    BORDER_SUBTLE,
)

logger = logging.getLogger(__name__)


class ModuleNavButton(QPushButton):
    """Navigations-Button fuer Modul-Sidebars (ACENCIA CI-konform).

    Optionaler Subtext wird als zweite Zeile dargestellt.
    """

    def __init__(self, icon: str, text: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        if subtitle:
            display = f"   {icon}  {text}\n        {subtitle}"
            self.setMinimumHeight(56)
        else:
            display = f"   {icon}  {text}"
            self.setMinimumHeight(40)

        self.setText(display)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0px;
                padding: 8px 20px;
                text-align: left;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_CAPTION};
                color: {PRIMARY_500};
                line-height: 1.4;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
                color: {SIDEBAR_TEXT};
            }}
            QPushButton:checked {{
                background-color: {SIDEBAR_HOVER};
                border-left: 3px solid {ACCENT_500};
                color: {SIDEBAR_TEXT};
                font-weight: 500;
            }}
        """)


class ModuleSidebar(QFrame):
    """Gemeinsame Basisklasse fuer alle Modul-Sidebars.

    Bietet:
    - Einheitliches Layout (Back-Button, Sections, NavButtons, Stretch, Refresh)
    - Einheitliches Styling (SIDEBAR_BG, border-right)
    - Slide+Fade Enter/Exit-Animation (play_enter_animation / play_exit_animation)
    """

    _ENTER_DURATION = 380
    _EXIT_DURATION = 200
    _FADE_DURATION = 180

    back_requested = Signal()
    exit_animation_finished = Signal()

    def __init__(self, object_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFixedWidth(SIDEBAR_WIDTH_INT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._nav_buttons: list[ModuleNavButton] = []
        self._anim_group: Optional[QTimeLine] = None
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._setup_base_style()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(0)

        self._build_back_button()

    def _setup_base_style(self):
        name = self.objectName()
        self.setStyleSheet(f"""
            QFrame#{name} {{
                background-color: {SIDEBAR_BG};
                border-right: 1px solid {BORDER_SUBTLE};
            }}
        """)

    def _build_back_button(self):
        back_btn = QPushButton(f"  \u2190  {texts.DASHBOARD_BACK}")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setMinimumHeight(44)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {BORDER_SUBTLE};
                padding: 10px 16px;
                text-align: left;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_BODY};
                color: {ACCENT_500};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
            }}
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        self._layout.addWidget(back_btn)
        self._layout.addSpacing(12)

    # ------------------------------------------------------------------
    # Builder-Methoden fuer Subklassen
    # ------------------------------------------------------------------

    def add_section_label(self, text: str):
        """Fuegt ein Section-Label hinzu (z.B. 'KONTAKTE', 'DATEN')."""
        lbl = QLabel(f"  {text}")
        lbl.setStyleSheet(f"""
            color: {ACCENT_500}; font-family: {FONT_BODY};
            font-size: 9pt; font-weight: 700; letter-spacing: 1px;
            padding: 4px 16px 4px 16px;
        """)
        self._layout.addWidget(lbl)
        return lbl

    def add_section_label_padded(self, text: str):
        """Fuegt ein Section-Label mit mehr Top-Padding hinzu."""
        lbl = QLabel(f"  {text}")
        lbl.setStyleSheet(f"""
            color: {ACCENT_500}; font-family: {FONT_BODY};
            font-size: 9pt; font-weight: 700; letter-spacing: 1px;
            padding: 12px 16px 4px 16px;
        """)
        self._layout.addWidget(lbl)
        return lbl

    def add_separator(self):
        """Fuegt eine orangene Trennlinie hinzu."""
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {ACCENT_500}; margin: 8px 16px;")
        self._layout.addWidget(sep)
        return sep

    def add_nav(self, icon: str, title: str, subtitle: str,
                index: int, callback=None) -> ModuleNavButton:
        """Erzeugt einen NavButton und verbindet ihn optional mit einem Callback."""
        btn = ModuleNavButton(icon, title, subtitle)
        if callback is not None:
            btn.clicked.connect(lambda checked, i=index: callback(i))
        self._layout.addWidget(btn)
        self._nav_buttons.append(btn)
        return btn

    def add_stretch(self):
        """Fuegt einen vertikalen Stretch ein (vor Refresh-Button)."""
        self._layout.addStretch()

    def add_refresh_button(self, text: str, callback, tooltip: str = ""):
        """Fuegt einen Refresh-Button am unteren Rand hinzu."""
        btn = QPushButton(f"  \u21BB  {text}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(44)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-top: 1px solid {BORDER_SUBTLE};
                padding: 10px 16px;
                text-align: left;
                font-family: {FONT_BODY};
                font-size: {FONT_SIZE_CAPTION};
                color: {ACCENT_500};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {SIDEBAR_HOVER};
            }}
        """)
        btn.clicked.connect(callback)
        self._layout.addWidget(btn)
        return btn

    def add_admin_section(self, text: str):
        """Fuegt eine Admin-Style Sektion hinzu (Trennlinie + Label mit kleinem Font)."""
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {ACCENT_500}; border: none; margin: 0;")
        self._layout.addWidget(line)

        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            background-color: transparent;
            color: {PRIMARY_500};
            font-size: {FONT_SIZE_CAPTION};
            padding: 10px 20px 4px 20px;
            letter-spacing: 1px;
        """)
        self._layout.addWidget(lbl)
        return lbl

    def add_widget(self, widget):
        """Fuegt ein beliebiges Widget in das Sidebar-Layout ein."""
        self._layout.addWidget(widget)

    def add_spacing(self, pixels: int):
        """Fuegt vertikalen Abstand ein."""
        self._layout.addSpacing(pixels)

    @property
    def nav_buttons(self) -> list[ModuleNavButton]:
        return self._nav_buttons

    def set_checked(self, index: int):
        """Setzt den NavButton an Position `index` als aktiv."""
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    # ------------------------------------------------------------------
    # Slide+Fade Enter/Exit-Animationen
    # ------------------------------------------------------------------

    def _stop_running(self):
        """Stoppt laufende Timeline."""
        if self._anim_group is not None:
            self._anim_group.stop()
            try:
                self._anim_group.frameChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                self._anim_group.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._anim_group.deleteLater()
            self._anim_group = None

    def _apply_enter_frame(self, frame: int):
        """Berechnet slide-offset + opacity aus dem Frame-Wert (0..1000)."""
        t = frame / 1000.0
        offset = int(-SIDEBAR_WIDTH_INT * (1.0 - t))
        self.setContentsMargins(offset, 0, 0, 0)
        fade_ratio = self._ENTER_DURATION / max(self._FADE_DURATION, 1)
        opacity = min(1.0, t * fade_ratio)
        self._opacity_effect.setOpacity(opacity)

    def _apply_exit_frame(self, frame: int):
        """Berechnet slide-offset + opacity aus dem Frame-Wert (0..1000)."""
        t = frame / 1000.0
        offset = int(-SIDEBAR_WIDTH_INT * t)
        self.setContentsMargins(offset, 0, 0, 0)
        self._opacity_effect.setOpacity(1.0 - t)

    def play_enter_animation(self):
        """Sidebar gleitet sanft von links herein und fadet ein."""
        self._stop_running()

        self.setContentsMargins(-SIDEBAR_WIDTH_INT, 0, 0, 0)
        self._opacity_effect.setOpacity(0.0)
        self.show()

        tl = QTimeLine(self._ENTER_DURATION, self)
        tl.setFrameRange(0, 1000)
        tl.setUpdateInterval(12)
        tl.setEasingCurve(QEasingCurve.OutCubic)
        tl.frameChanged.connect(self._apply_enter_frame)
        tl.finished.connect(self._on_enter_finished)
        self._anim_group = tl
        tl.start()

    def _on_enter_finished(self):
        self.setContentsMargins(0, 0, 0, 0)
        self._opacity_effect.setOpacity(1.0)

    def play_exit_animation(self):
        """Sidebar gleitet sanft nach links heraus und fadet aus.

        Emittiert exit_animation_finished wenn fertig.
        """
        self._stop_running()

        self.setContentsMargins(0, 0, 0, 0)
        self._opacity_effect.setOpacity(1.0)

        tl = QTimeLine(self._EXIT_DURATION, self)
        tl.setFrameRange(0, 1000)
        tl.setUpdateInterval(12)
        tl.setEasingCurve(QEasingCurve.InCubic)
        tl.frameChanged.connect(self._apply_exit_frame)
        tl.finished.connect(self._on_exit_finished)
        self._anim_group = tl
        tl.start()

    def _on_exit_finished(self):
        self.setContentsMargins(0, 0, 0, 0)
        self._opacity_effect.setOpacity(1.0)
        self.exit_animation_finished.emit()

    def reset_animation_state(self):
        """Setzt den Animationszustand zurueck – versteckt die Sidebar visuell,
        bereit fuer eine frische Enter-Animation."""
        self._stop_running()
        self.setContentsMargins(-SIDEBAR_WIDTH_INT, 0, 0, 0)
        self._opacity_effect.setOpacity(0.0)
