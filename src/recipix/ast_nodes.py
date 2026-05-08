"""
Recipix AST node dataclasses.

All nodes carry `line: int` for error reporting.
Nodes marked "spec §14" are pre-committed in the specification.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Type aliases (documentation only — no runtime enforcement)
# ---------------------------------------------------------------------------
Expr = object   # any expression node
Stmt = object   # any statement node


# ===========================================================================
# Top-level
# ===========================================================================

@dataclass
class Program:
    """Root node.  items is a sequence of RecipeDecl | FunctionDecl | EvalStmt."""
    items: list
    line: int = 0


# ===========================================================================
# Declarations (top-level and within recipe/function bodies)
# ===========================================================================

@dataclass
class Param:
    """A single parameter in a recipe or function signature: name : type_name."""
    name: str
    type_name: str
    line: int


@dataclass
class RecipeDecl:
    """recipe <name>([params]) serves <expr> { <ingredients> <steps> }"""
    name: str
    params: list          # List[Param]
    serves: Expr
    ingredients: list     # List[IngredientDecl]
    steps: list           # List[StepDecl]
    line: int


@dataclass
class FunctionDecl:
    """function <name>([params]) -> <return_type> { <stmts> return <expr> }
    INVARIANT (enforced by parser): body[-1] is always ReturnStmt,
    and it is the only ReturnStmt in the list."""
    name: str
    params: list          # List[Param]
    return_type: str
    body: list            # List[Stmt], last element is ReturnStmt
    line: int


@dataclass
class IngredientDecl:
    """ingredient <name> : <expr>"""
    name: str
    expr: Expr
    line: int


@dataclass
class StepDecl:
    """step <string_lit> [at <expr>] [for <expr>] { <stmts> }"""
    description: str
    at_expr: Optional[Expr]
    for_expr: Optional[Expr]
    body: list            # List[Stmt]
    line: int


# ===========================================================================
# Statements
# ===========================================================================

@dataclass
class EvalStmt:
    """evaluate <expr>  — top-level only (spec §9)."""
    expr: Expr
    line: int


@dataclass
class LetStmt:
    """let <name> : <type> = <expr>"""
    name: str
    type_name: str
    expr: Expr
    line: int


@dataclass
class IfStmt:
    """if <expr> { <stmts> } [else { <stmts> }]  — braces mandatory (Decision #20)."""
    condition: Expr
    then_body: list       # List[Stmt]
    else_body: Optional[list]  # List[Stmt] or None
    line: int


@dataclass
class RepeatStmt:
    """repeat <expr> times { <stmts> }"""
    count: Expr
    body: list            # List[Stmt]
    line: int


@dataclass
class ForeachStmt:
    """foreach <name> in <expr> { <stmts> }"""
    var_name: str
    iterable: Expr
    body: list            # List[Stmt]
    line: int


@dataclass
class ReturnStmt:
    """return <expr>  — last statement of a function body."""
    expr: Expr
    line: int


@dataclass
class ActionStmt:
    """<action_verb>(<args>)  — step action (closed verb set, spec §8)."""
    verb: str
    args: list            # List[Expr]
    line: int


# ===========================================================================
# Expressions
# ===========================================================================

@dataclass
class BinaryOp:
    """Left-associative binary operation."""
    op: str               # '+' '-' '*' '/' '&&' '||'
    left: Expr
    right: Expr
    line: int


@dataclass
class CompareOp:
    """Non-associative comparison (Decision #17).
    op is one of: '<' '<=' '>' '>=' '==' '!='
    Chaining (a < b < c) is a parse error caught by the parser."""
    op: str
    left: Expr
    right: Expr
    line: int


@dataclass
class UnaryOp:
    """Unary '-' or '!' (level-1 precedence, right-associative)."""
    op: str               # '-' or '!'
    operand: Expr
    line: int


@dataclass
class QuantityOf:
    """quantity_of(<expr>) — unary operator, not a function call (spec §14 / Decision #34)."""
    operand: Expr
    line: int


@dataclass
class SubstituteCall:
    """substitute(<recipe>, IDENT, with: IDENT, ratio: <expr>) (spec §14 / Decision #35).
    original_name and replacement_name are bare identifier strings, not Expr nodes."""
    recipe: Expr
    original_name: str    # bare identifier text
    replacement_name: str # bare identifier text
    ratio: Expr
    line: int


@dataclass
class ScaleCall:
    """scale(<recipe>, by: <expr>)"""
    recipe: Expr
    by: Expr
    line: int


@dataclass
class FunctionCall:
    """<name>(<positional_args>)  — scalar helper function call."""
    name: str
    args: list            # List[Expr]
    line: int


@dataclass
class AmbiguousCall:
    """A zero-argument call foo() whose kind (recipe vs function)
    is resolved by the type checker via name-table lookup."""
    name: str
    line: int


@dataclass
class RecipeCall:
    """<name>(<keyword_args>)  — recipe instantiation."""
    name: str
    kwargs: list          # List[KwArg]
    line: int


@dataclass
class KwArg:
    """name: value pair inside a recipe call."""
    name: str
    value: Expr
    line: int


@dataclass
class Identifier:
    """A plain name reference."""
    name: str
    line: int


@dataclass
class IntLit:
    value: int
    line: int


@dataclass
class FloatLit:
    value: float
    line: int


@dataclass
class BoolLit:
    value: bool
    line: int


@dataclass
class StringLit:
    value: str
    line: int


@dataclass
class QuantityLit:
    """A two-token quantity literal: numeric_value unit (Decision #7)."""
    number: object        # int or float
    unit: str
    line: int


@dataclass
class ListLit:
    """[elem, elem, ...]  — homogeneous list literal."""
    elements: list        # List[Expr]
    line: int
