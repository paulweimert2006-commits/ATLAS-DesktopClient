"""
UseCase: Dokument hochladen.
"""

from domain.archive.interfaces import IDocumentRepository
from domain.archive.entities import Document, UploadResult


class UploadDocument:
    """Laedt ein einzelnes Dokument in die Eingangsbox hoch."""

    def __init__(self, repository: IDocumentRepository):
        self._repo = repository

    def execute(
        self, file_path: str, *,
        source_type: str = 'manual_upload',
    ) -> UploadResult:
        doc = self._repo.upload(file_path, source_type=source_type)
        if doc:
            return UploadResult(
                success=True,
                filename=doc.original_filename,
                document=doc,
                is_duplicate=doc.is_duplicate,
            )
        from i18n.de import WORKER_UPLOAD_FAILED
        return UploadResult(
            success=False,
            filename=file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path.rsplit('\\', 1)[-1],
            error=WORKER_UPLOAD_FAILED,
        )
