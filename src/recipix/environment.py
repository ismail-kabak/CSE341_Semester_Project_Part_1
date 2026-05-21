"""
Lexical-scope environment chain for Recipix Part 2.

Owner:   Berk Hakan Öge (210104004132), drafts; İsmail Kabak (1901042652) reviews.
Status:  Joint module — both the type checker and the interpreter
         instantiate this class.
Plan:    Implements plan §2.5 (environment chain, single-assignment +
         no-shadowing enforcement, parameter-list-scope-equals-body-scope).

Summary
-------
A simple parent-pointer chain of name -> value scopes, deliberately
**type-agnostic**: the type checker stores type strings as values and
the interpreter stores runtime values from
:mod:`recipix.runtime_values`. Same scoping logic — no duplicated
walks, no separate "TypeEnvironment" / "RuntimeEnvironment" subclasses.

Single-assignment and no-shadowing enforcement lives in the type
checker via :meth:`declare_check` *before* every :meth:`define`. The
interpreter does not call :meth:`declare_check` — by the time the
interpreter runs, the program has been type-checked and shadowing /
redeclaration cannot occur.

Scope convention (plan §2.5 / Phase 0 §10.8): a function's or recipe's
parameters are declared into the same scope as the body. So
``function f(x: int) { let x : int = 1 }`` is a shadowing error, not a
fresh binding in a nested scope.
"""

from __future__ import annotations

from typing import Any, Optional


class RedeclarationError(KeyError):
    """Raised by :meth:`Environment.define` when a name is already in this scope."""


class ShadowingError(KeyError):
    """Raised by :meth:`Environment.declare_check` when a name is visible up-chain."""


class Environment:
    """
    A single lexical scope chained to an optional parent.

    The class is type-agnostic — both ``define("x", "int")`` (checker)
    and ``define("x", RtQuantity(1.0, "Mass"))`` (interpreter) are
    valid uses. No type annotation is placed on the ``value`` parameter
    of :meth:`define` for that reason.
    """

    __slots__ = ("_bindings", "parent")

    def __init__(self, parent: Optional["Environment"] = None):
        self._bindings: dict[str, Any] = {}
        self.parent: Optional["Environment"] = parent

    # -- introspection ------------------------------------------------------

    def has_local(self, name: str) -> bool:
        """Is ``name`` bound in *this* scope (not an ancestor)?"""
        return name in self._bindings

    def has_visible(self, name: str) -> bool:
        """Is ``name`` visible anywhere up the parent chain?"""
        env: Optional[Environment] = self
        while env is not None:
            if name in env._bindings:
                return True
            env = env.parent
        return False

    # -- mutation -----------------------------------------------------------

    def define(self, name: str, value: Any) -> None:
        """
        Bind ``name`` to ``value`` in *this* scope.

        Raises :class:`RedeclarationError` (a ``KeyError`` subclass) if
        ``name`` is already bound in this scope. This is the
        single-assignment rule from spec §6 / §10 error #5.

        Note: this method does **not** check ancestor scopes. The
        no-shadowing rule (spec §10 error #6) is the type checker's
        responsibility — it calls :meth:`declare_check` first.
        """
        if name in self._bindings:
            raise RedeclarationError(
                f"name {name!r} is already declared in this scope"
            )
        self._bindings[name] = value

    def declare_check(self, name: str) -> None:
        """
        Pre-flight check: would defining ``name`` here be a shadowing
        violation? Raises :class:`ShadowingError` if ``name`` is
        visible anywhere up the chain (including this scope, in which
        case it is a redeclaration).

        Called by the type checker before every :meth:`define`. The
        interpreter does not call this method — by the time the
        interpreter runs, the program is known to be free of shadowing
        violations.
        """
        if self.has_visible(name):
            raise ShadowingError(
                f"name {name!r} shadows an existing binding"
            )

    # -- lookup -------------------------------------------------------------

    def lookup(self, name: str) -> Any:
        """
        Resolve ``name`` against this scope and all ancestors. Raises
        ``KeyError`` if not found anywhere in the chain.
        """
        env: Optional[Environment] = self
        while env is not None:
            if name in env._bindings:
                return env._bindings[name]
            env = env.parent
        raise KeyError(f"unknown identifier: {name!r}")

    # -- ergonomics ---------------------------------------------------------

    def child(self) -> "Environment":
        """Convenience: open a new scope with ``self`` as the parent."""
        return Environment(parent=self)

    def __contains__(self, name: str) -> bool:
        return self.has_visible(name)

    def __repr__(self) -> str:
        depth = 0
        env: Optional[Environment] = self
        while env is not None:
            depth += 1
            env = env.parent
        return f"<Environment depth={depth} local={list(self._bindings)!r}>"
