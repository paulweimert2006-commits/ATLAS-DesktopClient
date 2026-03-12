## 2026-02-27 - [Accessibility & Keyboard Shortcuts in PySide6]
**Learning:** In PySide6, `QAction` objects do not support `setAccessibleName`. Additionally, merely hiding expert UI elements (`setVisible(False)`) is insufficient to prevent accidental keyboard shortcut triggers; they must also be explicitly disabled (`setEnabled(False)`).
**Action:** Always verify property support (like `setAccessibleName`) on specific Qt classes before batch assignment. Ensure mode-toggle logic synchronizes both visibility and enabled state for restricted widgets.

## 2026-02-27 - [Localized Shortcut Hints]
**Learning:** For desktop applications in the German market, users expect 'Strg' (Control) and 'Umschalt' (Shift) in shortcut hints. Tooltips are the ideal place for these hints to keep the primary UI clean.
**Action:** Store shortcut hint strings as i18n constants and append them to tooltips using the `(Shortcut)` convention.
