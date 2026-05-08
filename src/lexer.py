"""
Recipix Lexer
Converts source code (str) into a flat list of Token objects.
Raises LexerError with a line number on any unrecognised character.

Integration note for parser:
  - Quantity literals are TWO tokens: INT_LIT/FLOAT_LIT followed by UNIT_KW.
    The parser combines them into a QuantityLit AST node.
  - true/false produce BOOL_LIT tokens (value is Python bool), not IDENT.
  - Reserved keywords produce Token(keyword_str, keyword_str, line).
    e.g. Token('recipe', 'recipe', 3)
  - Type-name keywords produce Token(TYPE_KW, name_str, line).
    e.g. Token(TYPE_KW, 'Mass', 5)
  - Action-verb keywords produce Token(ACTION_KW, verb_str, line).
    e.g. Token(ACTION_KW, 'combine', 7)
  - Unit keywords produce Token(UNIT_KW, unit_str, line).
    e.g. Token(UNIT_KW, 'g', 4)
"""

from recipix.tokens import (
    Token,
    IDENT, INT_LIT, FLOAT_LIT, STRING_LIT, BOOL_LIT,
    UNIT_KW, UNIT_KEYWORDS,
    TYPE_KW, TYPE_KEYWORDS,
    ACTION_KW, ACTION_KEYWORDS,
    RESERVED_KEYWORDS,
    PLUS, MINUS, STAR, SLASH,
    EQ, NEQ, LT, LTE, GT, GTE,
    AND, OR, NOT, ASSIGN,
    LPAREN, RPAREN, LBRACE, RBRACE,
    LBRACKET, RBRACKET,
    COMMA, COLON, ARROW,
    EOF,
)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class LexerError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Lexer error at line {line}: {message}")
        self.line = line


# ---------------------------------------------------------------------------
# Single-character operator/separator map
# ---------------------------------------------------------------------------

