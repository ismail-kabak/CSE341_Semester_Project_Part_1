"""
Recipix interpreter tests — stdlib unittest only.

Covers:
  * Literals, identifiers, quantity-literal normalization.
  * Numeric and quantity arithmetic, comparisons, implicit projection.
  * Statements (let, if, repeat, foreach).
  * Function and recipe calls, ScaleCall and SubstituteCall semantics.
  * The five spec §10 runtime errors.
  * The locked scale-servings rounding rule (plan §2.6).
  * End-to-end golden output for sample1 and sample2.

The type checker is not used here — the interpreter is exercised on
parser-produced AST directly. Programs are deliberately written to
avoid AmbiguousCall (no nullary recipe/function calls); the few cases
where one matters are constructed manually.
"""

from __future__ import annotations

import os
import sys
import unittest

_here = os.path.dirname(__file__)
_project = os.path.dirname(_here)
_src = os.path.join(_project, "src")
for _p in (_src, _project):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lexer import Lexer
from recipix import ast_nodes as ast
from recipix.parser import parse
from recipix.interpreter import Interpreter, run
from recipix.errors import RuntimeRecipixError
from recipix.runtime_values import (
    PINCH,
    RtIngredient,
    RtList,
    RtPinch,
    RtQuantity,
    RtRecipe,
)


def _parse(source: str):
    program = parse(Lexer(source).tokenize())
    _resolve_ambiguous_calls(program)
    return program


def _resolve_ambiguous_calls(program) -> None:
    """Mini stand-in for İsmail's typechecker.

    Walks the parsed AST, builds a name→decl table for top-level
    recipes/functions, and rewrites every ``AmbiguousCall`` node into a
    ``RecipeCall`` (with empty kwargs) or a ``FunctionCall`` (with empty
    args). This is the minimum surface the interpreter needs after the
    plan §3 handoff. The interpreter itself refuses to dispatch raw
    ``AmbiguousCall`` so this rewrite is mandatory for any program with a
    zero-arg recipe/function call.
    """
    name_kind: dict[str, str] = {}
    for item in program.items:
        if isinstance(item, ast.RecipeDecl):
            name_kind[item.name] = "recipe"
        elif isinstance(item, ast.FunctionDecl):
            name_kind[item.name] = "function"

    def rewrite(value):
        if isinstance(value, ast.AmbiguousCall):
            kind = name_kind.get(value.name)
            if kind == "recipe":
                return ast.RecipeCall(name=value.name, kwargs=[], line=value.line)
            if kind == "function":
                return ast.FunctionCall(name=value.name, args=[], line=value.line)
            return value  # unresolved — interpreter will raise loudly
        if isinstance(value, list):
            for i, v in enumerate(value):
                value[i] = rewrite(v)
            return value
        if hasattr(value, "__dataclass_fields__"):
            for field_name in value.__dataclass_fields__:
                setattr(value, field_name, rewrite(getattr(value, field_name)))
            return value
        return value

    rewrite(program)


def _eval_expr(source: str):
    """Evaluate a single expression by wrapping it in an evaluate stmt.

    Only works for expressions whose value is renderable; for testing
    raw values, use _eval_expr_value instead.
    """
    program = _parse(f"evaluate {source}")
    return run(program)


def _eval_expr_value(source: str):
    """Evaluate an expression and return the raw runtime value."""
    program = _parse(f"evaluate {source}")
    # Hook into the interpreter so we capture the value pre-render.
    interp = Interpreter()
    for item in program.items:
        if isinstance(item, ast.RecipeDecl):
            interp.globals.define(item.name, item)
        elif isinstance(item, ast.FunctionDecl):
            interp.globals.define(item.name, item)
    eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
    return interp._eval(eval_stmt.expr, interp.globals)


# ---------------------------------------------------------------------------
# Literals + identifier + quantity normalization
# ---------------------------------------------------------------------------


