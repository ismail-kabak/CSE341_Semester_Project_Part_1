"""
Recipix parser tests — stdlib unittest only.

Run from the project root:
    python -m unittest discover tests

The lexer at src/lexer.py is used to tokenize fixtures; the parser under
test is at src/recipix/parser.py.
"""

import sys
import os
import unittest

# Make both src/ (for the lexer) and src/recipix (as a package parent)
# importable regardless of where the test runner is invoked.
_here    = os.path.dirname(__file__)
_project = os.path.dirname(_here)
_src     = os.path.join(_project, "src")

for _p in (_src, _project):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lexer import Lexer
from recipix.parser import parse
from recipix.errors import ParseError
from recipix.ast_nodes import (
    Program, RecipeDecl, FunctionDecl, EvalStmt,
    IngredientDecl, StepDecl,
    LetStmt, IfStmt, RepeatStmt, ForeachStmt, ReturnStmt, ActionStmt,
    BinaryOp, CompareOp, UnaryOp, QuantityOf, SubstituteCall, ScaleCall,
    FunctionCall, RecipeCall, KwArg,
    Identifier, IntLit, FloatLit, BoolLit, QuantityLit, ListLit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tokenize(src: str):
    return Lexer(src).tokenize()


def parse_src(src: str) -> Program:
    return parse(tokenize(src))


def fixture_path(subdir: str, name: str) -> str:
    return os.path.join(_here, "fixtures", subdir, name)


def parse_fixture(subdir: str, name: str) -> Program:
    with open(fixture_path(subdir, name), encoding="utf-8") as fh:
        src = fh.read()
    return parse_src(src)


def assert_parse_error(test: unittest.TestCase, src: str, *,
                       line: int | None = None, fragment: str | None = None):
    with test.assertRaises(ParseError) as ctx:
        parse_src(src)
    err = ctx.exception
    if line is not None:
        test.assertEqual(err.line, line,
                         f"expected error on line {line}, got line {err.line}: {err}")
    if fragment is not None:
        test.assertIn(fragment, str(err),
                      f"expected {fragment!r} in error message: {err}")
    return err


def assert_fixture_parse_error(test: unittest.TestCase, name: str, *,
                                line: int | None = None, fragment: str | None = None):
    with open(fixture_path("invalid", name), encoding="utf-8") as fh:
        src = fh.read()
    return assert_parse_error(test, src, line=line, fragment=fragment)


# ===========================================================================
# Valid fixture tests — spec §11 sample programs must parse without error
# ===========================================================================

class TestValidFixtures(unittest.TestCase):

    def test_sample1_parses(self):
        ast = parse_fixture("valid", "sample1.rcx")
        self.assertIsInstance(ast, Program)
        # Should have: FunctionDecl, RecipeDecl, EvalStmt
        self.assertEqual(len(ast.items), 3)
        self.assertIsInstance(ast.items[0], FunctionDecl)
        self.assertIsInstance(ast.items[1], RecipeDecl)
        self.assertIsInstance(ast.items[2], EvalStmt)

    def test_sample1_recipe_structure(self):
        ast = parse_fixture("valid", "sample1.rcx")
        recipe = ast.items[1]
        self.assertIsInstance(recipe, RecipeDecl)
        self.assertEqual(recipe.name, "pancakes")
        self.assertEqual(len(recipe.params), 1)
        self.assertEqual(recipe.params[0].name, "servings")
        self.assertEqual(len(recipe.ingredients), 4)
        self.assertEqual(len(recipe.steps), 3)

    def test_sample1_function_structure(self):
        ast = parse_fixture("valid", "sample1.rcx")
        fn = ast.items[0]
        self.assertIsInstance(fn, FunctionDecl)
        self.assertEqual(fn.name, "half")
        self.assertEqual(fn.return_type, "int")
        self.assertEqual(len(fn.params), 1)
        self.assertIsInstance(fn.body[-1], ReturnStmt)

    def test_sample1_eval_is_scale(self):
        ast = parse_fixture("valid", "sample1.rcx")
        ev = ast.items[2]
        self.assertIsInstance(ev, EvalStmt)
        self.assertIsInstance(ev.expr, ScaleCall)

    def test_sample1_step_modifiers(self):
        """Step 'Cook batches' has at=180°C and for=3min."""
        ast = parse_fixture("valid", "sample1.rcx")
        recipe = ast.items[1]
        cook_step = recipe.steps[2]
        self.assertIsInstance(cook_step, StepDecl)
        self.assertEqual(cook_step.description, "Cook batches")
        self.assertIsNotNone(cook_step.at_expr)
        self.assertIsNotNone(cook_step.for_expr)
        self.assertIsInstance(cook_step.at_expr, QuantityLit)
        self.assertEqual(cook_step.at_expr.unit, "°C")
        self.assertIsInstance(cook_step.for_expr, QuantityLit)
        self.assertEqual(cook_step.for_expr.unit, "min")

    def test_sample2_parses(self):
        ast = parse_fixture("valid", "sample2.rcx")
        self.assertIsInstance(ast, Program)
        # RecipeDecl + 2 EvalStmt
        self.assertEqual(len(ast.items), 3)
        self.assertIsInstance(ast.items[0], RecipeDecl)
        self.assertIsInstance(ast.items[1], EvalStmt)
        self.assertIsInstance(ast.items[2], EvalStmt)

    def test_sample2_substitute_call(self):
        ast = parse_fixture("valid", "sample2.rcx")
        ev = ast.items[1]
        self.assertIsInstance(ev.expr, SubstituteCall)
        sub = ev.expr
        # Decision #35: slots are bare strings, not Expr
        self.assertIsInstance(sub.original_name, str)
        self.assertIsInstance(sub.replacement_name, str)
        self.assertEqual(sub.original_name, "milk")
        self.assertEqual(sub.replacement_name, "oat_milk")

    def test_sample3_parses(self):
        """Sample 3 is grammatically valid; the type error is deferred to Part 2."""
        ast = parse_fixture("valid", "sample3.rcx")
        self.assertIsInstance(ast, Program)
        self.assertEqual(len(ast.items), 2)
        self.assertIsInstance(ast.items[0], RecipeDecl)
        self.assertIsInstance(ast.items[1], EvalStmt)

    def test_sample3_let_in_step(self):
        ast = parse_fixture("valid", "sample3.rcx")
        recipe = ast.items[0]
        step = recipe.steps[0]
        let = step.body[0]
        self.assertIsInstance(let, LetStmt)
        self.assertEqual(let.name, "total")
        self.assertEqual(let.type_name, "Mass")


# ===========================================================================
# Invalid fixture tests
# ===========================================================================

class TestInvalidFixtures(unittest.TestCase):

    def test_missing_brace_if(self):
        """if without braces is a parse error (Decision #20)."""
        assert_fixture_parse_error(self, "missing_brace_if.rcx",
                                   fragment="expected '{'")

    def test_wrong_modifier_order(self):
        """step 'for ... at ...' is a parse error (Decision #23)."""
        assert_fixture_parse_error(self, "wrong_modifier_order.rcx",
                                   fragment="'at' modifier must come before 'for'")

    def test_substitute_expr_slot(self):
        """Expression in substitute ingredient slot is a parse error (Decision #35)."""
        assert_fixture_parse_error(self, "substitute_expr_slot.rcx",
                                   fragment="bare identifier")

    def test_nonassoc_comparison(self):
        """a < b < c is a parse error (Decision #17)."""
        assert_fixture_parse_error(self, "nonassoc_comparison.rcx",
                                   fragment="non-associative")

    def test_quantity_of_no_paren(self):
        """quantity_of without '(' is a parse error (Decision #34)."""
        assert_fixture_parse_error(self, "quantity_of_no_paren.rcx",
                                   fragment="expected '('")


# ===========================================================================
# Inline unit tests for specific parser features
# ===========================================================================

class TestQuantityLiterals(unittest.TestCase):
    """Decision #7: two-token quantity literals."""

    def test_int_unit(self):
        ast = parse_src("recipe r() serves 1 { ingredient x : 200 g } evaluate r()")
        ing = ast.items[0].ingredients[0]
        self.assertIsInstance(ing.expr, QuantityLit)
        self.assertEqual(ing.expr.number, 200)
        self.assertEqual(ing.expr.unit, "g")

    def test_float_unit(self):
        ast = parse_src("recipe r() serves 1 { ingredient x : 1.5 kg } evaluate r()")
        ing = ast.items[0].ingredients[0]
        self.assertIsInstance(ing.expr, QuantityLit)
        self.assertAlmostEqual(ing.expr.number, 1.5)
        self.assertEqual(ing.expr.unit, "kg")

    def test_pinch_literal(self):
        ast = parse_src("recipe r() serves 1 { ingredient s : 1 pinch } evaluate r()")
        ing = ast.items[0].ingredients[0]
        self.assertIsInstance(ing.expr, QuantityLit)
        self.assertEqual(ing.expr.unit, "pinch")

    def test_int_without_unit(self):
        ast = parse_src("recipe r() serves 4 { ingredient x : 200 g } evaluate r()")
        serves = ast.items[0].serves
        self.assertIsInstance(serves, IntLit)
        self.assertEqual(serves.value, 4)

    def test_temperature_unit(self):
        ast = parse_src(
            'recipe r() serves 1 { ingredient x : 1 g  step "s" at 180 °C { bake(x) } } evaluate r()')
        step = ast.items[0].steps[0]
        self.assertIsInstance(step.at_expr, QuantityLit)
        self.assertEqual(step.at_expr.unit, "°C")


class TestQuantityOf(unittest.TestCase):
    """Decision #34: quantity_of is a unary operator, not a function call."""

    def test_quantity_of_node(self):
        ast = parse_src(
            "recipe r() serves 1 { ingredient x : 1 g  step \"s\" { let q : Mass = quantity_of(x) } } evaluate r()")
        step = ast.items[0].steps[0]
        let = step.body[0]
        self.assertIsInstance(let.expr, QuantityOf)
        self.assertIsInstance(let.expr.operand, Identifier)
        self.assertEqual(let.expr.operand.name, "x")

    def test_quantity_of_missing_lparen(self):
        src = 'recipe r() serves 1 { ingredient x:1 g step "s"{ let q:Mass = quantity_of x} } evaluate r()'
        assert_parse_error(self, src, fragment="expected '('")


class TestSubstituteCall(unittest.TestCase):
    """Decision #35: ingredient slots are bare identifiers."""

    def test_substitute_valid(self):
        src = (
            "recipe r() serves 1 { ingredient a : 1 g  ingredient b : 1 g "
            "step \"s\" { bake(a) } } "
            "evaluate substitute(r(), a, with: b, ratio: 1.0)"
        )
        ast = parse_src(src)
        ev = ast.items[1]
        self.assertIsInstance(ev.expr, SubstituteCall)
        self.assertEqual(ev.expr.original_name, "a")
        self.assertEqual(ev.expr.replacement_name, "b")

    def test_substitute_expr_in_slot_fails(self):
        src = (
            "recipe r() serves 1 { ingredient a : 1 g  ingredient b : 1 g "
            "step \"s\" { bake(a) } } "
            "evaluate substitute(r(), a + b, with: b, ratio: 1.0)"
        )
        assert_parse_error(self, src, fragment="bare identifier")

    def test_substitute_expr_in_replacement_slot_fails(self):
        src = (
            "recipe r() serves 1 { ingredient a : 1 g  ingredient b : 1 g "
            "step \"s\" { bake(a) } } "
            "evaluate substitute(r(), a, with: a + b, ratio: 1.0)"
        )
        assert_parse_error(self, src, fragment="bare identifier")


class TestNonAssocComparisons(unittest.TestCase):
    """Decision #17: comparisons are non-associative."""

    def _recipe_wrap(self, expr: str) -> str:
        return (
            f"function f(x: int) -> bool {{ return {expr} }} evaluate f(1)"
        )

    def test_single_lt_ok(self):
        parse_src(self._recipe_wrap("1 < 2"))

    def test_chained_lt_fails(self):
        assert_parse_error(self, self._recipe_wrap("1 < 2 < 3"),
                           fragment="non-associative")

    def test_chained_eq_fails(self):
        assert_parse_error(self, self._recipe_wrap("1 == 2 == 3"),
                           fragment="non-associative")

    def test_chained_mixed_fails(self):
        # Bug 1 fix: 1 < 2 == 2  is NOW VALID (cross-level, parses as (1<2)==2).
        # A truly-invalid cross-level chain needs comparison on BOTH sides of ==:
        # 1 < 2 == 2 < 3  =>  (1<2) == (2<3) — right side is a CompareOp → non-assoc error
        assert_parse_error(self, self._recipe_wrap("1 < 2 == 2 < 3"),
                           fragment="non-associative")


class TestMandatoryBraces(unittest.TestCase):
    """Decision #20: if and else bodies require braces."""

    def test_if_no_brace_fails(self):
        src = "function f(n: int) -> bool { if n > 0 return true return false } evaluate f(1)"
        assert_parse_error(self, src, fragment="expected '{'")

    def test_else_no_brace_fails(self):
        src = ("function f(n: int) -> bool { "
               "if n > 0 { return true } else return false } evaluate f(1)")
        assert_parse_error(self, src, fragment="expected '{'")

    def test_if_else_with_braces_ok(self):
        src = ("function f(n: int) -> int { "
               "if n > 0 { let x : int = 1 } else { let x : int = 0 } return n } evaluate f(1)")
        ast = parse_src(src)
        fn = ast.items[0]
        self.assertIsInstance(fn.body[0], IfStmt)
        self.assertIsNotNone(fn.body[0].else_body)


class TestStepModifiers(unittest.TestCase):
    """Decision #23: [at <expr>] must precede [for <expr>]."""

    def test_at_before_for_ok(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" at 180 °C for 3 min { bake(x) } } evaluate r()')
        ast = parse_src(src)
        step = ast.items[0].steps[0]
        self.assertIsNotNone(step.at_expr)
        self.assertIsNotNone(step.for_expr)

    def test_at_only_ok(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" at 180 °C { bake(x) } } evaluate r()')
        ast = parse_src(src)
        step = ast.items[0].steps[0]
        self.assertIsNotNone(step.at_expr)
        self.assertIsNone(step.for_expr)

    def test_for_only_ok(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" for 3 min { bake(x) } } evaluate r()')
        ast = parse_src(src)
        step = ast.items[0].steps[0]
        self.assertIsNone(step.at_expr)
        self.assertIsNotNone(step.for_expr)

    def test_for_before_at_fails(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" for 3 min at 180 °C { bake(x) } } evaluate r()')
        assert_parse_error(self, src, fragment="'at' modifier must come before 'for'")


class TestPrecedence(unittest.TestCase):
    """Spec §5: verify each precedence level produces the correct tree structure."""

    def _expr_ast(self, expr_src: str):
        src = f"function f(x: int) -> int {{ return {expr_src} }} evaluate f(1)"
        fn = parse_src(src).items[0]
        return fn.body[-1].expr  # ReturnStmt.expr

    def test_mul_binds_tighter_than_add(self):
        # 1 + 2 * 3  =>  BinaryOp('+', 1, BinaryOp('*', 2, 3))
        ast = self._expr_ast("1 + 2 * 3")
        self.assertIsInstance(ast, BinaryOp)
        self.assertEqual(ast.op, '+')
        self.assertIsInstance(ast.right, BinaryOp)
        self.assertEqual(ast.right.op, '*')

    def test_unary_minus_binds_tightest(self):
        # -1 * 2  =>  BinaryOp('*', UnaryOp('-', 1), 2)
        ast = self._expr_ast("-1 * 2")
        self.assertIsInstance(ast, BinaryOp)
        self.assertEqual(ast.op, '*')
        self.assertIsInstance(ast.left, UnaryOp)
        self.assertEqual(ast.left.op, '-')

    def test_and_binds_tighter_than_or(self):
        # a || b && c  =>  BinaryOp('||', a, BinaryOp('&&', b, c))
        ast = self._expr_ast("1 == 1 || 2 == 2 && 3 == 3")
        self.assertIsInstance(ast, BinaryOp)
        self.assertEqual(ast.op, '||')
        self.assertIsInstance(ast.right, BinaryOp)
        self.assertEqual(ast.right.op, '&&')

    def test_parens_override_precedence(self):
        # (1 + 2) * 3  =>  BinaryOp('*', BinaryOp('+', 1, 2), 3)
        ast = self._expr_ast("(1 + 2) * 3")
        self.assertIsInstance(ast, BinaryOp)
        self.assertEqual(ast.op, '*')
        self.assertIsInstance(ast.left, BinaryOp)
        self.assertEqual(ast.left.op, '+')


class TestActionVerbs(unittest.TestCase):
    """Spec §8: action verbs are statement-only; they cannot appear in expressions."""

    def test_action_verb_in_step_ok(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" { combine(x) } } evaluate r()')
        ast = parse_src(src)
        step = ast.items[0].steps[0]
        self.assertIsInstance(step.body[0], ActionStmt)
        self.assertEqual(step.body[0].verb, "combine")

    def test_action_verb_in_expr_fails(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" { let y : int = combine(x) } } evaluate r()')
        assert_parse_error(self, src, fragment="cannot appear in an expression")

    def test_zero_arg_action_ok(self):
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'step "s" { flip() } } evaluate r()')
        ast = parse_src(src)
        stmt = ast.items[0].steps[0].body[0]
        self.assertIsInstance(stmt, ActionStmt)
        self.assertEqual(stmt.args, [])


class TestEvaluateTopLevelOnly(unittest.TestCase):
    """Spec §9: evaluate is a top-level statement only."""

    def test_evaluate_inside_recipe_fails(self):
        # 'evaluate' inside a recipe body is not a valid statement keyword
        src = ('recipe r() serves 1 { ingredient x : 1 g '
               'evaluate r() } evaluate r()')
        assert_parse_error(self, src)

    def test_evaluate_inside_function_fails(self):
        src = 'function f(n: int) -> int { evaluate f(1) return 1 } evaluate f(1)'
        assert_parse_error(self, src)


class TestScaleCall(unittest.TestCase):

    def test_scale_parsed(self):
        src = ("recipe r() serves 1 { ingredient x : 1 g  step \"s\" { bake(x) } } "
               "evaluate scale(r(), by: 2)")
        ev = parse_src(src).items[1]
        self.assertIsInstance(ev.expr, ScaleCall)
        self.assertIsInstance(ev.expr.by, IntLit)
        self.assertEqual(ev.expr.by.value, 2)


class TestListLiteral(unittest.TestCase):

    def test_list_parsed(self):
        src = ("function f(n: int) -> int { return n } evaluate f(1)")
        # Test list in ingredient (type-check happens in Part 2)
        src2 = ("recipe r() serves 1 { ingredient x : 1 g  "
                "step \"s\" { foreach item in [1, 2, 3] { add(x) } } } evaluate r()")
        ast = parse_src(src2)
        step = ast.items[0].steps[0]
        foreach = step.body[0]
        self.assertIsInstance(foreach, ForeachStmt)
        self.assertIsInstance(foreach.iterable, ListLit)
        self.assertEqual(len(foreach.iterable.elements), 3)


class TestRecipeCallVsFunctionCall(unittest.TestCase):
    """Distinguish recipe calls (keyword args) from function calls (positional)."""

    def test_function_call_positional(self):
        src = ("function half(n: int) -> int { return n / 2 } "
               "recipe r() serves half(4) { ingredient x : 1 g  step \"s\" { bake(x) } } "
               "evaluate r()")
        ast = parse_src(src)
        serves = ast.items[1].serves
        self.assertIsInstance(serves, FunctionCall)
        self.assertEqual(serves.name, "half")
        self.assertEqual(len(serves.args), 1)

    def test_recipe_call_keyword(self):
        src = ("recipe r(n: int) serves n { ingredient x : 1 g  step \"s\" { bake(x) } } "
               "evaluate r(n: 4)")
        ev = parse_src(src).items[1]
        self.assertIsInstance(ev.expr, RecipeCall)
        self.assertEqual(ev.expr.kwargs[0].name, "n")


# ===========================================================================
# Round-2 bug-fix regression tests
# ===========================================================================

class TestBugFixesRound2(unittest.TestCase):
    """One test per bug/gap fixed in round 2."""

    # ------------------------------------------------------------------
    # Bug 1 — _parse_rel falsely rejected a < b == c
    # ------------------------------------------------------------------

    def test_bug1_cross_level_passes(self):
        """a < b == c is valid (different precedence levels, Decision #17)."""
        src = ("function f(a: int, b: int, c: bool) -> bool { return a < b == c } "
               "evaluate f(1, 2, true)")
        ast = parse_src(src)
        ret = ast.items[0].body[-1].expr   # ReturnStmt.expr
        self.assertIsInstance(ret, CompareOp)
        self.assertEqual(ret.op, '==')
        self.assertIsInstance(ret.left, CompareOp)
        self.assertEqual(ret.left.op, '<')

    def test_bug1_single_lt_still_ok(self):
        src = "function f(a: int, b: int) -> bool { return a < b } evaluate f(1, 2)"
        parse_src(src)  # must not raise

    def test_bug1_lt_lt_chain_still_fails(self):
        """a < b < c is still non-associative (level-4 chaining)."""
        src = "function f(a: int, b: int, c: int) -> bool { return a < b < c } evaluate f(1,2,3)"
        assert_parse_error(self, src, fragment="non-associative")

    def test_bug1_eq_eq_chain_still_fails(self):
        """a == b == c is still non-associative (level-5 chaining)."""
        src = "function f(a: int, b: int, c: int) -> bool { return a == b == c } evaluate f(1,2,3)"
        assert_parse_error(self, src, fragment="non-associative")

    def test_bug1_lt_eq_lt_chain_fails(self):
        """a < b == c < d still fails — comparison on both sides of == (Decision #17)."""
        src = ("function f(a: int, b: int, c: int, d: int) -> bool "
               "{ return a < b == c < d } evaluate f(1,2,3,4)")
        assert_parse_error(self, src, fragment="non-associative")

    def test_bug1_full_hierarchy_passes(self):
        """1 + 2*3 < 4 == true && false || true must parse cleanly."""
        src = "function f() -> bool { return 1 + 2 * 3 < 4 == true && false || true } evaluate f()"
        ast = parse_src(src)
        # Outermost op is ||
        ret = ast.items[0].body[-1].expr
        self.assertIsInstance(ret, BinaryOp)
        self.assertEqual(ret.op, '||')

    # ------------------------------------------------------------------
    # Bug 2 — scale/substitute accepted inside recipe/function bodies
    # ------------------------------------------------------------------

    def _simple_recipe(self, body_line: str) -> str:
        return (
            f"recipe base() serves 1 {{ ingredient x : 1 g  step \"s\" {{ bake(x) }} }}\n"
            f"recipe wrapper() serves 1 {{ ingredient x : 1 g  step \"s\" {{ {body_line} }} }}\n"
            f"evaluate wrapper()"
        )

    def test_bug2_scale_in_ingredient_fails(self):
        src = ("recipe base() serves 1 { ingredient x : 1 g  step \"s\" { bake(x) } }\n"
               "recipe wrapper() serves 1 { ingredient x : scale(base(), by: 2) "
               "step \"s\" { bake(x) } } evaluate wrapper()")
        assert_parse_error(self, src, fragment="call-site only")

    def test_bug2_scale_in_step_expr_fails(self):
        src = ("recipe base() serves 1 { ingredient x : 1 g  step \"s\" { bake(x) } }\n"
               "recipe wrapper() serves 1 { ingredient x : 1 g  step \"s\" { "
               "let r : int = scale(base(), by: 2)  bake(x) } } evaluate wrapper()")
        assert_parse_error(self, src, fragment="call-site only")

    def test_bug2_scale_in_evaluate_ok(self):
        src = ("recipe r() serves 1 { ingredient x : 1 g  step \"s\" { bake(x) } } "
               "evaluate scale(r(), by: 2)")
        parse_src(src)  # must not raise

    def test_bug2_substitute_in_step_fails(self):
        # 'substitute' as a statement inside step body triggers a different path
        # but is still caught (unexpected token)
        src = ("recipe r(n: int) serves n { ingredient a : 1 g  ingredient b : 1 g  "
               "step \"s\" { substitute(r(n: 2), a, with: b, ratio: 1.0) } } evaluate r(n: 1)")
        assert_parse_error(self, src)

    def test_bug2_scale_in_function_fails(self):
        src = ("recipe r() serves 1 { ingredient x : 1 g  step \"s\" { bake(x) } }\n"
               "function f() -> int { let s : int = scale(r(), by: 2) return 1 } evaluate f()")
        assert_parse_error(self, src, fragment="call-site only")

    # ------------------------------------------------------------------
    # Bug 3 — RecursionError on deep parens
    # ------------------------------------------------------------------

    def test_bug3_deep_nesting_parseable(self):
        """150 levels of nested parens must parse without RecursionError
        when the recursion limit is raised (as the CLI does)."""
        import sys
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(10000)
        try:
            inner = '1'
            for _ in range(150):
                inner = f'({inner})'
            src = f"function f() -> int {{ return {inner} }} evaluate f()"
            ast = parse_src(src)  # must not raise
            self.assertIsNotNone(ast)
        finally:
            sys.setrecursionlimit(old_limit)

    # ------------------------------------------------------------------
    # Bug 4 — repeated 'at' modifier should say "duplicate 'at'"
    # ------------------------------------------------------------------

    def test_bug4_repeated_at_fails(self):
        assert_fixture_parse_error(self, "wrong_modifier_order.rcx")  # existing check
        # inline: at...at
        src = ("recipe r() serves 1 { ingredient x : 1 g  "
               "step \"s\" at 180 °C at 200 °C { bake(x) } } evaluate r()")
        assert_parse_error(self, src, fragment="duplicate 'at'")

    # ------------------------------------------------------------------
    # Bug 5 — repeated 'for' modifier should say "duplicate 'for'"
    # ------------------------------------------------------------------

    def test_bug5_repeated_for_fails(self):
        src = ("recipe r() serves 1 { ingredient x : 1 g  "
               "step \"s\" for 30 min for 45 min { bake(x) } } evaluate r()")
        assert_parse_error(self, src, fragment="duplicate 'for'")

    # ------------------------------------------------------------------
    # Bug 6 — missing ratio: gives wrong error message
    # ------------------------------------------------------------------

    def test_bug6_missing_ratio_says_ratio(self):
        src = ("recipe r(n: int) serves n { ingredient a : 1 g  ingredient b : 1 g  "
               "step \"s\" { blend() } } "
               "evaluate substitute(r(n: 2), a, with: b)")
        assert_parse_error(self, src, fragment="ratio:")

    # ------------------------------------------------------------------
    # Bug 7 — quantity_of() empty parens
    # ------------------------------------------------------------------

    def test_bug7_quantity_of_empty_fails(self):
        src = ("recipe r() serves 1 { ingredient x : 1 g  "
               "step \"s\" { let q : Mass = quantity_of()  bake(x) } } evaluate r()")
        assert_parse_error(self, src, fragment="quantity_of requires an operand")

    # ------------------------------------------------------------------
    # Bug 9 — if-brace error mentions the 'if' line
    # ------------------------------------------------------------------

    def test_bug9_if_brace_error_mentions_if_line(self):
        # The 'if' is on line 1; 'return' is on line 2
        src = "function f(n: int) -> int {\nif n < 5\n  return 1\nreturn 2\n} evaluate f(3)"
        err = assert_parse_error(self, src)
        # The error must cite the 'if' line (2 in this source with the surrounding function)
        self.assertIn("'if'", str(err))

    # ------------------------------------------------------------------
    # Gap 2 — trailing comma in list literal now rejected
    # ------------------------------------------------------------------

    def test_gap2_trailing_comma_fixture_fails(self):
        assert_fixture_parse_error(self, "list_trailing_comma.rcx",
                                   fragment="trailing comma")

    def test_gap2_trailing_comma_inline_fails(self):
        src = ("function f(n: int) -> int { "
               "foreach x in [1, 2, 3,] { let y : int = x } return n } evaluate f(1)")
        assert_parse_error(self, src, fragment="trailing comma")

    def test_gap2_no_trailing_comma_ok(self):
        src = ("function f(n: int) -> int { "
               "foreach x in [1, 2, 3] { let y : int = x } return n } evaluate f(1)")
        parse_src(src)  # must not raise

    def test_gap2_empty_list_ok(self):
        src = ("function f(n: int) -> int { "
               "foreach x in [] { let y : int = x } return n } evaluate f(1)")
        parse_src(src)  # empty list — no trailing comma issue


if __name__ == "__main__":
    unittest.main()
