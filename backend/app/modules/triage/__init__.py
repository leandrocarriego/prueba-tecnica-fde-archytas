"""Triage: the queue of what could not be resolved, and the rules learned from it.

The queue is deliberately generic. A case has a `kind` and a `payload`, and this
module does not know what a price is: P2 will put invoices in the same queue
without a migration.
"""
