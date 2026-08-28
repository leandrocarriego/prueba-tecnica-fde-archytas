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
