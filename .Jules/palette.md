## 2026-03-07 - Accessibility and Visual Cues in BiPRO Actions

**Learning:** Combining visual indicators (emojis) with explicit `setAccessibleName` properties ensures that micro-UX improvements (like adding icons for delight) do not negatively impact screen reader experiences. Screen readers might mispronounce or skip emojis, so a clean, text-only accessible name is essential for critical action buttons.

**Action:** Whenever adding icons or emojis to button labels, always pair the change with a `setAccessibleName()` call in the UI code to provide a clear, unambiguous functional description for accessibility tools.