SINGLE_CHAR = {
    '+': PLUS,
    '*': STAR,
    '/': SLASH,
    '(': LPAREN,
    ')': RPAREN,
    '{': LBRACE,
    '}': RBRACE,
    '[': LBRACKET,
    ']': RBRACKET,
    ',': COMMA,
    ':': COLON,
}


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Hand-written lexer for Recipix (spec §1).

    Maximal munch ordering:
      1. Two-char operators first: ==, !=, <=, >=, &&, ||, ->
      2. Single-char operators and separators

    Keyword pre-emption ordering (on a scanned word):
      true/false  → BOOL_LIT
      unit        → UNIT_KW
      type-name   → TYPE_KW
      action-verb → ACTION_KW
      reserved    → Token(word, word, line)
      else        → IDENT
    """

    def __init__(self, source: str):
        self.source = source
        self.pos    = 0
        self.line   = 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0):
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else None

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def _error(self, msg: str):
        raise LexerError(msg, self.line)

    # ------------------------------------------------------------------
    # Skip whitespace and // comments
    # ------------------------------------------------------------------

    def _skip(self):
        """
        Skip spaces, tabs, newlines, and single-line comments.
        Comments start with '//' (not to be confused with the '/' operator).
        Checked here so that '//' never reaches the operator scanner.
        """
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in ' \t\r\n':
                self._advance()
            elif ch == '/' and self._peek(1) == '/':
                while self.pos < len(self.source) and self._peek() != '\n':
                    self._advance()
            else:
                break

    # ------------------------------------------------------------------
    # Scanners
    # ------------------------------------------------------------------

    def _scan_number(self) -> Token:
        """
        Scan INT_LIT or FLOAT_LIT.
        Does NOT consume a following unit keyword — that is a separate token.
        The parser combines (INT_LIT | FLOAT_LIT) + UNIT_KW into QuantityLit.

        Decision #7: a numeric literal and its unit keyword MUST be separated
        by at least one whitespace character or a // comment.
        '200g' with no separator is a lexical error.
        """
        start = self.pos
        line  = self.line
        while self._peek() is not None and self._peek().isdigit():
            self._advance()
        if self._peek() == '.' and self._peek(1) is not None and self._peek(1).isdigit():
            self._advance()  # consume '.'
            while self._peek() is not None and self._peek().isdigit():
                self._advance()
            self._check_no_unit_glued(start)
            return Token(FLOAT_LIT, float(self.source[start:self.pos]), line)
        self._check_no_unit_glued(start)
        return Token(INT_LIT, int(self.source[start:self.pos]), line)

    def _check_no_unit_glued(self, num_start: int):
        """
        Raise LexerError only when a unit keyword immediately follows the number
        with no whitespace (decision #7: '200g' is a lexical error).
        A non-unit identifier like '200foo' is NOT an error — it tokenizes as
        INT_LIT(200) followed by IDENT('foo') on the next call.
        """
        nxt = self._peek()
        if nxt is None:
            return
        if nxt == '°':
            # '°' can only start '°C' — always a unit, always an error
            num_text = self.source[num_start:self.pos]
            self._error(
                f"Missing separator between number and unit: '{num_text} °C'. "
                f"Write '{num_text} °C' with a space (spec decision #7)."
            )
        if nxt.isalpha() or nxt == '_':
            # Scan ahead (without consuming) to get the full word
            p = self.pos
            while p < len(self.source) and (self.source[p].isalnum() or self.source[p] == '_'):
                p += 1
            word = self.source[self.pos:p]
            if word in UNIT_KEYWORDS:
                num_text = self.source[num_start:self.pos]
                self._error(
                    f"Missing separator between number and unit: '{num_text}{word}'. "
                    f"Write '{num_text} {word}' with a space (spec decision #7)."
                )

    def _scan_string(self) -> Token:
        """
        Scan STRING_LIT: "..."
        UTF-8 contents; any character except '"' and newline is allowed.
        No escape sequences in v1.
        """
        line = self.line
        self._advance()  # consume opening '"'
        chars = []
        while self.pos < len(self.source):
            ch = self._peek()
            if ch == '"':
                self._advance()
                return Token(STRING_LIT, ''.join(chars), line)
            if ch == '\n':
                self._error("Unterminated string literal (newline inside string)")
            chars.append(self._advance())
        self._error("Unterminated string literal (reached end of file)")

    def _scan_word(self) -> Token:
        """
        Scan a word [a-zA-Z_][a-zA-Z0-9_]* and classify:
          true/false    → BOOL_LIT
          unit keyword  → UNIT_KW
          type keyword  → TYPE_KW
          action verb   → ACTION_KW
          reserved word → Token(word, word, line)   e.g. Token('recipe',...)
          user name     → IDENT
        """
        start = self.pos
        line  = self.line
        while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
            self._advance()
        word = self.source[start:self.pos]

        if word == 'true':
            return Token(BOOL_LIT, True, line)
        if word == 'false':
            return Token(BOOL_LIT, False, line)
        if word in UNIT_KEYWORDS:
            return Token(UNIT_KW, word, line)
        if word in TYPE_KEYWORDS:
            return Token(TYPE_KW, word, line)
        if word in ACTION_KEYWORDS:
            return Token(ACTION_KW, word, line)
        if word in RESERVED_KEYWORDS:
            return Token(word, word, line)   # token type IS the keyword
        return Token(IDENT, word, line)

    def _scan_degree_c(self) -> Token:
        """
        Scan the '°C' unit token.
        Called when current char is '°' (U+00B0).
        The degree symbol cannot appear standalone — 'C' must follow.
        """
        line = self.line
        self._advance()  # consume '°'
        if self._peek() != 'C':
            self._error("'°' must be followed by 'C' to form the '°C' unit token")
        self._advance()  # consume 'C'
        return Token(UNIT_KW, '°C', line)

    # ------------------------------------------------------------------
    # Main token scanner
    # ------------------------------------------------------------------

    def _next_token(self) -> Token:
        self._skip()

        if self.pos >= len(self.source):
            return Token(EOF, None, self.line)

        line = self.line
        ch   = self._peek()

        # Degree symbol → °C unit token
        if ch == '°':
            return self._scan_degree_c()

        # Numbers
        if ch.isdigit():
            return self._scan_number()

        # Strings
        if ch == '"':
            return self._scan_string()

        # Words (identifiers, keywords)
        if ch.isalpha() or ch == '_':
            return self._scan_word()

        # --- Multi-character tokens first (maximal munch) ---

        two = self.source[self.pos: self.pos + 2]

        if two == '==':
            self.pos += 2; return Token(EQ,    '==', line)
        if two == '!=':
            self.pos += 2; return Token(NEQ,   '!=', line)
        if two == '<=':
            self.pos += 2; return Token(LTE,   '<=', line)
        if two == '>=':
            self.pos += 2; return Token(GTE,   '>=', line)
        if two == '&&':
            self.pos += 2; return Token(AND,   '&&', line)
        if two == '||':
            self.pos += 2; return Token(OR,    '||', line)
        if two == '->':
            self.pos += 2; return Token(ARROW, '->', line)

        # Single-character: - < > = ! first checked for non-two-char cases
        if ch == '-':
            self._advance(); return Token(MINUS,  '-', line)
        if ch == '<':
            self._advance(); return Token(LT,     '<', line)
        if ch == '>':
            self._advance(); return Token(GT,     '>', line)
        if ch == '=':
            self._advance(); return Token(ASSIGN, '=', line)
        if ch == '!':
            self._advance(); return Token(NOT,    '!', line)

        # Remaining single-char operators and separators
        if ch in SINGLE_CHAR:
            self._advance()
            return Token(SINGLE_CHAR[ch], ch, line)

        self._error(f"Unexpected character: {ch!r}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> list:
        """Return the complete token list, ending with an EOF token."""
        tokens = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.type == EOF:
                break
        return tokens