class TestLiteralsAndQuantities(unittest.TestCase):

    def test_int_literal(self):
        self.assertEqual(_eval_expr_value("42"), 42)

    def test_float_literal(self):
        self.assertEqual(_eval_expr_value("3.14"), 3.14)

    def test_bool_literal(self):
        self.assertIs(_eval_expr_value("true"), True)
        self.assertIs(_eval_expr_value("false"), False)

    def test_quantity_mass_normalizes_kg_to_g(self):
        q = _eval_expr_value("1 kg")
        self.assertIsInstance(q, RtQuantity)
        self.assertEqual(q.value, 1000)
        self.assertEqual(q.dimension, "Mass")

    def test_quantity_volume_normalizes_l_to_ml(self):
        q = _eval_expr_value("2 l")
        self.assertEqual(q.value, 2000)
        self.assertEqual(q.dimension, "Volume")

    def test_quantity_duration_normalizes_hr_to_min(self):
        q = _eval_expr_value("2 hr")
        self.assertEqual(q.value, 120)
        self.assertEqual(q.dimension, "Duration")

    def test_quantity_pinch_is_singleton(self):
        v = _eval_expr_value("1 pinch")
        self.assertIs(v, PINCH)


# ---------------------------------------------------------------------------
# Numeric & quantity arithmetic
# ---------------------------------------------------------------------------


class TestArithmetic(unittest.TestCase):

    def test_int_addition(self):
        self.assertEqual(_eval_expr_value("2 + 3"), 5)

    def test_int_division_truncates_toward_zero(self):
        # spec §3: int / int — truncated toward zero.
        self.assertEqual(_eval_expr_value("7 / 2"), 3)

    def test_mixed_int_float_widens_to_float(self):
        result = _eval_expr_value("1 + 0.5")
        self.assertIsInstance(result, float)
        self.assertEqual(result, 1.5)

    def test_quantity_same_dimension_add_with_unit_conversion(self):
        # 200 g + 1 kg -> 1200 g (per spec §3 example)
        q = _eval_expr_value("200 g + 1 kg")
        self.assertEqual(q.value, 1200)
        self.assertEqual(q.dimension, "Mass")

    def test_quantity_scalar_multiplication_commutative(self):
        a = _eval_expr_value("200 g * 2")
        b = _eval_expr_value("2 * 200 g")
        self.assertEqual(a.value, 400)
        self.assertEqual(b.value, 400)
        self.assertEqual(a.dimension, b.dimension)

    def test_quantity_same_dim_division_yields_unitless(self):
        # 1 kg / 200 g -> 5  (spec §3 example)
        v = _eval_expr_value("1 kg / 200 g")
        self.assertEqual(v, 5)

    def test_unary_minus_on_quantity(self):
        q = _eval_expr_value("-200 g")
        self.assertEqual(q.value, -200)
        self.assertEqual(q.dimension, "Mass")

    def test_comparison_quantity_same_dim_with_unit_conv(self):
        self.assertTrue(_eval_expr_value("1 kg > 500 g"))
        self.assertFalse(_eval_expr_value("1 kg < 500 g"))
        self.assertTrue(_eval_expr_value("1000 g == 1 kg"))


