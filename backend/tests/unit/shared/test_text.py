"""Unit tests for `app.shared.text`.

Entity resolution lives or dies on these functions: two spellings of the same
supplier must normalise to the same string, and two different suppliers must
not.
"""

import pytest

from app.shared.text import (
    LEGAL_SUFFIXES,
    STOP_WORDS,
    normalize,
    normalize_entity_name,
    strip_accents,
)


@pytest.mark.unit
class TestStripAccents:
    """Diacritics are dropped, the letters underneath are kept."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Ferretería", "Ferreteria"),
            ("Ñandú", "Nandu"),
            ("ÁÉÍÓÚ", "AEIOU"),
            ("Aceros", "Aceros"),
            ("", ""),
        ],
    )
    def test_strip_accents(self, value: str, expected: str) -> None:
        """Accented characters lose the accent and nothing else."""
        assert strip_accents(value) == expected

    def test_case_is_preserved(self) -> None:
        """Stripping accents is not lowercasing: `normalize` does that."""
        assert strip_accents("Metalúrgica SUR") == "Metalurgica SUR"


@pytest.mark.unit
class TestNormalize:
    """Lowercase, no accents, no punctuation, single spaces."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Metalúrgica Sur", "metalurgica sur"),
            ("  ACEROS   del   SUR  ", "aceros del sur"),
            ("Aceros, S.A.", "aceros s a"),
            ("Tornillos & Bulones", "tornillos bulones"),
            ("Perfil-L 40x40", "perfil l 40x40"),
            ("\tHierro\nRedondo\r", "hierro redondo"),
            ("", ""),
            ("   ", ""),
            ("...", ""),
        ],
    )
    def test_normalize(self, value: str, expected: str) -> None:
        """Casing, accents, punctuation and whitespace stop mattering."""
        assert normalize(value) == expected

    def test_normalize_is_idempotent(self) -> None:
        """Normalising an already normalised value changes nothing."""
        # Arrange
        once = normalize("  Ferretería Industrial, S.R.L.  ")

        # Act
        twice = normalize(once)

        # Assert
        assert twice == once

    def test_digits_and_underscores_survive(self) -> None:
        """Document numbers and product keys must not lose their characters."""
        assert normalize("FC_A 0001-00012345") == "fc_a 0001 00012345"


@pytest.mark.unit
class TestNormalizeEntityName:
    """Company names come down to the tokens that identify the company."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # Legal forms carry no identity.
            ("Aceros del Sur SA", "aceros sur"),
            ("ACEROS SUR SRL", "aceros sur"),
            ("Aceros Sur SAS", "aceros sur"),
            ("Aceros Sur LTDA", "aceros sur"),
            # Connecting words carry no identity either.
            ("Ferretería de la Costa", "ferreteria costa"),
            ("Hierros y Metales del Norte", "hierros metales norte"),
            # Accents are gone before the tokens are filtered.
            ("Metalúrgica Güemes SRL", "metalurgica guemes"),
            ("", ""),
        ],
    )
    def test_normalize_entity_name(self, value: str, expected: str) -> None:
        """The identifying tokens survive; the decoration does not."""
        assert normalize_entity_name(value) == expected

    def test_two_spellings_of_the_same_company_match(self) -> None:
        """Casing, accents and the legal form must not separate one company in two."""
        assert normalize_entity_name("Acerós del Sur SA") == normalize_entity_name("ACEROS SUR SRL")

    def test_different_companies_do_not_collapse(self) -> None:
        """Normalisation must not merge two suppliers that are genuinely different."""
        assert normalize_entity_name("Aceros del Sur SA") != normalize_entity_name(
            "Aceros del Norte SA"
        )

    def test_a_name_made_only_of_noise_normalises_to_nothing(self) -> None:
        """No identifying token left means an empty key, not a partial match."""
        assert normalize_entity_name("La de los y del SA") == ""

    def test_dotted_legal_suffix_is_dropped(self) -> None:
        """A dotted legal form must not identify a company any more than a bare one."""
        assert normalize_entity_name("Aceros del Sur S.A.") == normalize_entity_name(
            "aceros sur srl"
        )

    def test_every_configured_suffix_is_dropped(self) -> None:
        """Each entry of LEGAL_SUFFIXES disappears from the key."""
        for suffix in LEGAL_SUFFIXES:
            assert normalize_entity_name(f"Aceros Sur {suffix}") == "aceros sur"

    def test_every_configured_stop_word_is_dropped(self) -> None:
        """Each entry of STOP_WORDS disappears from the key."""
        for word in STOP_WORDS:
            assert normalize_entity_name(f"Aceros {word} Sur") == "aceros sur"
