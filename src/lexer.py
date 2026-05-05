"""
DataScript Lexer
Converts source code (string) into a flat list of Token objects.
Raises LexerError with a line number on any unrecognised character.
"""


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

class Token:
    """A single lexical unit produced by the lexer."""

    def __init__(self, type: str, value, line: int):
        self.type = type    # e.g. 'INT_LIT', 'IDENT', 'SELECT', 'PLUS'
        self.value = value  # Python value: int, float, str, bool, or the lexeme string
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Reserved words
# ---------------------------------------------------------------------------

# Query and logic keywords (uppercase in source)
QUERY_KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'ORDER', 'BY', 'GROUP',
    'HAVING', 'AND', 'OR', 'NOT', 'ASC', 'DESC',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
}

# Statement and type keywords (lowercase in source)
STMT_KEYWORDS = {
    'table', 'load', 'let', 'print',
    'if', 'then', 'else', 'function', 'return',
    'int', 'float', 'string', 'bool',
}

# Boolean literals — reserved so they cannot be used as identifiers
BOOL_KEYWORDS = {'true', 'false'}

ALL_KEYWORDS = QUERY_KEYWORDS | STMT_KEYWORDS | BOOL_KEYWORDS

# Single-character operator/separator map
SINGLE_CHAR_TOKENS = {
    '<': 'LT',
    '>': 'GT',
    '=': 'ASSIGN',
    '+': 'PLUS',
    '-': 'MINUS',
    '*': 'STAR',
    '/': 'SLASH',
    '(': 'LPAREN',
    ')': 'RPAREN',
    '{': 'LBRACE',
    '}': 'RBRACE',
    ',': 'COMMA',
    ':': 'COLON',
}


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class LexerError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Lexer error at line {line}: {message}")
        self.line = line


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Hand-written lexer for DataScript.

    Design notes (Sebesta §3.1):
    - Token categories are defined by regular expressions; the lexer implements
      those automata directly as methods rather than using a regex engine, so
      that every decision is explicit and testable.
    - Maximal munch: two-character operators (==, !=, <=, >=, ->) are checked
      before their single-character prefixes.
    - Keywords are pre-empted: after reading an alphanumeric word the lexer
      checks the reserved-word table before emitting IDENT.
    """

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0):
        """Return character at pos+offset without advancing, or None at EOF."""
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else None

    def _advance(self) -> str:
        """Consume and return the current character; track newlines."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def _error(self, msg: str):
        raise LexerError(msg, self.line)

    # ------------------------------------------------------------------
    # Skipping
    # ------------------------------------------------------------------

    def _skip_whitespace_and_comments(self):
        """
        Skip spaces, tabs, newlines, and single-line comments (-- to EOL).
        Comments start with '--'; this is checked here so that '--' is never
        mistakenly split into MINUS MINUS by the operator scanner.
        """
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in ' \t\r\n':
                self._advance()
            elif ch == '-' and self._peek(1) == '-':
                # consume everything up to (but not including) the newline
                while self.pos < len(self.source) and self._peek() != '\n':
                    self._advance()
            else:
                break

    # ------------------------------------------------------------------
    # Scanners for individual token kinds
    # ------------------------------------------------------------------

    def _scan_number(self) -> Token:
        """
        Scan INT_LIT or FLOAT_LIT.
        FLOAT_LIT requires at least one digit after the decimal point,
        matching the regex: [0-9]+ '.' [0-9]+
        A lone trailing dot (e.g. '3.') is scanned as INT_LIT '3' followed
        by COLON or another token — not a float.
        """
        start = self.pos
        line = self.line
        while self._peek() is not None and self._peek().isdigit():
            self._advance()
        # Check for decimal point followed by digit (not just '.')
        if self._peek() == '.' and self._peek(1) is not None and self._peek(1).isdigit():
            self._advance()  # consume '.'
            while self._peek() is not None and self._peek().isdigit():
                self._advance()
            return Token('FLOAT_LIT', float(self.source[start:self.pos]), line)
        return Token('INT_LIT', int(self.source[start:self.pos]), line)

    def _scan_string(self) -> Token:
        """
        Scan STRING_LIT: opening '"' already peeked but not consumed.
        Newlines inside a string literal are a lexer error (Sebesta §3.1 —
        token patterns are single-line by convention in this language).
        """
        line = self.line
        self._advance()  # consume opening '"'
        chars = []
        while self.pos < len(self.source):
            ch = self._peek()
            if ch == '"':
                self._advance()  # consume closing '"'
                return Token('STRING_LIT', ''.join(chars), line)
            if ch == '\n':
                self._error("Unterminated string literal (newline inside string)")
            chars.append(self._advance())
        self._error("Unterminated string literal (reached end of file)")

    def _scan_word(self) -> Token:
        """
        Scan a word matching [a-zA-Z_][a-zA-Z0-9_]* and classify it as:
          - BOOL_LIT  for 'true' / 'false'
          - keyword token (type = the word itself) for all other reserved words
          - IDENT for user-defined names
        """
        start = self.pos
        line = self.line
        while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
            self._advance()
        word = self.source[start:self.pos]

        if word in BOOL_KEYWORDS:
            return Token('BOOL_LIT', word == 'true', line)   # value is Python bool
        if word in ALL_KEYWORDS:
            return Token(word, word, line)   # e.g. Token('SELECT', 'SELECT', 3)
        return Token('IDENT', word, line)

    # ------------------------------------------------------------------
    # Main tokeniser
    # ------------------------------------------------------------------

    def _next_token(self) -> Token:
        self._skip_whitespace_and_comments()

        if self.pos >= len(self.source):
            return Token('EOF', None, self.line)

        line = self.line
        ch = self._peek()

        # Numbers
        if ch.isdigit():
            return self._scan_number()

        # String literals
        if ch == '"':
            return self._scan_string()

        # Identifiers and keywords
        if ch.isalpha() or ch == '_':
            return self._scan_word()

        # --- Operators: check two-character sequences first (maximal munch) ---
        two = self.source[self.pos: self.pos + 2]
        if two == '==':
            self.pos += 2
            return Token('EQ', '==', line)
        if two == '!=':
            self.pos += 2
            return Token('NEQ', '!=', line)
        if two == '<=':
            self.pos += 2
            return Token('LTE', '<=', line)
        if two == '>=':
            self.pos += 2
            return Token('GTE', '>=', line)
        if two == '->':
            self.pos += 2
            return Token('ARROW', '->', line)

        # Single-character operators and separators
        if ch in SINGLE_CHAR_TOKENS:
            self._advance()
            return Token(SINGLE_CHAR_TOKENS[ch], ch, line)

        self._error(f"Unexpected character: {ch!r}")

    def tokenize(self) -> list:
        """Return the full token list including the final EOF token."""
        tokens = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.type == 'EOF':
                break
        return tokens
