## 2026-03-14 - [BiPRO UI Accessibility & Discovery]
**Learning:** Icon-enhanced buttons in PySide6 require explicit `setAccessibleName` for screen readers, as visual indicators (emojis) can clutter or obscure the functional intent for accessibility tools. Localized keyboard shortcut hints in tooltips significantly improve power-user discoverability without increasing cognitive load.
**Action:** Always pair emoji labels with `setAccessibleName` and include localized keyboard shortcut hints (e.g., '(Strg+R)') in tooltips for all primary and secondary action buttons.
