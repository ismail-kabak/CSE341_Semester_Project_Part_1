"""
Recipix Part 2 — type checker.

Owner:   İsmail Kabak (1901042652)
Plan:    Implements plan §2.1 (in-place AST annotation + AmbiguousCall
         resolution), §2.3 (action-verb 3-class table), §2.5 (environment
         chain), §2.6 (serves timing, single-return, evaluate-only), §5.

Spec §10 error checklist
-------------------------
  #1   dimension mismatch in BinaryOp / CompareOp / SubstituteCall
  #2   Pinch in arithmetic / comparison / scaling
  #3   heterogeneous list literal
  #4   unknown identifier
  #5   single-assignment violation (re-declare in same scope)
  #6   shadowing (re-declare visible from any ancestor scope)
  #7   non-bool in if condition
  #8   non-int in repeat count
  #9   non-list in foreach source
  #10  non-Temperature in step at modifier
  #11  non-Duration in step for modifier
  #12  wrong arity in recipe or function call
  #13  wrong argument types in recipe or function call / action verbs
  #14  substitute of unknown ingredient
  #15  float → int coercion attempt
  #16  substitute swaps Pinch ↔ Quantity
  #17  non-IDENT in substitute slot (parser catches this; no checker branch needed)
  #18  quantity_of on non-Ingredient
  #19  return not as last statement of function body (plan §2.6)
"""

from __future__ import annotations

from typing import Optional

from . import ast_nodes as ast
from .ast_nodes import Program
from .environment import Environment
from .errors import TypeCheckError, ShadowingError
from .runtime_values import UNIT_TABLE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIMITIVES   = frozenset({"int", "float", "bool"})
DIMENSIONS   = frozenset({"Mass", "Volume", "Count", "Temperature", "Duration"})
SCALAR_TYPES = frozenset({"int", "float"})
VALID_TYPES  = PRIMITIVES | DIMENSIONS | {"Pinch"}

# Action verb classification (plan §2.3)
HETEROGENEOUS_VERBS = frozenset({"combine", "mix", "add", "sprinkle"})
HOMOGENEOUS_VERBS   = frozenset({"pour", "drizzle", "whisk", "blend", "knead", "melt"})
NULLARY_VERBS       = frozenset({"bake", "flip"})


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check(program: Program) -> Program:
    """
    Type-check *program* in-place and return it.

    Annotates every Expr node with ``.inferred_type`` and rewrites every
    ``AmbiguousCall`` to a ``FunctionCall`` or ``RecipeCall``.
    Raises :class:`recipix.errors.TypeCheckError` on the first violation.
    """
    return TypeChecker().check(program)


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

