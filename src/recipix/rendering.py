"""
Recipix Part 2 rendering — cookbook-style output for evaluated recipes.

Owner:   Berk Hakan Öge (210104004132)
Plan:    Implements plan §2.4 — Mass: g/kg at 1000; Volume: ml/l at 1000;
         Duration: min/hr at 60; Count and Temperature shown as-is.
"""

from __future__ import annotations

from .runtime_values import RtIngredient, RtPinch, RtQuantity, RtRecipe


def render_quantity(q: RtQuantity) -> str:
    """Plan §2.4 unit-promotion heuristic."""
    v = q.value
    if q.dimension == "Mass":
        if abs(v) < 1000:
            return f"{_fmt(v)} g"
        return f"{_fmt(v / 1000)} kg"
    if q.dimension == "Volume":
        if abs(v) < 1000:
            return f"{_fmt(v)} ml"
        return f"{_fmt(v / 1000)} l"
    if q.dimension == "Duration":
        if abs(v) < 60:
            return f"{_fmt(v)} min"
        return f"{_fmt(v / 60)} hr"
    if q.dimension == "Count":
        return _fmt(v)
    if q.dimension == "Temperature":
        return f"{_fmt(v)} °C"
    return f"{_fmt(v)} ?{q.dimension}"


def _fmt(v) -> str:
    if isinstance(v, int):
        return str(v)
    if v == int(v):
        return str(int(v))
    # Trim trailing zeros to avoid 1.50 -> "1.50"; keep 1.5
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def _render_ingredient_value(rti: RtIngredient) -> str:
    if isinstance(rti.quantity, RtPinch):
        return "a pinch"
    return render_quantity(rti.quantity)


def _render_action_arg(arg, recipe: RtRecipe) -> str:
    tag, payload = arg
    if tag == "ingredient_ref":
        ing = recipe.ingredients.get(payload)
        if ing is None:
            return payload
        return ing.name
    # value
    v = payload
    if isinstance(v, RtIngredient):
        return v.name
    if isinstance(v, RtQuantity):
        return render_quantity(v)
    if isinstance(v, RtPinch):
        return "a pinch"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return _fmt(v)
    if isinstance(v, str):
        return v
    return repr(v)


def render_recipe(r: RtRecipe) -> str:
    lines: list[str] = []
    lines.append(f"{r.name} — serves {r.servings}")
    lines.append("")
    lines.append("Ingredients:")
    for key, ing in r.ingredients.items():
        lines.append(f"  {ing.name}: {_render_ingredient_value(ing)}")
    lines.append("")
    lines.append("Steps:")
    for idx, step in enumerate(r.steps, start=1):
        modifiers: list[str] = []
        if step["at"] is not None:
            modifiers.append(f"at {render_quantity(step['at'])}")
        if step["for"] is not None:
            modifiers.append(f"for {render_quantity(step['for'])}")
        suffix = (" " + " ".join(modifiers)) if modifiers else ""
        lines.append(f"  {idx}. {step['description']}{suffix}")
        for verb, args in step["actions"]:
            rendered = ", ".join(_render_action_arg(a, r) for a in args)
            if rendered:
                lines.append(f"     - {verb}({rendered})")
            else:
                lines.append(f"     - {verb}()")
    return "\n".join(lines)


__all__ = ["render_recipe", "render_quantity"]
