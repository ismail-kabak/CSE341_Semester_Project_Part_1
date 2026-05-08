"""ParseError — carries location and a useful description."""


class ParseError(Exception):
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
