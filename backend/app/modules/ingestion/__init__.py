"""Ingestion: `raw` -> `staging`.

Hashes, types and normalises what the portal said into rows that either can be
interpreted or cannot. The ones that cannot are set aside with their reason
instead of being dropped, and they never stop the rest of the batch
(Artículo II).
"""
