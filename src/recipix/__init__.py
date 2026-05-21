"""
Recipix language package.

Public surface — what teammates should import from this package:

    from recipix import parse, check, run

* ``parse``  — Part 1, source → AST. Lexer/parser combined entry.
* ``check``  — Part 2, in-place type-check; annotates Expr nodes and
               resolves AmbiguousCall. Currently a stub.
* ``run``    — Part 2, evaluates a type-checked program and returns the
               list of rendered ``evaluate`` outputs. Currently a stub.

Stubs raise :class:`NotImplementedError`. Importing them does not.
"""

from .parser import parse
from .typechecker import check
from .interpreter import run

__all__ = ["parse", "check", "run"]
