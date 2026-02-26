## 2026-02-26 - [BiPRO Accessibility & Shortcuts]
**Learning:** Accessibility and keyboard efficiency were missing in the BiPRO view. Icon-heavy buttons lacked screen reader context, and many actions were mouse-only. Additionally, the CI accent color (orange) failed WCAG contrast guidelines for text links.
**Action:** Always add `setAccessibleName` to buttons, include shortcut hints in tooltips, and use high-contrast blue (`PRIMARY_900`) for links instead of brand orange.
