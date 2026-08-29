"""Data access for the portal module. Private to this module.

Deliberately **not** a `BaseRepository`: that one exposes `update` and `delete`,
and `raw` may never be rewritten (Artículo III). Leaving the methods out is the
cheap way to make the rule hold without anyone having to remember it.

The one write after the insert is `mark_normalized`, and it is narrow on
purpose: it touches a bookkeeping column and can never reach the content, the
hash or the moment the document arrived.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portal.models import PortalDocument


class RawDocumentRepository:
    """Appends documents to `raw` and reads them back. Nothing else."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        *,
        section: str,
        content: bytes,
        content_hash: str,
        content_type: str,
        job_run_id: int | None = None,
    ) -> PortalDocument:
        """Store a document exactly as it arrived."""
        document = PortalDocument(
            section=section,
            content=content,
            content_hash=content_hash,
            content_type=content_type,
            job_run_id=job_run_id,
        )
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def mark_normalized(self, document: PortalDocument, moment: datetime) -> None:
        """Record that the pipeline finished reading this document.

        Until this is set, the document is evidence that nobody could interpret,
        and the next attempt has to try again instead of skipping it.
        """
        document.normalized_at = moment
        await self.session.flush()

    async def get(self, document_id: int) -> PortalDocument | None:
        """Return a document by id, or None."""
        return await self.session.get(PortalDocument, document_id)

    async def get_by_hash(self, content_hash: str) -> PortalDocument | None:
        """Return the document with this content hash, or None.

        This is the idempotency check: the same bytes are never stored twice.
        """
        result = await self.session.execute(
            select(PortalDocument).where(PortalDocument.content_hash == content_hash)
        )
        return result.scalar_one_or_none()
