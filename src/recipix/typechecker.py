"""
Recipix Part 2 type checker — public surface, body to be filled in.

Owner:   İsmail Kabak (1901042652)
Plan:    Implements plan §2.1 (in-place AST annotation with ``.inferred_type``
         on every Expr node; ``.resolved_kind`` on every ``AmbiguousCall``),
         §2.3 (action-verb signature classes: Heterogeneous / Homogeneous /
         Nullary), §2.6 (``serves`` evaluation timing + single-return
         enforcement), §5 (İsmail's task list).
Spec:    Enforces the 19 compile-time errors enumerated in spec §10
         (errors 1–18 from the v4.1 spec plus error #19, "return must
         appear only as the last statement of a function body", added
         in the Part 2 revision per plan §2.6).

Summary
-------
The checker is a tree-walking visitor (:class:`TypeChecker`) over the
AST produced by ``recipix.parser``. It:

1. Annotates every ``Expr`` node in-place with ``.inferred_type``.
2. Resolves every ``AmbiguousCall`` (a call whose target the parser
   could not classify as recipe-vs-function) by setting
   ``.resolved_kind`` to ``"recipe"`` or ``"function"``. This is the
   handoff Berk's interpreter depends on (plan §3).
3. Raises :class:`recipix.errors.TypeCheckError` on the first
   violation, with line + col + the §10 error number when applicable.

The checker mutates AST nodes in-place rather than producing a parallel
TypedAST — see plan §2.1 rationale.

Spec §10 error checklist (19 items — İsmail's working list)
-----------------------------------------------------------
  #1   dimension mismatch in BinaryOp / CompareOp
  #2   Pinch used in arithmetic
  #3   heterogeneous list literal
  #4   unknown identifier
  #5   single-assignment violation (re-declare in same scope)
  #6   shadowing (re-declare visible from any ancestor scope)
  #7   non-bool in ``if`` condition
  #8   non-int (or negative-at-typecheck-time? — runtime) in ``repeat`` count
  #9   non-list in ``foreach`` source
  #10  non-Temperature in step ``at`` modifier
  #11  non-Duration in step ``for`` modifier
  #12  wrong arity in recipe or function call
  #13  wrong argument types in recipe or function call (incl. action verbs)
  #14  ``substitute`` of an unknown ingredient
  #15  float→int coercion attempted in a non-int context
  #16  ``substitute`` swaps Pinch ↔ Quantity
  #17  ``quantity_of(...)`` of a non-IDENT slot (already caught by parser)
  #18  ``quantity_of`` on a non-Ingredient
  #19  ``return`` appearing other than as the last statement of a function
       body (added in the Part 2 revision, plan §2.6)
"""

from __future__ import annotations

from .ast_nodes import Program
from .errors import TypeCheckError  # re-export hint for callers


def check(program: Program) -> Program:
    """
    Type-check ``program`` in-place and return the same object.

    On success, every ``Expr`` node carries an ``inferred_type`` string
    and every ``AmbiguousCall`` node has been replaced (or annotated)
    with its ``resolved_kind``. On failure, raises
    :class:`recipix.errors.TypeCheckError` for the first §10 violation
    found.

    Not yet implemented — body lands in the typechecker milestone.
    """
    raise NotImplementedError("recipix.typechecker.check is not implemented yet")


