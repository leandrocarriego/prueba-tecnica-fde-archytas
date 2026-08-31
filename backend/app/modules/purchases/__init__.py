"""Purchases: the supplier register, the invoices, what was paid and what is due.

One module and not three, and the spec is what says so: suppliers and invoices
are "el mismo problema mirado desde dos lados". Splitting them would force one
side to keep a projection of the other — the cost Artículo IV tells us to
accept — just to list the invoices of a supplier, which is the central screen
of the feature. When respecting a boundary hurts like that, the boundary is in
the wrong place, and the constitution says to move the boundary.
"""
