"""The catalog of business parameters: what the owner may change, and within what.

A declaration, not a table. `operations.parameter` stores **only the values the
owner changed**; everything else about a parameter — that it exists, what it
starts at, how far it may move, what sentence the owner reads next to it —
lives here, frozen, in code.

Three consequences the design is built on:

* **A parameter nobody touched still has a value** (RF-04). It is `initial`,
  read from here, so a fresh installation behaves like a configured one.
* **A key that is not here cannot be written** (RF-06). The list is closed,
  which is also what keeps a credential from ever entering as a parameter over
  the API (Artículo VII).
* **The screen is drawn from here** (RF-01, RF-05): the backend validates the
  range, so the range and the sentence beside it come from the same place. A
  second copy in the browser would be a second rule.

It lives in `shared/` for the same reason the event catalog does: it is shared
vocabulary, every feature adds its line, and no module owns it.
"""

import enum
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.shared.errors import ValidationError

TIME_OF_DAY_FORMAT = "HH:MM"
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24


class ParameterKind(enum.StrEnum):
    """What kind of value a parameter holds, and therefore how it is checked."""

    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    TIME_OF_DAY = "TIME_OF_DAY"


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """One parameter: its identity, its bounds and what the owner reads.

    `label` and `effect` are in Spanish because a person reads them on the
    settings screen (Artículo VIII); everything else is code.

    `consumed_by` names the functionality that actually reads the value, and is
    empty while nothing does. The screen shows that plainly instead of offering
    a knob that moves nothing: five of these are waiting for the feature that
    will read them, and a panel that hid the difference would be lying.
    """

    key: str
    label: str
    effect: str
    kind: ParameterKind
    initial: Any
    minimum: Any | None = None
    maximum: Any | None = None
    unit: str | None = None
    consumed_by: str = ""

    @property
    def has_effect(self) -> bool:
        """Whether some built functionality reads this value today."""
        return bool(self.consumed_by)

    @property
    def stored_initial(self) -> Any:
        """The starting value in the shape the database and the API carry it.

        `initial` is written in the type that reads best in code — a `Decimal`
        for a percentage — and JSONB does not take one. Coercing it is exactly
        what a `PUT` of the same value would do, so the two can never disagree.
        """
        return self.coerce(self.initial)

    @property
    def range_text(self) -> str:
        """The admitted range, in the sentence the owner is shown (RF-06)."""
        if self.kind is ParameterKind.TIME_OF_DAY:
            return "una hora del día entre 00:00 y 23:59"
        return f"un valor entre {self.minimum} y {self.maximum}"

    def coerce(self, value: Any) -> Any:
        """Return the value to store, or say why it cannot be stored.

        Coercion and range live together on purpose: RF-06 asks the system to
        reject the change *and* say between which values it has to be, and a
        message written anywhere else drifts from the bound it describes.
        """
        if self.kind is ParameterKind.TIME_OF_DAY:
            return self._as_time_of_day(value)
        number = self._as_number(value)
        if (self.minimum is not None and number < self.minimum) or (
            self.maximum is not None and number > self.maximum
        ):
            raise ValidationError(
                f"«{self.label}» tiene que ser {self.range_text}.",
                details={
                    "key": self.key,
                    "minimum": str(self.minimum),
                    "maximum": str(self.maximum),
                },
            )
        # A decimal travels to JSONB as text so it does not become a float on
        # the way in and lose the cents on the way out.
        return int(number) if self.kind is ParameterKind.INTEGER else str(number)

    def _as_number(self, value: Any) -> Decimal:
        """Read the value as the number this parameter holds."""
        try:
            number = Decimal(str(value).strip())
        except (InvalidOperation, ArithmeticError, AttributeError, TypeError) as error:
            raise self._not_a_number_error() from error
        # `nan`, `snan` and `infinity` spell themselves as a Decimal without
        # complaining and only detonate later: the range check compares them
        # with `<`, which signals `InvalidOperation` outside any guard. They are
        # refused right here, beside the text that never parsed, because no kind
        # of parameter can hold a value that is not a finite number — left to
        # the integer check below they would be refused for INTEGER only.
        if not number.is_finite():
            raise self._not_a_number_error()
        if self.kind is ParameterKind.INTEGER and number != number.to_integral_value():
            raise ValidationError(
                f"«{self.label}» tiene que ser un número entero.", details={"key": self.key}
            )
        return number

    def _not_a_number_error(self) -> ValidationError:
        """Build the refusal for a value that is no number at all.

        It returns the error instead of raising it because two paths reach it —
        the text that never parsed and the text that parsed into something not
        finite — and each wants its own `from`.
        """
        return ValidationError(
            f"«{self.label}» tiene que ser un número.", details={"key": self.key}
        )

    def _as_time_of_day(self, value: Any) -> str:
        """Read the value as `HH:MM`, which is how a time of day is stored."""
        text = str(value).strip()
        hours, _, minutes = text.partition(":")
        if (
            not hours.isdigit()
            or not minutes.isdigit()
            or len(minutes) != 2
            or int(hours) >= HOURS_PER_DAY
            or int(minutes) >= MINUTES_PER_HOUR
        ):
            raise ValidationError(
                f"«{self.label}» tiene que ser {self.range_text}, con el formato "
                f"{TIME_OF_DAY_FORMAT}.",
                details={"key": self.key},
            )
        return f"{int(hours):02d}:{int(minutes):02d}"


