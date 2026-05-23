"""
Runtime value representations for Recipix Part 2.

Owner:   Berk Hakan Öge (210104004132), drafts; İsmail Kabak (1901042652) reviews.
Status:  Joint module — both type checker and interpreter import from here.
Plan:    Implements plan §2.2 (runtime value shapes), §2.4 (normalization
         location: lives in the interpreter, fed by ``normalize_to_base``
         here). The base-unit convention table and the spec §3 conversion
         factors are encoded in this file as the single source of truth.

Summary
-------
This module is **pure data**: dataclasses for runtime values and a
single ``normalize_to_base`` function that converts a (value, unit)
pair into the dimension's base unit. No statement evaluation, no
environment, no rendering — those live in ``interpreter.py`` and
``rendering.py``. Both the interpreter and the type checker can
import this module without pulling in either of those concerns.

Primitives ``int``, ``float``, ``bool`` use Python natives directly;
they have no wrapper dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


# ---------------------------------------------------------------------------
# Base-unit convention (plan §2.2, locked at Phase 0)
# ---------------------------------------------------------------------------

BASE_UNIT: dict[str, str] = {
    "Mass":         "g",
    "Volume":       "ml",
    "Count":        "count",
    "Temperature":  "°C",
    "Duration":     "min",
}

# ---------------------------------------------------------------------------
# Conversion factors (spec §3, "Conversion factors" table)
#
# Each entry maps a surface unit string to (factor, dimension), where
# ``factor`` is the multiplier needed to convert from the surface unit
# to the dimension's base unit (e.g. 1 kg = 1000 g, so kg→g factor is
# 1000). The base unit itself is included with factor 1.0.
# ---------------------------------------------------------------------------

UNIT_TABLE: dict[str, tuple[float, str]] = {
    # Mass — base: g
    "g":     (1.0,     "Mass"),
    "kg":    (1000.0,  "Mass"),
    "mg":    (0.001,   "Mass"),

    # Volume — base: ml
    "ml":    (1.0,     "Volume"),
    "l":     (1000.0,  "Volume"),
    "tsp":   (5.0,     "Volume"),
    "tbsp":  (15.0,    "Volume"),
    "cup":   (240.0,   "Volume"),

    # Count — base: count (no conversions)
    "count": (1.0,     "Count"),

    # Temperature — base: °C (no conversions; °C is the only unit)
    "°C":    (1.0,     "Temperature"),

    # Duration — base: min
    "min":   (1.0,     "Duration"),
    "hr":    (60.0,    "Duration"),
}


def normalize_to_base(value: float, unit: str) -> tuple[float, str]:
    """
    Convert ``(value, unit)`` to the dimension's base unit.

    Returns ``(base_value, dimension)``. Raises ``ValueError`` for any
    unit string not in :data:`UNIT_TABLE`. ``pinch`` is intentionally
    excluded — it is a sentinel, not a quantity, and is handled by
    callers via :data:`PINCH` instead of by going through this function.
    """
    try:
        factor, dimension = UNIT_TABLE[unit]
    except KeyError:
        raise ValueError(f"unknown unit: {unit!r}") from None
    return value * factor, dimension


# ---------------------------------------------------------------------------
# Runtime values
# ---------------------------------------------------------------------------

@dataclass
class RtQuantity:
    """A dimensioned numeric value, always carried in the dimension's base unit."""
    value: float
    dimension: str       # one of BASE_UNIT.keys()


class RtPinch:
    """Singleton sentinel for ``pinch`` ingredients. No fields, ceremonial."""
    __slots__ = ()

    def __repr__(self) -> str:
        return "PINCH"

    def __eq__(self, other) -> bool:
        return isinstance(other, RtPinch)

    def __hash__(self) -> int:
        return hash("RtPinch")


PINCH = RtPinch()


@dataclass
class RtIngredient:
    """A named ingredient binding with a quantity (or :data:`PINCH`)."""
    name: str
    quantity: Union[RtQuantity, RtPinch]


@dataclass
class RtRecipe:
    """
    An evaluated recipe — the value an ``evaluate`` statement produces
    when applied to a recipe call.

    ``servings`` is locked at recipe-instantiation time per plan §2.6
    (the ``serves`` expression is evaluated once during ``RecipeCall``,
    not per ingredient).

    ``steps`` holds the AST nodes for lazy rendering — the interpreter
    does not evaluate step bodies at recipe instantiation; rendering
    walks them.

    ``step_decls``, ``serves_decl``, ``captured_params`` are stored so
    that ``scale`` can re-execute step bodies with an updated environment.
    """
    name: str
    servings: int
    ingredients: dict[str, RtIngredient] = field(default_factory=dict)
    steps: list = field(default_factory=list)
    step_decls: list = field(default_factory=list)
    serves_decl: object = None
    captured_params: dict = field(default_factory=dict)


@dataclass
class RtList:
    """A homogeneous list value carrying its element type for runtime checks."""
    elements: list
    element_type: str