class TypeChecker:
    """Tree-walking type checker for Recipix programs."""

    def __init__(self) -> None:
        self.globals: Environment = Environment()
        self.env: Environment = self.globals

        # Top-level symbol tables (name → declaration node)
        self.recipes:   dict[str, ast.RecipeDecl]   = {}
        self.functions: dict[str, ast.FunctionDecl] = {}

        # Ingredient types per recipe: recipe_name → {ing_name → "Ingredient:D"}
        self.recipe_ingredient_types: dict[str, dict[str, str]] = {}

        # Flags
        self.in_evaluate: bool = False
        self.current_return_type: Optional[str] = None

    # -----------------------------------------------------------------------
    # Public
    # -----------------------------------------------------------------------

    def check(self, program: Program) -> Program:
        self._check_Program(program)
        return program

    # -----------------------------------------------------------------------
    # Helpers — declaration
    # -----------------------------------------------------------------------

    def _declare(self, name: str, type_str: str, line: int, col: int = 0) -> None:
        """declare_check + define, wrapping both exceptions as TypeCheckError."""
        if self.env.has_local(name):
            raise TypeCheckError(line, col,
                f"name {name!r} is already declared in this scope", error_code=5)
        try:
            self.env.declare_check(name)
        except ShadowingError:
            raise TypeCheckError(line, col,
                f"name {name!r} shadows an existing binding", error_code=6)
        self.env.define(name, type_str)

    def _resolve_type_name(self, type_name: str, line: int) -> str:
        if type_name not in VALID_TYPES:
            raise TypeCheckError(line, 0, f"unknown type name {type_name!r}")
        return type_name

    # -----------------------------------------------------------------------
    # Helpers — annotation and type predicates
    # -----------------------------------------------------------------------

    def _annotate(self, node, t: str) -> str:
        node.inferred_type = t
        return t

    def _dimension_of(self, t: str) -> Optional[str]:
        """Return dimension if t is Quantity<D> or Ingredient:D (non-Pinch)."""
        if t in DIMENSIONS:
            return t
        if t.startswith("Ingredient:") and not t.endswith(":Pinch"):
            return t[len("Ingredient:"):]
        return None

    def _reject_pinch(self, t: str, line: int, ctx: str) -> None:
        if t in ("Pinch", "Ingredient:Pinch"):
            raise TypeCheckError(line, 0,
                f"Pinch value cannot appear in {ctx}", error_code=2)

    def _compatible(self, actual: str, expected: str) -> bool:
        """True if actual is assignable to expected (coercions allowed)."""
        if actual == expected:
            return True
        # int widens to float
        if actual == "int" and expected == "float":
            return True
        # Ingredient:D projects to its dimension D
        if actual.startswith("Ingredient:") and not actual.endswith(":Pinch"):
            if actual[len("Ingredient:"):] == expected:
                return True
        return False

    # -----------------------------------------------------------------------
    # Pre-pass: rewrite AmbiguousCall throughout the AST
    # -----------------------------------------------------------------------

    def _rewrite_ambiguous(self, value):
        """
        Walk the whole AST and replace every AmbiguousCall with the correct
        resolved node (FunctionCall or RecipeCall).  Uses __dataclass_fields__
        for generic traversal — same strategy as the test helper.
        """
        if isinstance(value, ast.AmbiguousCall):
            if value.name in self.functions:
                return ast.FunctionCall(name=value.name, args=[], line=value.line)
            if value.name in self.recipes:
                return ast.RecipeCall(name=value.name, kwargs=[], line=value.line)
            return value  # unknown name — left for error #4 in _check_expr
        if isinstance(value, list):
            for i, v in enumerate(value):
                value[i] = self._rewrite_ambiguous(v)
            return value
        if hasattr(value, "__dataclass_fields__"):
            for field_name in value.__dataclass_fields__:
                setattr(value, field_name,
                        self._rewrite_ambiguous(getattr(value, field_name)))
            return value
        return value

    # -----------------------------------------------------------------------
    # Single-return enforcement (error #19)
    # -----------------------------------------------------------------------

    def _check_single_return(self, body: list, line: int) -> None:
        if not body or not isinstance(body[-1], ast.ReturnStmt):
            raise TypeCheckError(line, 0,
                "function body must end with exactly one return statement",
                error_code=19)
        for stmt in body[:-1]:
            self._no_return_in(stmt, line)

    def _no_return_in(self, stmt, line: int) -> None:
        if isinstance(stmt, ast.ReturnStmt):
            raise TypeCheckError(stmt.line, 0,
                "return must appear only as the last statement of a function body",
                error_code=19)
        if isinstance(stmt, ast.IfStmt):
            for s in stmt.then_body:
                self._no_return_in(s, line)
            for s in (stmt.else_body or []):
                self._no_return_in(s, line)
        elif isinstance(stmt, ast.RepeatStmt):
            for s in stmt.body:
                self._no_return_in(s, line)
        elif isinstance(stmt, ast.ForeachStmt):
            for s in stmt.body:
                self._no_return_in(s, line)

    # -----------------------------------------------------------------------
    # Top-level
    # -----------------------------------------------------------------------

    def _check_Program(self, node: ast.Program) -> None:
        # Pass 1: collect top-level names
        for item in node.items:
            if isinstance(item, ast.RecipeDecl):
                if item.name in self.recipes or item.name in self.functions:
                    raise TypeCheckError(item.line, 0,
                        f"name {item.name!r} is already declared", error_code=5)
                self.recipes[item.name] = item
                self.globals.define(item.name, "RecipeDecl")
            elif isinstance(item, ast.FunctionDecl):
                if item.name in self.functions or item.name in self.recipes:
                    raise TypeCheckError(item.line, 0,
                        f"name {item.name!r} is already declared", error_code=5)
                self.functions[item.name] = item
                self.globals.define(item.name, "FunctionDecl")

        # Pass 2: rewrite all AmbiguousCall nodes in the whole tree
        self._rewrite_ambiguous(node)

        # Pass 3: type-check everything
        for item in node.items:
            if isinstance(item, ast.RecipeDecl):
                self._check_RecipeDecl(item)
            elif isinstance(item, ast.FunctionDecl):
                self._check_FunctionDecl(item)
            elif isinstance(item, ast.EvalStmt):
                self._check_EvalStmt(item)

    def _check_RecipeDecl(self, node: ast.RecipeDecl) -> None:
        saved_env = self.env
        self.env = saved_env.child()
        ing_types: dict[str, str] = {}

        # Bind params into body scope (plan §2.5: same scope as body)
        for p in node.params:
            t = self._resolve_type_name(p.type_name, p.line)
            self._declare(p.name, t, p.line)

        # serves expression must be int
        serves_t = self._check_expr(node.serves)
        if serves_t != "int":
            raise TypeCheckError(node.line, 0,
                f"serves expression must be int, got {serves_t!r}")

        # Ingredient declarations
        for ing in node.ingredients:
            expr_t = self._check_expr(ing.expr)
            if expr_t not in DIMENSIONS and expr_t != "Pinch":
                raise TypeCheckError(ing.line, 0,
                    f"ingredient {ing.name!r} must have a quantity type, got {expr_t!r}")
            ing_type_str = f"Ingredient:{expr_t}"
            self._declare(ing.name, ing_type_str, ing.line)
            ing_types[ing.name] = ing_type_str

        self.recipe_ingredient_types[node.name] = ing_types

        # Step declarations
        for step in node.steps:
            self._check_StepDecl(step)

        self.env = saved_env

    def _check_FunctionDecl(self, node: ast.FunctionDecl) -> None:
        # Error #19: check before walking body
        self._check_single_return(node.body, node.line)

        ret_type = self._resolve_type_name(node.return_type, node.line)
        saved_env = self.env
        saved_ret = self.current_return_type
        self.env = saved_env.child()
        self.current_return_type = ret_type

        for p in node.params:
            t = self._resolve_type_name(p.type_name, p.line)
            self._declare(p.name, t, p.line)

        for stmt in node.body[:-1]:
            self._check_stmt(stmt)

        # Check return statement type
        ret_stmt = node.body[-1]
        actual = self._check_expr(ret_stmt.expr)
        if actual == "float" and ret_type == "int":
            raise TypeCheckError(ret_stmt.line, 0,
                "cannot implicitly convert float to int in return", error_code=15)
        if not self._compatible(actual, ret_type):
            raise TypeCheckError(ret_stmt.line, 0,
                f"return type {actual!r} does not match declared {ret_type!r}")

        self.env = saved_env
        self.current_return_type = saved_ret

    def _check_StepDecl(self, node: ast.StepDecl) -> None:
        if node.at_expr is not None:
            at_t = self._check_expr(node.at_expr)
            if at_t != "Temperature":
                raise TypeCheckError(node.line, 0,
                    f"step 'at' modifier must be Temperature, got {at_t!r}",
                    error_code=10)
        if node.for_expr is not None:
            for_t = self._check_expr(node.for_expr)
            if for_t != "Duration":
                raise TypeCheckError(node.line, 0,
                    f"step 'for' modifier must be Duration, got {for_t!r}",
                    error_code=11)
        saved_env = self.env
        self.env = saved_env.child()
        for stmt in node.body:
            self._check_stmt(stmt)
        self.env = saved_env

    def _check_Param(self, node: ast.Param) -> str:
        return self._resolve_type_name(node.type_name, node.line)

    # -----------------------------------------------------------------------
    # Statement dispatch
    # -----------------------------------------------------------------------

    def _check_stmt(self, node) -> None:
        handler = getattr(self, f"_check_{type(node).__name__}", None)
        if handler is None:
            raise NotImplementedError(f"No checker for statement {type(node).__name__}")
        handler(node)

    def _check_EvalStmt(self, node: ast.EvalStmt) -> None:
        saved = self.in_evaluate
        self.in_evaluate = True
        self._check_expr(node.expr)
        self.in_evaluate = saved

    def _check_LetStmt(self, node: ast.LetStmt) -> None:
        ann = self._resolve_type_name(node.type_name, node.line)
        actual = self._check_expr(node.expr)
        if actual == "float" and ann == "int":
            raise TypeCheckError(node.line, 0,
                f"cannot implicitly convert float to int in let {node.name!r}",
                error_code=15)
        if not self._compatible(actual, ann):
            raise TypeCheckError(node.line, 0,
                f"let {node.name!r}: expected {ann!r}, got {actual!r}")
        self._declare(node.name, ann, node.line)

    def _check_IfStmt(self, node: ast.IfStmt) -> None:
        cond_t = self._check_expr(node.condition)
        if cond_t != "bool":
            raise TypeCheckError(node.line, 0,
                f"if condition must be bool, got {cond_t!r}", error_code=7)
        saved_env = self.env
        self.env = saved_env.child()
        for s in node.then_body:
            self._check_stmt(s)
        self.env = saved_env
        if node.else_body is not None:
            self.env = saved_env.child()
            for s in node.else_body:
                self._check_stmt(s)
            self.env = saved_env

    def _check_RepeatStmt(self, node: ast.RepeatStmt) -> None:
        count_t = self._check_expr(node.count)
        if count_t != "int":
            raise TypeCheckError(node.line, 0,
                f"repeat count must be int, got {count_t!r}", error_code=8)
        saved_env = self.env
        self.env = saved_env.child()
        for s in node.body:
            self._check_stmt(s)
        self.env = saved_env

    def _check_ForeachStmt(self, node: ast.ForeachStmt) -> None:
        iter_t = self._check_expr(node.iterable)
        if not iter_t.startswith("List<"):
            raise TypeCheckError(node.line, 0,
                f"foreach source must be a list, got {iter_t!r}", error_code=9)
        elem_t = iter_t[5:-1]  # "List<X>" → "X"
        saved_env = self.env
        self.env = saved_env.child()
        self._declare(node.var_name, elem_t, node.line)
        for s in node.body:
            self._check_stmt(s)
        self.env = saved_env

    def _check_ReturnStmt(self, node: ast.ReturnStmt) -> None:
        self._check_expr(node.expr)

    def _check_ActionStmt(self, node: ast.ActionStmt) -> None:
        verb = node.verb
        arg_types = [self._check_expr(a) for a in node.args]

        if verb in NULLARY_VERBS:
            if len(node.args) != 0:
                raise TypeCheckError(node.line, 0,
                    f"{verb!r} takes 0 arguments, got {len(node.args)}",
                    error_code=12)

        elif verb in HETEROGENEOUS_VERBS:
            if not node.args:
                raise TypeCheckError(node.line, 0,
                    f"{verb!r} requires at least 1 argument", error_code=12)
            for i, t in enumerate(arg_types):
                if not (t.startswith("Ingredient:") or t in DIMENSIONS or t == "Pinch"):
                    raise TypeCheckError(node.line, 0,
                        f"{verb!r} argument {i+1}: expected Ingredient or Quantity, "
                        f"got {t!r}", error_code=13)

        elif verb in HOMOGENEOUS_VERBS:
            dims = []
            for i, t in enumerate(arg_types):
                d = self._dimension_of(t)
                if d is None:
                    raise TypeCheckError(node.line, 0,
                        f"{verb!r} argument {i+1}: expected non-Pinch "
                        f"quantity or ingredient, got {t!r}", error_code=13)
                dims.append(d)
            if len(set(dims)) > 1:
                raise TypeCheckError(node.line, 0,
                    f"{verb!r} arguments must share one dimension, got {dims!r}",
                    error_code=13)
        else:
            raise TypeCheckError(node.line, 0, f"unknown action verb {verb!r}")

    # -----------------------------------------------------------------------
    # Expression dispatch
    # -----------------------------------------------------------------------

    def _check_expr(self, node) -> str:
        handler = getattr(self, f"_check_{type(node).__name__}", None)
        if handler is None:
            raise NotImplementedError(
                f"No type-check handler for {type(node).__name__}")
        return handler(node)

    # -----------------------------------------------------------------------
    # Expressions — literals
    # -----------------------------------------------------------------------

    def _check_IntLit(self, node: ast.IntLit) -> str:
        return self._annotate(node, "int")

    def _check_FloatLit(self, node: ast.FloatLit) -> str:
        return self._annotate(node, "float")

    def _check_BoolLit(self, node: ast.BoolLit) -> str:
        return self._annotate(node, "bool")

    def _check_StringLit(self, node: ast.StringLit) -> str:
        raise TypeCheckError(
            node.line, 0,
            "string literal in expression position: per spec §1, string is not "
            "a type and string literals are only allowed as step descriptions",
            error_code=21,
        )

    def _check_QuantityLit(self, node: ast.QuantityLit) -> str:
        if node.unit == "pinch":
            return self._annotate(node, "Pinch")
        try:
            _, dim = UNIT_TABLE[node.unit]
        except KeyError:
            raise TypeCheckError(node.line, 0, f"unknown unit {node.unit!r}")
        return self._annotate(node, dim)

    def _check_ListLit(self, node: ast.ListLit) -> str:
        if not node.elements:
            raise TypeCheckError(
                node.line, 0,
                "empty list literal: Recipix v1 has no list type annotation syntax, "
                "so the element type of an empty list cannot be inferred; "
                "write a list with at least one element",
                error_code=20,
            )
        types = [self._check_expr(e) for e in node.elements]
        first = types[0]
        first_dim = self._dimension_of(first)
        for i, t in enumerate(types[1:], 1):
            d = self._dimension_of(t)
            same_dim = first_dim is not None and d == first_dim
            same_scalar = {first, t} <= SCALAR_TYPES
            if not (same_dim or same_scalar or first == t):
                raise TypeCheckError(node.line, 0,
                    f"heterogeneous list: element 1 is {first!r}, "
                    f"element {i + 1} is {t!r}", error_code=3)
        if first_dim is not None:
            return self._annotate(node, f"List<{first_dim}>")
        if all(t in SCALAR_TYPES for t in types):
            result = "float" if any(t == "float" for t in types) else "int"
            return self._annotate(node, f"List<{result}>")
        return self._annotate(node, f"List<{first}>")

    # -----------------------------------------------------------------------
    # Expressions — operators
    # -----------------------------------------------------------------------

    def _check_Identifier(self, node: ast.Identifier) -> str:
        try:
            t = self.env.lookup(node.name)
        except KeyError:
            raise TypeCheckError(node.line, 0,
                f"unknown identifier {node.name!r}", error_code=4)
        return self._annotate(node, t)

    def _check_UnaryOp(self, node: ast.UnaryOp) -> str:
        t = self._check_expr(node.operand)
        if node.op == "!":
            if t != "bool":
                raise TypeCheckError(node.line, 0,
                    f"! requires bool, got {t!r}")
            return self._annotate(node, "bool")
        if node.op == "-":
            d = self._dimension_of(t)
            if t in SCALAR_TYPES:
                return self._annotate(node, t)
            if d is not None:
                return self._annotate(node, d)
            raise TypeCheckError(node.line, 0,
                f"unary - not allowed on {t!r}")
        raise TypeCheckError(node.line, 0, f"unknown unary operator {node.op!r}")

    def _check_QuantityOf(self, node: ast.QuantityOf) -> str:
        t = self._check_expr(node.operand)
        if not t.startswith("Ingredient:"):
            raise TypeCheckError(node.line, 0,
                f"quantity_of requires an Ingredient, got {t!r}", error_code=18)
        dim = t[len("Ingredient:"):]
        return self._annotate(node, dim)

    def _check_BinaryOp(self, node: ast.BinaryOp) -> str:
        lt = self._check_expr(node.left)
        rt = self._check_expr(node.right)
        op = node.op

        # Logical operators — short-circuit handled at runtime
        if op in ("&&", "||"):
            if lt != "bool" or rt != "bool":
                raise TypeCheckError(node.line, 0,
                    f"{op!r} requires bool on both sides, got {lt!r} and {rt!r}")
            return self._annotate(node, "bool")

        # Reject Pinch before quantity dispatch
        self._reject_pinch(lt, node.line, f"binary {op!r}")
        self._reject_pinch(rt, node.line, f"binary {op!r}")

        ld = self._dimension_of(lt)
        rd = self._dimension_of(rt)

        if ld is not None or rd is not None:
            return self._check_quantity_binop(node, ld, rd, op)

        # Pure scalar arithmetic
        if lt in SCALAR_TYPES and rt in SCALAR_TYPES:
            result = "float" if "float" in (lt, rt) else "int"
            return self._annotate(node, result)

        raise TypeCheckError(node.line, 0,
            f"cannot apply {op!r} to {lt!r} and {rt!r}", error_code=1)

    def _check_quantity_binop(self, node: ast.BinaryOp,
                               ld: Optional[str], rd: Optional[str],
                               op: str) -> str:
        lt_label = ld or "scalar"
        rt_label = rd or "scalar"

        if op in ("+", "-"):
            if ld is None or rd is None:
                raise TypeCheckError(node.line, 0,
                    f"cannot {op} quantity and non-quantity "
                    f"({lt_label}, {rt_label})", error_code=1)
            if ld != rd:
                raise TypeCheckError(node.line, 0,
                    f"dimension mismatch: cannot {op} {ld} and {rd}",
                    error_code=1)
            return self._annotate(node, ld)

        if op == "*":
            if ld is not None and rd is not None:
                raise TypeCheckError(node.line, 0,
                    f"cannot multiply two quantities ({ld} * {rd})",
                    error_code=1)
            scalar_t = node.right.inferred_type if ld is not None else node.left.inferred_type
            if scalar_t not in SCALAR_TYPES:
                raise TypeCheckError(node.line, 0,
                    f"quantity * requires an int or float scalar, got {scalar_t!r}",
                    error_code=1)
            dim = ld if ld is not None else rd
            return self._annotate(node, dim)

        if op == "/":
            if ld is not None and rd is not None:
                if ld != rd:
                    raise TypeCheckError(node.line, 0,
                        f"dimension mismatch: cannot divide {ld} by {rd}",
                        error_code=1)
                return self._annotate(node, "float")
            if ld is not None:
                scalar_t = node.right.inferred_type
                if scalar_t not in SCALAR_TYPES:
                    raise TypeCheckError(node.line, 0,
                        f"quantity / requires an int or float scalar, got {scalar_t!r}",
                        error_code=1)
                return self._annotate(node, ld)

        raise TypeCheckError(node.line, 0,
            f"cannot apply {op!r} to quantity types "
            f"({lt_label}, {rt_label})", error_code=1)

    def _check_CompareOp(self, node: ast.CompareOp) -> str:
        lt = self._check_expr(node.left)
        rt = self._check_expr(node.right)

        self._reject_pinch(lt, node.line, "comparison")
        self._reject_pinch(rt, node.line, "comparison")

        ld = self._dimension_of(lt)
        rd = self._dimension_of(rt)

        if ld is not None or rd is not None:
            if ld is None or rd is None or ld != rd:
                raise TypeCheckError(node.line, 0,
                    f"dimension mismatch in comparison: {ld or lt!r} vs {rd or rt!r}",
                    error_code=1)
            return self._annotate(node, "bool")

        if lt in SCALAR_TYPES and rt in SCALAR_TYPES:
            return self._annotate(node, "bool")

        if lt == rt:
            return self._annotate(node, "bool")

        raise TypeCheckError(node.line, 0,
            f"cannot compare {lt!r} and {rt!r}", error_code=1)

    # -----------------------------------------------------------------------
    # Expressions — calls
    # -----------------------------------------------------------------------

    def _check_AmbiguousCall(self, node: ast.AmbiguousCall) -> str:
        # After _rewrite_ambiguous, only truly unknown names reach here.
        raise TypeCheckError(node.line, 0,
            f"unknown identifier {node.name!r}", error_code=4)

    def _check_FunctionCall(self, node: ast.FunctionCall) -> str:
        decl = self.functions.get(node.name)
        if decl is None:
            raise TypeCheckError(node.line, 0,
                f"unknown function {node.name!r}", error_code=4)
        if len(node.args) != len(decl.params):
            raise TypeCheckError(node.line, 0,
                f"{node.name!r} expects {len(decl.params)} arguments, "
                f"got {len(node.args)}", error_code=12)
        for i, (arg, param) in enumerate(zip(node.args, decl.params)):
            at = self._check_expr(arg)
            exp = param.type_name
            if at == "float" and exp == "int":
                raise TypeCheckError(getattr(arg, "line", node.line), 0,
                    f"cannot pass float as int to {node.name!r} "
                    f"parameter {param.name!r}", error_code=15)
            if not self._compatible(at, exp):
                raise TypeCheckError(node.line, 0,
                    f"{node.name!r} argument {i + 1}: expected {exp!r}, "
                    f"got {at!r}", error_code=13)
        return self._annotate(node, decl.return_type)

    def _check_RecipeCall(self, node: ast.RecipeCall) -> str:
        decl = self.recipes.get(node.name)
        if decl is None:
            raise TypeCheckError(node.line, 0,
                f"unknown recipe {node.name!r}", error_code=4)
        if len(node.kwargs) != len(decl.params):
            raise TypeCheckError(node.line, 0,
                f"{node.name!r} expects {len(decl.params)} keyword arguments, "
                f"got {len(node.kwargs)}", error_code=12)
        param_map = {p.name: p.type_name for p in decl.params}
        seen: set[str] = set()
        for kw in node.kwargs:
            if kw.name not in param_map:
                raise TypeCheckError(kw.line, 0,
                    f"recipe {node.name!r} has no parameter {kw.name!r}",
                    error_code=12)
            if kw.name in seen:
                raise TypeCheckError(kw.line, 0,
                    f"duplicate keyword argument {kw.name!r}")
            seen.add(kw.name)
            vt = self._check_expr(kw.value)
            exp = param_map[kw.name]
            if vt == "float" and exp == "int":
                raise TypeCheckError(kw.line, 0,
                    f"cannot pass float as int to {node.name!r}.{kw.name!r}",
                    error_code=15)
            if not self._compatible(vt, exp):
                raise TypeCheckError(kw.line, 0,
                    f"{node.name!r}.{kw.name!r}: expected {exp!r}, got {vt!r}",
                    error_code=13)
        return self._annotate(node, f"Recipe:{node.name}")

    def _check_KwArg(self, node: ast.KwArg) -> str:
        return self._check_expr(node.value)

    def _check_ScaleCall(self, node: ast.ScaleCall) -> str:
        if not self.in_evaluate:
            raise TypeCheckError(node.line, 0,
                "scale may only appear inside an evaluate statement")
        recipe_t = self._check_expr(node.recipe)
        if not recipe_t.startswith("Recipe:"):
            raise TypeCheckError(node.line, 0,
                f"scale first argument must be a Recipe, got {recipe_t!r}")
        by_t = self._check_expr(node.by)
        if by_t not in SCALAR_TYPES:
            raise TypeCheckError(node.line, 0,
                f"scale 'by' must be int or float, got {by_t!r}")
        return self._annotate(node, recipe_t)

    def _check_SubstituteCall(self, node: ast.SubstituteCall) -> str:
        if not self.in_evaluate:
            raise TypeCheckError(node.line, 0,
                "substitute may only appear inside an evaluate statement")
        recipe_t = self._check_expr(node.recipe)
        if not recipe_t.startswith("Recipe:"):
            raise TypeCheckError(node.line, 0,
                f"substitute first argument must be a Recipe, got {recipe_t!r}")
        recipe_name = recipe_t[len("Recipe:"):]
        ing_types = self.recipe_ingredient_types.get(recipe_name, {})

        orig_t = ing_types.get(node.original_name)
        if orig_t is None:
            raise TypeCheckError(node.line, 0,
                f"ingredient {node.original_name!r} not found in "
                f"recipe {recipe_name!r}", error_code=14)
        repl_t = ing_types.get(node.replacement_name)
        if repl_t is None:
            raise TypeCheckError(node.line, 0,
                f"ingredient {node.replacement_name!r} not found in "
                f"recipe {recipe_name!r}", error_code=14)

        orig_dim = orig_t[len("Ingredient:"):]
        repl_dim = repl_t[len("Ingredient:"):]

        # Error #16: Pinch in either position — ratio doesn't apply to Pinch
        if orig_dim == "Pinch" or repl_dim == "Pinch":
            raise TypeCheckError(node.line, 0,
                "cannot apply substitute-by-ratio to a Pinch ingredient",
                error_code=16)
        # Error #1: dimension mismatch
        if orig_dim != repl_dim:
            raise TypeCheckError(node.line, 0,
                f"cannot substitute {orig_dim} ingredient with "
                f"{repl_dim} ingredient (dimension mismatch)", error_code=1)

        ratio_t = self._check_expr(node.ratio)
        if ratio_t not in SCALAR_TYPES:
            raise TypeCheckError(node.line, 0,
                f"substitute ratio must be int or float, got {ratio_t!r}")

        return self._annotate(node, recipe_t)


__all__ = ["check", "TypeChecker"]
