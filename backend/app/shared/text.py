"""Text normalisation used by entity resolution and deduplication.

Supplier names, product keys and document numbers arrive from the portal with
inconsistent casing, accents, punctuation and legal suffixes. Normalising them
in one place keeps matching decisions reproducible and testable.
"""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)

# Legal forms and connecting words carry no identity: "Aceros del Sur S.A." and
# "aceros sur srl" are the same company.
LEGAL_SUFFIXES = frozenset({"sa", "srl", "sas", "sh", "sca", "scs", "ltda", "sl", "inc"})
STOP_WORDS = frozenset({"de", "del", "la", "las", "el", "los", "y"})


def strip_accents(value: str) -> str:
    """Return the string without diacritics."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize(value: str) -> str:
    """Lowercase, strip accents and punctuation, and collapse whitespace."""
    cleaned = _PUNCTUATION.sub(" ", strip_accents(value).lower())
    return _WHITESPACE.sub(" ", cleaned).strip()


def only_digits(value: str) -> str:
    """A tax id with its punctuation taken out.

    `30-70918273-4` and `30709182734` are the same number written twice, and
    which of the two gets printed depends on who typed it. Every comparison of
    two tax ids goes through here so that the answer never depends on the
    formatting — the SQL side of the same rule is `_only_digits` in the
    purchases repository, which strips the same two characters in the database.
    """
    return "".join(character for character in value if character.isdigit())


def _merge_initials(tokens: list[str]) -> list[str]:
    """Join runs of single letters back into the word they abbreviate.

    `normalize` turns punctuation into whitespace, so "S.A." and "S. A." arrive
    here as two separate one-letter tokens. Without this step they would never
    match `LEGAL_SUFFIXES`, and "Aceros del Sur S.A." would not resolve to the
    same company as "Aceros Sur SRL" — which is precisely the case the portal
    produces, since it writes both spellings for the same supplier.
    """
    merged: list[str] = []
    run: list[str] = []
    for token in tokens:
        if len(token) == 1:
            run.append(token)
            continue
        if run:
            merged.append("".join(run))
            run = []
        merged.append(token)
    if run:
        merged.append("".join(run))
    return merged


def normalize_entity_name(value: str) -> str:
    """Normalise a company name down to its identifying tokens.

    Drops legal forms and connecting words so that fuzzy matching compares the
    parts that actually identify the company.
    """
    tokens = _merge_initials(normalize(value).split())
    return " ".join(
        token for token in tokens if token not in LEGAL_SUFFIXES and token not in STOP_WORDS
    )


def collapse_written_form(value: str) -> str:
    """Collapse a written form down to the only differences that are not real.

    Deliberately dumb, and that is the feature: trim the ends, collapse inner
    whitespace, casefold. It does **not** strip accents, does not expand `/`
    into ` y `, and does not undo an abbreviation — so `ELECTRICIDAD` and
    `Electricidad` become one key, while `Ferreteria Gral.` and
    `Ferreteria General` stay two, each pointing at its rubro through the table
    of equivalences somebody signed.

    The temptation is to make it clever. A clever normaliser gets `Herram.`
    right and, some day, silently joins two rubros the business tells apart —
    an opinion hidden in code where Artículo II wants a person. Everything this
    function does not resolve goes to review, and that is the whole design.
    """
    return _WHITESPACE.sub(" ", value.strip()).casefold()
