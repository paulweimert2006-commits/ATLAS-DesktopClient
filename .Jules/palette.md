## 2026-03-05 - Visual Consistency with Dynamic Text Updates
**Learning:** In PySide6, when adding emojis to button labels for visual delight, it is critical to also update all locations where `setText()` is called dynamically (e.g., during progress or state changes). Failing to do so causes the visual indicator to "flicker" out of existence when the operation starts, breaking the UX.
**Action:** Always grep for all `setText()` calls on a modified button to ensure the visual indicator (emoji) is preserved in all states.

## 2026-03-05 - Screen Reader Friendly Emojis
**Learning:** Prepending emojis to button text in PySide6 is great for visual recognition but can be noisy for screen readers if the emoji is read as a separate word.
**Action:** Use `setAccessibleName()` on buttons with emoji prefixes to provide a clean, descriptive label for assistive technologies that matches the localized intent without the visual-only prefix.