# The parameters the business has identified. Adding one is a line here plus
# the feature that reads it — never a migration, and never a second screen.
#
# `access.session_idle_minutes` is the one key that was already in use before
# this catalog existed: `identity` reads it, and it keeps its name so the
# parameter the owner moves is the parameter the platform obeys.
PARAMETERS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        key="price_update.interval_hours",
        label="Cada cuántas horas se consulta el portal",
        effect="Cambia cada cuánto el sistema le pide la lista de precios al proveedor.",
        kind=ParameterKind.INTEGER,
        initial=12,
        minimum=1,
        maximum=168,
        unit="horas",
        consumed_by="catalog",
    ),
    ParameterSpec(
        key="price_update.highlight_threshold_pct",
        label="Porcentaje de suba a partir del cual se destaca un precio",
        effect="Cambia a partir de qué suba un producto aparece destacado en la lista de precios.",
        kind=ParameterKind.DECIMAL,
        initial=Decimal("10"),
        minimum=Decimal("0"),
        maximum=Decimal("1000"),
        unit="%",
        consumed_by="catalog",
    ),
    ParameterSpec(
        key="access.session_idle_minutes",
        label="Minutos sin uso después de los cuales se cierra la sesión",
        effect="Cambia cuánto puede quedar abierta una pantalla sin usarse antes de pedir la clave "
        "de nuevo.",
        kind=ParameterKind.INTEGER,
        initial=60,
        minimum=5,
        maximum=1440,
        unit="minutos",
        consumed_by="identity",
    ),
    ParameterSpec(
        key="due_date.notice_days",
        label="Días de anticipación con que se avisa un vencimiento",
        effect="Cambia con cuántos días de anticipación el sistema avisa que algo vence.",
        kind=ParameterKind.INTEGER,
        initial=3,
        minimum=0,
        maximum=90,
        unit="días",
    ),
    ParameterSpec(
        key="purchase_order.stalled_days",
        label="Días a partir de los cuales una orden de compra está estancada",
        effect="Cambia a los cuántos días una orden que no avanzó se considera estancada.",
        kind=ParameterKind.INTEGER,
        initial=15,
        minimum=1,
        maximum=365,
        unit="días",
    ),
    ParameterSpec(
        key="receipt.notice_days",
        label="Días de anticipación con que se avisa una factura sin recibo",
        effect="Cambia con cuántos días de anticipación se avisa una factura que sigue sin recibo.",
        kind=ParameterKind.INTEGER,
        initial=3,
        minimum=0,
        maximum=90,
        unit="días",
    ),
    ParameterSpec(
        key="daily_digest.time",
        label="Hora a la que sale el resumen diario de avisos",
        effect="Cambia a qué hora del día el sistema manda el resumen de lo que pasó.",
        kind=ParameterKind.TIME_OF_DAY,
        initial="08:00",
    ),
)

BY_KEY: dict[str, ParameterSpec] = {spec.key: spec for spec in PARAMETERS}


def spec_for(key: str) -> ParameterSpec:
    """Return the declaration of a parameter, or refuse the key.

    The refusal is a `ValidationError` and not a `NotFoundError` on purpose:
    from the caller's side this is a body that names something that is not a
    parameter, not a resource that went missing.
    """
    spec = BY_KEY.get(key)
    if spec is None:
        raise ValidationError(
            f"«{key}» no es un parámetro del sistema.",
            details={"key": key, "known": sorted(BY_KEY)},
        )
    return spec


def initial_value(key: str) -> Any:
    """The value a parameter has while nobody has changed it (RF-04)."""
    return spec_for(key).initial
