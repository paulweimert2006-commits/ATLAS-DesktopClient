"""
UseCase: Dokumente fuer die automatische Verarbeitung freigeben.

Verschiebt Dokumente zurueck in die Eingangsbox mit
processing_status='pending'.
"""

from typing import List

from domain.archive.interfaces import IDocumentRepository
from domain.archive.entities import Document


class IncludeForProcessing:
    """Gibt Dokumente fuer die automatische Verarbeitung frei."""

    def __init__(self, repository: IDocumentRepository):
        self._repo = repository

    def execute(self, documents: List[Document]) -> int:
        """Gibt Anzahl erfolgreich freigegebener Dokumente zurueck."""
        doc_ids = [d.id for d in documents]
        return self._repo.move_documents(
            doc_ids, 'eingang',
            processing_status='pending',
        )
