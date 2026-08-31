"""What each role may reach, and whether they may change it.

This is a constant and not a table on purpose. The signed spec fixes three
roles and says there is no screen where the owner builds a new one, so a table
would be configurability nobody asked for — and a badly edited row would open
a section. Code, reviewed and typed, is the cheaper place for a rule that is
not meant to move.

The map is **complete**: every section has an entry for every role. A section
added without deciding its permission fails the test that walks the whole
product of roles and sections, instead of silently defaulting to something.
"""

import enum


class Section(enum.StrEnum):
    """The parts of the business a person can be let into."""

    PRICES = "PRICES"
    CALENDAR = "CALENDAR"
    SUPPLIERS = "SUPPLIERS"
    PURCHASE_INVOICES = "PURCHASE_INVOICES"
    PAYMENTS = "PAYMENTS"
    PURCHASE_ORDERS = "PURCHASE_ORDERS"
    RECEIPTS = "RECEIPTS"
    SUPPLIER_MESSAGES = "SUPPLIER_MESSAGES"
    SALES = "SALES"
    DASHBOARD = "DASHBOARD"
    STOCK = "STOCK"
    PRODUCT_CATEGORIES = "PRODUCT_CATEGORIES"
    PRODUCT_CATALOG = "PRODUCT_CATALOG"
    ACCESS_ADMIN = "ACCESS_ADMIN"
    ACCESS_LOG = "ACCESS_LOG"
    SYSTEM_PARAMETERS = "SYSTEM_PARAMETERS"
    MANUAL_CORRECTIONS = "MANUAL_CORRECTIONS"


class Level(enum.IntEnum):
    """How far into a section a role gets.

    Ordered, not a set of flags: whoever may edit may also read, so
    `require_section(x, READ)` admits somebody holding `WRITE`.
    """

    NONE = 0
    READ = 1
    WRITE = 2


_OWNER = "OWNER"
_PURCHASING = "PURCHASING"
_SALES = "SALES"

# Reading guide, from the spec:
#   RF-08 the owner reaches everything · RF-09 purchasing sees no sales or
#   dashboard · RF-10 sales sees no suppliers, purchase invoices or payments ·
#   RF-11 the three consult prices · RF-34 sales consults the calendar without
#   editing it · RF-35 only the owner and purchasing act on prices ·
#   RF-24 and RF-31 the access screens are the owner's alone.
#
# `SUPPLIER_MESSAGES` is the portal inbox that 007 empties. It sits with the
# rest of purchasing because that is who answers a supplier's claim, and sales
# is kept out of it by RF-46 of that spec.
#
# Nobody *edits* a dashboard, so it has no write level for anyone.
#
# `PRODUCT_CATEGORIES` is the one row of this table the 002 got wrong, and the
# **010** corrects it: the rubros are maintained by whoever buys, not by whoever
# sells. A rubro is the category something is bought under — the owner buys a
# pair of pliers to resell, and it is Herramientas from the moment it is bought
# — so the person who sees it arrive is the one in a position to say which rubro
# it belongs to. Sales keeps `READ`, the same deal it already has with list
# prices and with the calendar: it sells from that catalog and needs to know
# where each product falls.
#
# **The catalog did not move with it**, and that is deliberate: `PRODUCT_CATALOG`
# stays with sales. It is the first time the two are separated, and the 010 says
# so out loud.
#
# `MANUAL_CORRECTIONS` is the odd one out, and worth a sentence. Making a
# correction is authorised by the section the datum belongs to — the catalog
# for a price, purchase invoices for an invoice — because that is what RF-24 of
# 003 says. **Undoing** one is the owner's alone, whatever the datum, and that
# is a different question from who may reach any single section. So it gets its
# own entry rather than borrowing a section whose name would be a lie.
MATRIX: dict[Section, dict[str, Level]] = {
    Section.PRICES: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.READ},
    Section.CALENDAR: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.READ},
    Section.SUPPLIERS: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.NONE},
    Section.PURCHASE_INVOICES: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.NONE},
    Section.PAYMENTS: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.NONE},
    Section.PURCHASE_ORDERS: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.NONE},
    Section.RECEIPTS: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.NONE},
    Section.SUPPLIER_MESSAGES: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.NONE},
    Section.SALES: {_OWNER: Level.WRITE, _PURCHASING: Level.NONE, _SALES: Level.WRITE},
    Section.DASHBOARD: {_OWNER: Level.READ, _PURCHASING: Level.NONE, _SALES: Level.READ},
    Section.STOCK: {_OWNER: Level.WRITE, _PURCHASING: Level.NONE, _SALES: Level.WRITE},
    Section.PRODUCT_CATEGORIES: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.READ},
    Section.PRODUCT_CATALOG: {_OWNER: Level.WRITE, _PURCHASING: Level.NONE, _SALES: Level.WRITE},
    Section.ACCESS_ADMIN: {_OWNER: Level.WRITE, _PURCHASING: Level.NONE, _SALES: Level.NONE},
    Section.ACCESS_LOG: {_OWNER: Level.READ, _PURCHASING: Level.NONE, _SALES: Level.NONE},
    Section.SYSTEM_PARAMETERS: {_OWNER: Level.WRITE, _PURCHASING: Level.NONE, _SALES: Level.NONE},
    Section.MANUAL_CORRECTIONS: {
        _OWNER: Level.WRITE,
        _PURCHASING: Level.NONE,
        _SALES: Level.NONE,
    },
}


def level_for(role: str, section: Section) -> Level:
    """Return how far this role gets into this section."""
    return MATRIX[section].get(role, Level.NONE)


def permissions_for(role: str) -> dict[Section, Level]:
    """Return the whole map for one role, which is what draws their menu."""
    return {section: level_for(role, section) for section in Section}
