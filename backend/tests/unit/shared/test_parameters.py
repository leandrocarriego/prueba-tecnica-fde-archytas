"""The catalog of business parameters holds together on its own.

Nothing here touches the database: the catalog is a declaration, and what can
go wrong with a declaration is that it contradicts itself — a duplicated key, a
starting value outside the range it declares, a bound that means nothing for
the kind of value it holds. Every one of those would only show up on the
owner's screen, at the worst possible moment.
"""

from decimal import Decimal

import pytest

from app.shared.errors import ValidationError
from app.shared.parameters import (
    PARAMETERS,
    ParameterKind,
    ParameterSpec,
    initial_value,
    spec_for,
)

NUMERIC_KINDS = (ParameterKind.INTEGER, ParameterKind.DECIMAL)


@pytest.mark.unit
class TestTheCatalogIsConsistent:
    """What the declaration promises about itself."""

    def test_keys_are_unique(self) -> None:
        """Two specs under one key would make the second unreachable."""
        # Arrange
        keys = [spec.key for spec in PARAMETERS]

        # Assert
        assert len(keys) == len(set(keys))

    def test_the_catalog_is_not_empty(self) -> None:
        """Guard against a check that passes because it walked nothing."""
        assert PARAMETERS

    @pytest.mark.parametrize("spec", PARAMETERS, ids=lambda spec: spec.key)
    def test_the_initial_value_is_inside_its_own_range(self, spec: ParameterSpec) -> None:
        """A starting value the owner could not have typed is a contradiction (RF-04, RF-06)."""
        # Act — coercing the initial value is exactly what a PUT of it would do
        stored = spec.coerce(spec.initial)

        # Assert
        assert stored is not None

    @pytest.mark.parametrize("spec", PARAMETERS, ids=lambda spec: spec.key)
    def test_a_numeric_parameter_declares_both_bounds(self, spec: ParameterSpec) -> None:
        """RF-06 promises the rejection says between which values it has to be."""
        if spec.kind not in NUMERIC_KINDS:
            pytest.skip("a time of day is bounded by the clock, not by a pair of numbers")

        # Assert
        assert spec.minimum is not None
        assert spec.maximum is not None
        assert spec.minimum <= spec.maximum

    @pytest.mark.parametrize("spec", PARAMETERS, ids=lambda spec: spec.key)
    def test_the_owner_reads_a_label_and_an_effect(self, spec: ParameterSpec) -> None:
        """RF-05: next to every parameter, one sentence saying what changes."""
        # Assert
        assert spec.label.strip()
        assert spec.effect.strip()


@pytest.mark.unit
class TestReadingTheCatalog:
    """Looking a parameter up, and being told when it is not one."""

    def test_an_unknown_key_is_refused(self) -> None:
        """The list is closed: a key that is not declared cannot be written (RF-06)."""
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            spec_for("portal.password")

        assert "portal.password" in refusal.value.message

    def test_the_initial_value_comes_from_the_declaration(self) -> None:
        """RF-04: the value in force before anybody touched anything."""
        # Assert
        assert initial_value("price_update.interval_hours") == 12


@pytest.mark.unit
class TestCoercingAValue:
    """What the owner may type, and what is refused with the range in the message."""

    @pytest.fixture
    def interval(self) -> ParameterSpec:
        return spec_for("price_update.interval_hours")

    @pytest.fixture
    def threshold(self) -> ParameterSpec:
        return spec_for("price_update.highlight_threshold_pct")

    @pytest.fixture
    def digest_time(self) -> ParameterSpec:
        return spec_for("daily_digest.time")

    def test_a_whole_number_is_stored_as_one(self, interval: ParameterSpec) -> None:
        # Act
        stored = interval.coerce("24")

        # Assert
        assert stored == 24

    def test_both_ends_of_the_range_are_admitted(self, interval: ParameterSpec) -> None:
        """The bounds are inclusive: 1 hour and 168 hours are both legal."""
        # Assert
        assert interval.coerce(1) == 1
        assert interval.coerce(168) == 168

    @pytest.mark.parametrize("value", [0, 169])
    def test_a_value_outside_the_range_is_refused(
        self, interval: ParameterSpec, value: int
    ) -> None:
        """RF-06, with the criterion's own example: a frequency of zero."""
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            interval.coerce(value)

        # The message says between which values it has to be, not only that it failed.
        assert "1" in refusal.value.message
        assert "168" in refusal.value.message

    def test_a_decimal_keeps_its_cents(self, threshold: ParameterSpec) -> None:
        """Stored as text so JSONB does not turn it into a float."""
        # Act
        stored = threshold.coerce(Decimal("12.50"))

        # Assert
        assert stored == "12.50"

    def test_a_word_is_not_a_number(self, interval: ParameterSpec) -> None:
        # Act / Assert
        with pytest.raises(ValidationError):
            interval.coerce("cada tanto")

    def test_a_fraction_is_not_a_whole_number(self, interval: ParameterSpec) -> None:
        """Half an hour of interval is not a value this parameter can hold."""
        # Act / Assert
        with pytest.raises(ValidationError):
            interval.coerce("12.5")

    def test_a_time_of_day_is_normalised(self, digest_time: ParameterSpec) -> None:
        # Act
        stored = digest_time.coerce("8:05")

        # Assert
        assert stored == "08:05"

    @pytest.mark.parametrize("value", ["24:00", "08:60", "ocho", "8", "08:5"])
    def test_a_time_that_is_not_on_the_clock_is_refused(
        self, digest_time: ParameterSpec, value: str
    ) -> None:
        # Act / Assert
        with pytest.raises(ValidationError):
            digest_time.coerce(value)
