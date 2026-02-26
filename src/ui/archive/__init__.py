"""
ACENCIA ATLAS - Dokumentenarchiv UI-Module.

Neue Architektur (Clean Architecture):
    ui/archive/         - Qt-Widgets, Layout, Signals
    presenters/archive/ - Vermittler UI <-> UseCases
    usecases/archive/   - Anwendungslogik (kein Qt)
    domain/archive/     - Reine Business-Logik
    infrastructure/     - API, Filesystem, Threading

Import-Pfade (neuer kanonischer Pfad):
    from ui.archive.widgets import DocumentHistoryPanel, LoadingOverlay
    from ui.archive.models import DocumentTableModel, DocumentSortFilterProxy
    from ui.archive.table import DraggableDocumentView
    from ui.archive.search_widget import AtlasIndexWidget, SearchResultCard
    from ui.archive.sidebar import BoxSidebar
    from ui.archive.dialogs import SmartScanDialog
    from ui.archive.workers import MultiUploadWorker, ...

Backward-Kompatibilitaet:
    Alle Klassen sind weiterhin ueber archive_boxes_view.py importierbar.
"""
