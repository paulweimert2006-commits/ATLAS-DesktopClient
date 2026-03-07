## 2026-03-07 - Safety Pattern for Destructive Shortcuts in Mode-based UIs
**Learning:** In Qt/PySide, keyboard shortcuts assigned to widgets can remain active even when the widget is hidden via `hide()` or `setVisible(False)`. This is particularly dangerous for destructive actions like "Acknowledge All" in an admin mode that is normally hidden from standard users.
**Action:** When toggling UI modes, ensure that expert or destructive widgets are also programmatically disabled using `setEnabled(False)` when hidden to effectively neutralize their shortcuts and prevent accidental background execution.

## 2026-03-07 - Localization and Accessible Names in PySide6
**Learning:** Hardcoding `setAccessibleName` strings in UI view files violates internationalization principles and leads to fragmented language support for screen reader users.
**Action:** Always store accessible names in the central translation system (e.g., `src/i18n/de.py`) using a clear naming convention like `ACC_*` to ensure consistent localization across all interface layers.
