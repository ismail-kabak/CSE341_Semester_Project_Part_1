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