class TestImplicitIngredientProjection(unittest.TestCase):
    """Decision #31 — Ingredient implicitly projects to its Quantity field
    in arithmetic, comparison, and substitution contexts. Spec §2:
    `flour + 100 g` is shorthand for `quantity_of(flour) + 100 g`.
    """

    def test_ingredient_plus_quantity_in_step_body(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient flour : 200 g
                step "x" {
                    // flour is an Ingredient; +100 g triggers the implicit
                    // projection. Result is a Mass.
                    let total : Mass = flour + 100 g
                    sprinkle(total)
                }
            }
            evaluate r()
        """)
        outs = run(program)
        # total = 200 g + 100 g = 300 g — rendered as the sprinkle arg
        self.assertIn("300 g", outs[0])

    def test_ingredient_comparison_via_projection(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient flour : 200 g
                ingredient salt  : 1 pinch
                step "x" {
                    // flour > 100 g implicitly projects flour to Mass.
                    if flour > 100 g { sprinkle(salt) } else { combine(flour) }
                }
            }
            evaluate r()
        """)
        outs = run(program)
        self.assertIn("sprinkle", outs[0])
        self.assertNotIn("combine", outs[0])

    def test_explicit_quantity_of_matches_implicit(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient flour : 200 g
                step "x" {
                    let a : Mass = flour + 100 g
                    let b : Mass = quantity_of(flour) + 100 g
                    if a == b { sprinkle(flour) } else { combine(flour) }
                }
            }
            evaluate r()
        """)
        outs = run(program)
        self.assertIn("sprinkle", outs[0])


# ---------------------------------------------------------------------------
# Function / recipe call basics
# ---------------------------------------------------------------------------


class TestFunctionCall(unittest.TestCase):

    def test_function_returns_value(self):
        program = _parse("""
            function half(n: int) -> int { return n / 2 }
            evaluate half(10)
        """)
        outputs = run(program)
        self.assertEqual(outputs, ["5"])

    def test_function_with_quantity_arg(self):
        program = _parse("""
            function double(q: Mass) -> Mass { return q * 2 }
            evaluate double(250 g)
        """)
        interp = Interpreter()
        for item in program.items:
            if isinstance(item, (ast.RecipeDecl, ast.FunctionDecl)):
                interp.globals.define(item.name, item)
        eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
        result = interp._eval(eval_stmt.expr, interp.globals)
        self.assertEqual(result.value, 500)


class TestRecipeCall(unittest.TestCase):

    SAMPLE1 = """
        function half(n: int) -> int { return n / 2 }

        recipe pancakes(servings: int) serves servings {
            ingredient flour : 50 g * servings
            ingredient milk  : 60 ml * servings
            ingredient eggs  : half(servings) * 1 count
            ingredient salt  : 1 pinch

            step "Mix dry" { combine(flour, salt) }
            step "Cook" at 180 °C for 3 min {
                pour(milk)
                flip()
            }
        }

        evaluate pancakes(servings: 4)
    """

    def test_sample1_recipe_instantiation(self):
        program = _parse(self.SAMPLE1)
        outputs = run(program)
        self.assertEqual(len(outputs), 1)
        text = outputs[0]
        self.assertIn("pancakes", text)
        self.assertIn("serves 4", text)
        self.assertIn("flour: 200 g", text)
        self.assertIn("milk: 240 ml", text)
        self.assertIn("eggs: 2", text)
        self.assertIn("salt: a pinch", text)
        self.assertIn("180", text)  # temperature shown
        self.assertIn("3 min", text)

    def test_serves_is_evaluated_once_at_instantiation(self):
        # If 'serves servings' were re-evaluated per ingredient, mutating
        # servings inside the body would break things. We don't allow that,
        # but we can verify the captured value matches the kwarg.
        program = _parse(self.SAMPLE1)
        interp = Interpreter()
        for item in program.items:
            if isinstance(item, (ast.RecipeDecl, ast.FunctionDecl)):
                interp.globals.define(item.name, item)
        eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
        rt = interp._eval(eval_stmt.expr, interp.globals)
        self.assertIsInstance(rt, RtRecipe)
        self.assertEqual(rt.servings, 4)


# ---------------------------------------------------------------------------
# Scale + Substitute
# ---------------------------------------------------------------------------


class TestScale(unittest.TestCase):

    BASE = """
        recipe r(s: int) serves s {
            ingredient flour : 100 g * s
            ingredient water : 200 ml * s
            ingredient salt  : 1 pinch
            step "x" at 180 °C for 5 min { pour(water) }
        }
    """

    def _scale(self, by_src):
        program = _parse(self.BASE + f"\nevaluate scale(r(s: 4), by: {by_src})")
        interp = Interpreter()
        for item in program.items:
            if isinstance(item, (ast.RecipeDecl, ast.FunctionDecl)):
                interp.globals.define(item.name, item)
        eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
        return interp._eval(eval_stmt.expr, interp.globals)

    def test_scale_mass_and_volume_but_not_temperature_duration(self):
        rt = self._scale("2")
        self.assertEqual(rt.ingredients["flour"].quantity.value, 800)  # 100*4*2
        self.assertEqual(rt.ingredients["water"].quantity.value, 1600)  # 200*4*2
        # Step at/for not scaled
        self.assertEqual(rt.steps[0]["at"].value, 180)
        self.assertEqual(rt.steps[0]["for"].value, 5)

    def test_scale_does_not_touch_pinch(self):
        rt = self._scale("3")
        self.assertIs(rt.ingredients["salt"].quantity, PINCH)

    def test_scale_servings_uses_bankers_rounding(self):
        # plan §2.6 locked: int(round(servings * by))
        # recipe-of-3 * 0.5 -> int(round(1.5)) = 2 (banker's: round-half-to-even)
        program = _parse("""
            recipe r(s: int) serves s {
                ingredient w : 1 ml
                step "x" { pour(w) }
            }
            evaluate scale(r(s: 3), by: 0.5)
        """)
        interp = Interpreter()
        for item in program.items:
            if isinstance(item, (ast.RecipeDecl, ast.FunctionDecl)):
                interp.globals.define(item.name, item)
        eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
        rt = interp._eval(eval_stmt.expr, interp.globals)
        self.assertEqual(rt.servings, 2)

    def test_scale_servings_two_thirds_rounds_to_two(self):
        # 3 * (2/3) = 2.0 exactly in float? Actually 2/3 is float; verify.
        program = _parse("""
            recipe r(s: int) serves s {
                ingredient w : 1 ml
                step "x" { pour(w) }
            }
            function third(n: int) -> float { return n / 3 }
            evaluate scale(r(s: 3), by: 0.6666666666666666)
        """)
        interp = Interpreter()
        for item in program.items:
            if isinstance(item, (ast.RecipeDecl, ast.FunctionDecl)):
                interp.globals.define(item.name, item)
        eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
        rt = interp._eval(eval_stmt.expr, interp.globals)
        self.assertEqual(rt.servings, 2)


class TestSubstitute(unittest.TestCase):

    SAMPLE2 = """
        recipe smoothie(s: int) serves s {
            ingredient milk     : 150 ml * s
            ingredient banana   : 1 count * s
            ingredient oat_milk : 150 ml * s
            step "Blend" for 1 min { combine(milk, banana) blend() }
        }
        evaluate substitute(smoothie(s: 2), milk, with: oat_milk, ratio: 1.0)
    """

    def test_substitute_rebinds_original_to_replacement(self):
        program = _parse(self.SAMPLE2)
        outputs = run(program)
        text = outputs[0]
        # After substitution the milk slot displays as oat_milk
        self.assertIn("oat_milk: 300 ml", text)
        # oat_milk binding is consumed — no separate oat_milk entry
        lines_oat = [ln for ln in text.splitlines() if "oat_milk" in ln]
        # one line in Ingredients section + (possibly) one in combine() args
        # but should only show ONE ingredient line
        ing_lines = [ln for ln in lines_oat if ln.lstrip().startswith("oat_milk:")]
        self.assertEqual(len(ing_lines), 1)

    def test_substitute_applies_ratio(self):
        program = _parse("""
            recipe r(s: int) serves s {
                ingredient flour : 200 g
                ingredient alt   : 100 g
                step "x" { combine(flour) }
            }
            evaluate substitute(r(s: 1), flour, with: alt, ratio: 0.5)
        """)
        interp = Interpreter()
        for item in program.items:
            if isinstance(item, (ast.RecipeDecl, ast.FunctionDecl)):
                interp.globals.define(item.name, item)
        eval_stmt = next(i for i in program.items if isinstance(i, ast.EvalStmt))
        rt = interp._eval(eval_stmt.expr, interp.globals)
        # new quantity = original_quantity * ratio = 200 g * 0.5 = 100 g
        self.assertEqual(rt.ingredients["flour"].quantity.value, 100)
        # display name is alt
        self.assertEqual(rt.ingredients["flour"].name, "alt")


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


class TestStatements(unittest.TestCase):

    def test_let_inside_function(self):
        program = _parse("""
            function f(n: int) -> int {
                let x : int = n + 1
                return x * 2
            }
            evaluate f(3)
        """)
        self.assertEqual(run(program), ["8"])

    def test_if_else(self):
        # Single-return rule (spec §7): function bodies must end with return.
        program = _parse("""
            function pick(b: bool) -> int {
                let x : int = 0
                if b { let x_then : int = 1 } else { let x_else : int = 2 }
                return x
            }
            evaluate pick(true)
        """)
        # Just verify the branch executed without error.
        outputs = run(program)
        self.assertEqual(outputs[0], "0")

    def test_if_branches_in_step_body(self):
        # if/else inside step bodies is more idiomatic for Recipix.
        program = _parse("""
            recipe r(s: int) serves s {
                ingredient w : 1 ml * s
                ingredient salt : 1 pinch
                step "x" {
                    if s > 1 { pour(w) } else { sprinkle(salt) }
                }
            }
            evaluate r(s: 2)
            evaluate r(s: 1)
        """)
        outs = run(program)
        self.assertIn("pour", outs[0])
        self.assertNotIn("pour", outs[1])
        self.assertIn("sprinkle", outs[1])

    def test_repeat_zero_is_noop(self):
        # No runtime error on repeat 0 times — just no iterations.
        program = _parse("""
            recipe r() serves 1 {
                ingredient x : 1 ml
                step "loop" {
                    repeat 0 times { pour(x) }
                }
            }
            evaluate r()
        """)
        outputs = run(program)
        # No "pour" line should appear in the output
        self.assertNotIn("pour", outputs[0])


# ---------------------------------------------------------------------------
# Runtime errors — one test per spec §10 runtime error + rounding rule
# ---------------------------------------------------------------------------


class TestRuntimeErrors(unittest.TestCase):

    def test_R1_division_by_zero(self):
        program = _parse("""
            function f(n: int) -> int { return n / 0 }
            evaluate f(5)
        """)
        with self.assertRaises(RuntimeRecipixError) as cm:
            run(program)
        self.assertIn("division by zero", str(cm.exception))

    def test_R2_negative_repeat_count(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient x : 1 ml
                step "loop" {
                    repeat -1 times { pour(x) }
                }
            }
            evaluate r()
        """)
        with self.assertRaises(RuntimeRecipixError) as cm:
            run(program)
        self.assertIn("negative repeat count", str(cm.exception))

    def test_R3_negative_scale_factor(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient x : 1 ml
                step "x" { pour(x) }
            }
            evaluate scale(r(), by: -1)
        """)
        with self.assertRaises(RuntimeRecipixError) as cm:
            run(program)
        self.assertIn(">", str(cm.exception))  # "> 0" in message

    def test_R3_zero_scale_factor(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient x : 1 ml
                step "x" { pour(x) }
            }
            evaluate scale(r(), by: 0)
        """)
        with self.assertRaises(RuntimeRecipixError):
            run(program)

    def test_R4_substitute_unknown_ingredient(self):
        # Substitute slots are bare IDENTs; the parser does not verify they
        # name real ingredients. The typechecker normally catches this as
        # error #14, but with a runtime-computed AST or absent typechecker
        # the slot can still name a non-existent binding — and the
        # interpreter must raise R4. See spec §10 runtime error #4.
        program = _parse("""
            recipe r() serves 1 {
                ingredient flour : 200 g
                ingredient alt   : 100 g
                step "x" { combine(flour) }
            }
            evaluate substitute(r(), bogus, with: alt, ratio: 1.0)
        """)
        with self.assertRaises(RuntimeRecipixError) as cm:
            run(program)
        msg = str(cm.exception)
        self.assertIn("substitute", msg)
        self.assertIn("bogus", msg)

    def test_R4_substitute_unknown_replacement(self):
        program = _parse("""
            recipe r() serves 1 {
                ingredient flour : 200 g
                ingredient alt   : 100 g
                step "x" { combine(flour) }
            }
            evaluate substitute(r(), flour, with: ghost, ratio: 1.0)
        """)
        with self.assertRaises(RuntimeRecipixError) as cm:
            run(program)
        self.assertIn("ghost", str(cm.exception))

    def test_R5_division_by_zero_in_quantity(self):
        program = _parse("""
            function f(q: Mass) -> float { return q / (0 g) }
            evaluate f(200 g)
        """)
        with self.assertRaises(RuntimeRecipixError) as cm:
            run(program)
        self.assertIn("division by zero", str(cm.exception))


