## 2026-03-15 - BiPRO Action Consolidation

**Learning:** Large technician-style panels with multiple top-level buttons (5+) increase cognitive load and obscure the primary user path. Consolidating secondary/expert actions into a 'More' (•••) menu attached to a dominant primary action (44px height) significantly improves focus.

**Action:** Consolidate secondary technical actions into `QMenu` dropdowns in similar PySide6 views to maintain a clear interaction hierarchy. Always register `QAction` objects with the parent widget using `addAction()` to ensure keyboard shortcuts work globally.
