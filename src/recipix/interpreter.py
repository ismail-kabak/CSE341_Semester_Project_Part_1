"""
Recipix Part 2 interpreter — public surface, body to be filled in.

Owner:   Berk Hakan Öge (210104004132)
Plan:    Implements plan §2.2 (runtime value shapes — from
         :mod:`recipix.runtime_values`), §2.4 (normalization location —
         the interpreter normalizes ``QuantityLit`` to base unit at
         evaluation time), §2.5 (environment chain — from
         :mod:`recipix.environment`), §2.6 (``serves`` evaluated once
         at recipe instantiation; ``scale``-servings uses banker's
         rounding via ``int(round(servings * by))``), §4 (Berk's
         task list).

Summary
-------
The interpreter is a tree-walking evaluator over the AST produced by
``recipix.parser`` and annotated by ``recipix.typechecker``. It
assumes the input has already been type-checked: every ``Expr`` node
has ``.inferred_type``, every ``AmbiguousCall`` has ``.resolved_kind``,
and the 19 spec §10 compile-time errors are guaranteed not to occur.

The interpreter therefore concerns itself only with the **five spec
§10 runtime errors**:

  R1   division by zero
  R2   negative repeat count
  R3   ``scale`` ``by`` ≤ 0 (negative or zero scale factor)
  R4   ``substitute`` of an ingredient not in the recipe (computed at
       run time when the ``original_name`` is itself the result of
       an expression — most cases are caught statically as #14)
  R5   (reserved)

Plus the locked rounding rule from plan §2.6: ``scale`` servings is
``int(round(servings * by))`` — banker's rounding after multiply.

Output is collected from every ``EvalStmt`` and returned as a list of
strings (one per ``evaluate``).
"""

from __future__ import annotations

from .ast_nodes import Program
from .errors import RuntimeRecipixError  # re-export hint for callers


def run(program: Program, *, render_output: bool = True) -> list[str]:
    """
    Execute ``program`` and return the list of rendered output strings.

    The input is assumed to have been type-checked (see
    :func:`recipix.typechecker.check`) so that every ``AmbiguousCall``
    has a ``.resolved_kind`` and every ``Expr`` carries a sensible
    ``.inferred_type``. Behaviour on un-checked input is undefined.

    ``render_output`` toggles whether ``RtRecipe`` values are stringified
    via :mod:`recipix.rendering`. When ``False``, ``evaluate`` is run
    purely for side effects (none, currently — Recipix is pure) and the
    returned list will contain raw ``repr``-like strings.

    Raises :class:`recipix.errors.RuntimeRecipixError` on the first
    runtime violation.

    Not yet implemented.
    """
    raise NotImplementedError("recipix.interpreter.run is not implemented yet")


class Interpreter:
    """
    Tree-walking evaluator. Method dispatch by AST class name:
    ``_eval_<ClassName>``. Returns a Python-native or
    :mod:`recipix.runtime_values` value for ``Expr`` nodes; ``None``
    for statement nodes (statements have no value in Recipix).

    Dispatch table (full surface)
    -----------------------------
    Top-level / declarations
      _eval_Program, _eval_RecipeDecl, _eval_FunctionDecl
      (RecipeDecl/FunctionDecl just bind the declaration into the
      global environment; instantiation happens at call site.)
    Statements
      _eval_EvalStmt, _eval_LetStmt, _eval_IfStmt, _eval_RepeatStmt,
      _eval_ForeachStmt, _eval_ReturnStmt, _eval_ActionStmt
    Expressions
      _eval_BinaryOp, _eval_CompareOp, _eval_UnaryOp, _eval_QuantityOf,
      _eval_SubstituteCall, _eval_ScaleCall, _eval_FunctionCall,
      _eval_RecipeCall, _eval_KwArg, _eval_Identifier,
      _eval_IntLit, _eval_FloatLit, _eval_BoolLit, _eval_StringLit,
      _eval_QuantityLit, _eval_ListLit

    ``AmbiguousCall`` does not have its own ``_eval_`` method: by the
    time the interpreter runs, every ``AmbiguousCall`` is treated as
    its ``resolved_kind`` and dispatched to ``_eval_FunctionCall`` or
    ``_eval_RecipeCall`` accordingly.
    """

    class ReturnException(Exception):
        """Internal: carries a function return value up through the call stack."""
        __slots__ = ("value",)
        def __init__(self, value):
            self.value = value
            super().__init__()

    def __init__(self) -> None:
        raise NotImplementedError(
            "recipix.interpreter.Interpreter.__init__ is not implemented yet"
        )

    # -- top-level dispatch -------------------------------------------------

    def run(self, program: Program, *, render_output: bool = True) -> list[str]:
        raise NotImplementedError("Interpreter.run is not implemented yet")

    # -- declarations -------------------------------------------------------

    def _eval_Program(self, node):
        raise NotImplementedError

    def _eval_RecipeDecl(self, node):
        raise NotImplementedError

    def _eval_FunctionDecl(self, node):
        raise NotImplementedError

    # -- statements ---------------------------------------------------------

    def _eval_EvalStmt(self, node):
        raise NotImplementedError

    def _eval_LetStmt(self, node):
        raise NotImplementedError

    def _eval_IfStmt(self, node):
        raise NotImplementedError

    def _eval_RepeatStmt(self, node):
        # Runtime error R2: negative repeat count.
        raise NotImplementedError

    def _eval_ForeachStmt(self, node):
        raise NotImplementedError

    def _eval_ReturnStmt(self, node):
        # Raises self.ReturnException, caught at FunctionCall.
        raise NotImplementedError

    def _eval_ActionStmt(self, node):
        raise NotImplementedError

    # -- expressions --------------------------------------------------------

    def _eval_BinaryOp(self, node):
        # Runtime error R1: division by zero.
        raise NotImplementedError

    def _eval_CompareOp(self, node):
        raise NotImplementedError

    def _eval_UnaryOp(self, node):
        raise NotImplementedError

    def _eval_QuantityOf(self, node):
        raise NotImplementedError

    def _eval_SubstituteCall(self, node):
        # Runtime error R4: substitute of unknown ingredient
        # (rare — most cases caught statically as #14).
        raise NotImplementedError

    def _eval_ScaleCall(self, node):
        # Runtime error R3: by ≤ 0.
        # Rounding rule: int(round(servings * by)) — banker's rounding
        # after multiply (plan §2.6).
        raise NotImplementedError

    def _eval_FunctionCall(self, node):
        raise NotImplementedError

    def _eval_RecipeCall(self, node):
        # serves expression evaluated here, once, with kwargs bound
        # into the new scope (plan §2.6). Result stored in
        # RtRecipe.servings.
        raise NotImplementedError

    def _eval_KwArg(self, node):
        raise NotImplementedError

    def _eval_Identifier(self, node):
        raise NotImplementedError

    def _eval_IntLit(self, node):
        raise NotImplementedError

    def _eval_FloatLit(self, node):
        raise NotImplementedError

    def _eval_BoolLit(self, node):
        raise NotImplementedError

    def _eval_StringLit(self, node):
        raise NotImplementedError

    def _eval_QuantityLit(self, node):
        # Normalize to base unit here (plan §2.4) via
        # recipix.runtime_values.normalize_to_base.
        raise NotImplementedError

    def _eval_ListLit(self, node):
        raise NotImplementedError


__all__ = ["run", "Interpreter", "RuntimeRecipixError"]