class TypeChecker:
    """
    Visitor for type-checking a Recipix :class:`~recipix.ast_nodes.Program`.

    Method dispatch is by AST node class name: ``_check_<ClassName>``.
    Each method either returns the inferred type string (for ``Expr``
    nodes) or ``None`` (for statement nodes), and may mutate the node
    in place to record annotations.

    Dispatch table (full surface)
    -----------------------------
    Top-level / declarations
      _check_Program, _check_RecipeDecl, _check_FunctionDecl,
      _check_IngredientDecl, _check_StepDecl, _check_Param
    Statements
      _check_EvalStmt, _check_LetStmt, _check_IfStmt, _check_RepeatStmt,
      _check_ForeachStmt, _check_ReturnStmt, _check_ActionStmt
    Expressions
      _check_BinaryOp, _check_CompareOp, _check_UnaryOp, _check_QuantityOf,
      _check_SubstituteCall, _check_ScaleCall, _check_FunctionCall,
      _check_AmbiguousCall, _check_RecipeCall, _check_KwArg,
      _check_Identifier, _check_IntLit, _check_FloatLit, _check_BoolLit,
      _check_StringLit, _check_QuantityLit, _check_ListLit
    """

    def __init__(self) -> None:
        # Symbol tables, evaluate-only flag, function-return-context, etc.
        # populated when the checker actually runs.
        raise NotImplementedError(
            "recipix.typechecker.TypeChecker.__init__ is not implemented yet"
        )

    # -- top-level dispatch -------------------------------------------------

    def check(self, program: Program) -> Program:
        raise NotImplementedError("TypeChecker.check is not implemented yet")

    # -- declarations -------------------------------------------------------

    def _check_Program(self, node):
        raise NotImplementedError

    def _check_RecipeDecl(self, node):
        raise NotImplementedError

    def _check_FunctionDecl(self, node):
        # NB: error #19 (single-return) is enforced at *entry* here,
        # before walking the body — see plan §2.6.
        raise NotImplementedError

    def _check_IngredientDecl(self, node):
        raise NotImplementedError

    def _check_StepDecl(self, node):
        raise NotImplementedError

    def _check_Param(self, node):
        raise NotImplementedError

    # -- statements ---------------------------------------------------------

    def _check_EvalStmt(self, node):
        # Sets the ``in_evaluate`` flag for the duration of the inner
        # expression; ``scale`` and ``substitute`` are legal only while
        # this flag is true (plan §5 task 4).
        raise NotImplementedError

    def _check_LetStmt(self, node):
        raise NotImplementedError

    def _check_IfStmt(self, node):
        raise NotImplementedError

    def _check_RepeatStmt(self, node):
        raise NotImplementedError

    def _check_ForeachStmt(self, node):
        raise NotImplementedError

    def _check_ReturnStmt(self, node):
        raise NotImplementedError

    def _check_ActionStmt(self, node):
        # Dispatches on the verb's class (Heterogeneous / Homogeneous /
        # Nullary) per plan §2.3.
        raise NotImplementedError

    # -- expressions --------------------------------------------------------

    def _check_BinaryOp(self, node):
        raise NotImplementedError

    def _check_CompareOp(self, node):
        raise NotImplementedError

    def _check_UnaryOp(self, node):
        raise NotImplementedError

    def _check_QuantityOf(self, node):
        raise NotImplementedError

    def _check_SubstituteCall(self, node):
        raise NotImplementedError

    def _check_ScaleCall(self, node):
        raise NotImplementedError

    def _check_FunctionCall(self, node):
        raise NotImplementedError

    def _check_AmbiguousCall(self, node):
        # Resolves to FunctionCall vs RecipeCall by looking up the
        # callee name in the symbol table. Sets ``.resolved_kind``.
        # This is the deliverable Berk's interpreter blocks on
        # (plan §3, Thu 21 May 12:00).
        raise NotImplementedError

    def _check_RecipeCall(self, node):
        raise NotImplementedError

    def _check_KwArg(self, node):
        raise NotImplementedError

    def _check_Identifier(self, node):
        raise NotImplementedError

    def _check_IntLit(self, node):
        raise NotImplementedError

    def _check_FloatLit(self, node):
        raise NotImplementedError

    def _check_BoolLit(self, node):
        raise NotImplementedError

    def _check_StringLit(self, node):
        raise NotImplementedError

    def _check_QuantityLit(self, node):
        raise NotImplementedError

    def _check_ListLit(self, node):
        raise NotImplementedError


__all__ = ["check", "TypeChecker", "TypeCheckError"]
