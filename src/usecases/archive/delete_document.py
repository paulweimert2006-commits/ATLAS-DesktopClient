"""
UseCase: Dokumente loeschen.
"""

from typing import List

from domain.archive.interfaces import IDocumentRepository
from domain.archive.entities import Document, DeleteResult


class DeleteDocument:
    """Loescht ein oder mehrere Dokumente."""

    def __init__(self, repository: IDocumentRepository):
        self._repo = repository

    def execute_single(self, doc: Document) -> DeleteResult:
        success = self._repo.delete(doc.id)
        return DeleteResult(
            deleted_count=1 if success else 0,
            total_requested=1,
        )

    def execute_bulk(self, documents: List[Document]) -> DeleteResult:
        doc_ids = [d.id for d in documents]
        deleted = self._repo.delete_documents(doc_ids)
        return DeleteResult(
            deleted_count=deleted,
            total_requested=len(doc_ids),
        )
