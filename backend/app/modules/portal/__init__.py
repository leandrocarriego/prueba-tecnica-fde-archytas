"""Portal: browser automation over SIGProv, the read-only source system.

No `routes.py`: the module has no HTTP surface of its own. Celery tasks drive
it, and what it extracts leaves as a domain event. It is also where the portal
credentials live — and die (Artículo VII).
"""
