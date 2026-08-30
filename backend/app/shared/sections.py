"""The sections of the business, as vocabulary nobody owns.

Three coarse areas, taken from the map of roles in the brief. They are not
`identity.permissions.Section`, which is finer and answers a different
question: that one says *which screen* a role reaches, this one says *what part
of the business a fact belongs to*. The name says `Business` for that reason
and for one more: two enums called `Section` make FastAPI fall back to
fully-qualified names for **both** in the OpenAPI document, which silently
renames a type the frontend already reads.

Why here and not inside a module: a manual change published as a domain event
carries the section it happened in, and an event lives in `shared/`
(`GEN-08`). If this enum lived in `identity`, `catalog` would have to import
`identity` to say "this correction is a sales fact", and `shared/` may not
import a module at all (`GEN-03`). So the vocabulary is shared and the
translation from a role to the sections it may read is `identity`'s alone —
`identity.dependencies.visible_sections()`, where the authorisation exception
already lives.
"""

import enum


class BusinessSection(enum.StrEnum):
    """The part of the business a fact belongs to."""

    # suppliers, purchase invoices, payments, orders, receipts, the calendar
    PURCHASING = "PURCHASING"
    # sales, prices, the product catalog, categories
    SALES = "SALES"
    # the parameters and the operation of the platform itself
    SYSTEM = "SYSTEM"
