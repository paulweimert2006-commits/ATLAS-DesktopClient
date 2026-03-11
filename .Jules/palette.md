## 2026-03-11 - BiPRO UI Keyboard Accessibility & Visual Delight
**Learning:** In PySide6, `QPushButton.setShortcut` is sufficient for window-wide shortcut triggering and does not require the button to have focus. Adding a redundant `QShortcut` for the same key sequence causes double-triggering of the associated action. Emojis and shortcut hints in localized strings provide immediate functional recognition.
**Action:** Use `QPushButton.setShortcut` for standard button actions and avoid redundant `QShortcut` listeners to prevent double execution.
