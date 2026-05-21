"""
Recipix error hierarchy.

Three sibling exception types, one per language phase:

* ``ParseError``           — front-end (lexer/parser). Part 1, unchanged.
* ``TypeCheckError``       — middle-end (type checker). Part 2.
* ``RuntimeRecipixError``  — back-end (interpreter). Part 2.

The wire format for the three is kept aligned so a single CLI sink
(``__main__.py``) can stringify any of them uniformly:

    parse    error at line L, col C: <message>
    type     error at line L, col C: <message>
    runtime  error at line L: <message>             (no col)

Both Part 2 classes are additive — ``ParseError`` is untouched so the
Part 1 parser keeps working without changes.

Two lower-level ``KeyError`` subclasses, ``RedeclarationError`` and
``ShadowingError``, are raised by :mod:`recipix.environment` when the
scope chain detects a binding violation. The type checker is expected
to catch these and wrap-and-re-raise them as a ``TypeCheckError`` with
``error_code=5`` (single-assignment) or ``error_code=6`` (shadowing),
plus proper line/col, so the user sees the canonical
``type error at line X, col Y: ...`` format instead of a Python
traceback. They live in this module — not in ``environment.py`` —
because they belong to the error vocabulary of the language, not to
the data structure that happens to detect them.
"""


class ParseError(Exception):
    """Lexer/parser rejected this source. Part 1 contract — do not modify."""

    def __init__(self, line: int, col: int, message: str, *,
                 expected: str | None = None, got: str | None = None):
        self.line = line
        self.col = col
        self.message = message
        self.expected = expected
        self.got = got
        super().__init__(self._format())

    def _format(self) -> str:
        return f"parse error at line {self.line}, col {self.col}: {self.message}"


class TypeCheckError(Exception):
    """
    Type checker rejected this program.

    ``error_code`` indexes the spec §10 error table (1–19). Numbers
    1–18 were locked in the v4.1 spec; #19 ("return must appear only as
    the last statement of a function body") was added in the Part 2
    revision per plan §2.6. ``None`` is allowed for diagnostics that
    do not yet have a stable spec number.
    """

    def __init__(self, line: int, col: int, message: str,
                 error_code: int | None = None):
        self.line = line
        self.col = col
        self.message = message
        self.error_code = error_code
        super().__init__(self._format())

    def _format(self) -> str:
        return f"type error at line {self.line}, col {self.col}: {self.message}"


class RedeclarationError(KeyError):
    """
    Raised by :meth:`recipix.environment.Environment.define` when a
    name is already bound in the current scope (single-assignment
    violation — spec §10 error #5).

    The type checker catches this and re-raises as
    ``TypeCheckError(error_code=5)`` with proper line/col.
    """


class ShadowingError(KeyError):
    """
    Raised by :meth:`recipix.environment.Environment.declare_check`
    when a name is visible anywhere up the parent chain (no-shadowing
    violation — spec §10 error #6).

    The type checker catches this and re-raises as
    ``TypeCheckError(error_code=6)`` with proper line/col.
    """


class RuntimeRecipixError(Exception):
    """
    Interpreter rejected this program at run time.

    Covers the five runtime errors enumerated in spec §10
    ("Runtime errors"):

      1. division by zero
      2. negative repeat count
      3. negative or zero ``scale.by``
      4. ``substitute`` of an ingredient not in the recipe
      5. (reserved)

    No column is carried — runtime locations are statement-level at
    best, and many runtime errors arise from values whose token
    columns have long since been thrown away.
    """

    def __init__(self, line: int, message: str):
        self.line = line
        self.message = message
        super().__init__(self._format())

    def _format(self) -> str:
        return f"runtime error at line {self.line}: {self.message}"
