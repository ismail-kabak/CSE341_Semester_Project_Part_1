"""
Recipix Part 2 rendering — cookbook-style output for evaluated recipes.

Owner:   Berk Hakan Öge (210104004132)
Plan:    Implements plan §2.4 (rendering unit heuristic: ``g``→``kg`` at
         ≥1000, ``ml``→``l`` at ≥1000, ``min``→``hr`` at ≥60; ``count``
         and ``°C`` always shown as-is).

Summary
-------
Stateless helpers that walk an :class:`~recipix.runtime_values.RtRecipe`
and produce the human-readable string that an ``evaluate`` statement
prints. The rendering heuristic is intentionally simple — base-unit
numerics are kept for arithmetic correctness, but a 2500-gram ingredient
should print as ``2.5 kg``, not ``2500 g``. See plan §2.4 for the
unit-promotion thresholds.

The two public entry points are :func:`render_recipe` (top-level, for
``EvalStmt`` use) and :func:`render_quantity` (the unit-heuristic
helper, exported in case the interpreter wants to format quantities
elsewhere).
"""

from __future__ import annotations

from .runtime_values import RtRecipe, RtQuantity


def render_recipe(r: RtRecipe) -> str:
    """
    Produce a cookbook-style multi-line string for an evaluated recipe.

    Layout (subject to integration-day polish):

        <Recipe Name> — serves N

        Ingredients:
          <ingredient name>: <rendered quantity>
          ...

        Steps:
          1. <step description> [at <quantity>] [for <quantity>]
             <action verb> <args>
          ...

    Not yet implemented.
    """
    raise NotImplementedError("recipix.rendering.render_recipe is not implemented yet")


def render_quantity(q: RtQuantity) -> str:
    """
    Render a :class:`RtQuantity` using the plan §2.4 unit-promotion
    heuristic. The input value is in the dimension's base unit; this
    function may scale it back up for display.

    Heuristic (plan §2.4):
      - Mass:        value < 1000   → ``g``; else ``kg`` (value / 1000)
      - Volume:      value < 1000   → ``ml``; else ``l`` (value / 1000)
      - Duration:    value < 60     → ``min``; else ``hr`` (value / 60)
      - Count:       always shown as the bare number (no unit suffix)
      - Temperature: always shown as ``<value> °C``

    Not yet implemented.
    """
    raise NotImplementedError("recipix.rendering.render_quantity is not implemented yet")


__all__ = ["render_recipe", "render_quantity"]
