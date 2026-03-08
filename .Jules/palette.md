# Palette's Journal - UX & Accessibility Learnings

## 2026-03-08 - Standardized Keyboard Shortcuts and Screen Reader Support
**Learning:** Standardizing keyboard shortcuts (F5, Ctrl+R, etc.) and adding explicit accessible names (setAccessibleName) significantly improves both power-user efficiency and accessibility for screen readers in PySide6 applications.
**Action:** Always include keyboard shortcut hints in tooltips (localized as 'Strg'/'Umschalt' for German) and define `setAccessibleName` using i18n constants for all primary action buttons.