# ---------------------------------------------------------------------------
# End-to-end golden output for the two D3 samples
# ---------------------------------------------------------------------------


class TestSampleGoldens(unittest.TestCase):

    def _load(self, name):
        path = os.path.join(_here, "fixtures", "valid", name)
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_sample1_renders_without_error(self):
        program = _parse(self._load("sample1.rcx"))
        outputs = run(program)
        self.assertEqual(len(outputs), 1)
        text = outputs[0]
        # scale(pancakes(servings: 4), by: 1.5) -> serves 6, scaled qts
        self.assertIn("serves 6", text)
        self.assertIn("300 g", text)  # 50 * 4 * 1.5
        self.assertIn("360 ml", text)  # 60 * 4 * 1.5
        self.assertIn("180", text)  # 180 °C unchanged
        self.assertIn("3 min", text)

    def test_sample2_renders_both_evals(self):
        program = _parse(self._load("sample2.rcx"))
        outputs = run(program)
        self.assertEqual(len(outputs), 2)
        # 1st: substituted smoothie (oat_milk replaces milk slot)
        self.assertIn("oat_milk: 300 ml", outputs[0])
        # 2nd: vanilla smoothie still has milk
        self.assertIn("milk: 300 ml", outputs[1])


if __name__ == "__main__":
    unittest.main()
