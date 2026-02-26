"""
UseCase: Dokument herunterladen.
"""

from typing import Optional

from domain.archive.interfaces import IDocumentRepository
from domain.archive.entities import Document, DownloadResult
from domain.archive import archive_rules


class DownloadDocument:
    """Laedt ein Dokument herunter und archiviert es bei Bedarf automatisch."""

    def __init__(self, repository: IDocumentRepository):
        self._repo = repository

    def execute(
        self, doc: Document, target_dir: str,
    ) -> DownloadResult:
        saved_path = self._repo.download(
            doc.id, target_dir,
            filename_override=doc.original_filename,
        )

        if not saved_path:
            return DownloadResult(
                success=False,
                doc_id=doc.id,
                filename=doc.original_filename,
                error='Download fehlgeschlagen',
            )

        auto_archived = False
        if archive_rules.should_auto_archive_on_download(doc.box_type, doc.is_archived):
            if self._repo.archive_document(doc.id):
                auto_archived = True

        return DownloadResult(
            success=True,
            doc_id=doc.id,
            filename=doc.original_filename,
            saved_path=saved_path,
            auto_archived=auto_archived,
        )
