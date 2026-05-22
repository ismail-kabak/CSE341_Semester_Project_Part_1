"""
Recipix Token contract — published for the lexer team.

The parser consumes Iterable[Token].  Every Token must carry:
  .type   (str)  — one of the constants below
  .value         — Python value (int, float, str, bool) or the lexeme string
  .line   (int)  — 1-based source line number
  .col    (int)  — 1-based column (0 if unavailable from the lexer)

The lexer team's src/tokens.py uses the same string constants for .type,
so their Token objects are accepted by the parser via duck typing.

Token type constants
--------------------
Literals:
  INT_LIT    — integer, e.g. 42         (.value is int)
  FLOAT_LIT  — float,   e.g. 3.14       (.value is float)
  STRING_LIT — string,  e.g. "Cook"     (.value is str, without quotes)
  BOOL_LIT   — boolean, true / false    (.value is bool)

Identifiers:
  IDENT      — user identifier           (.value is str)

Unit keywords  (spec §1):
  UNIT_KW    — mg g kg ml l tsp tbsp cup °C min hr count pinch  (.value is str)

Type-name keywords (spec §1):
  TYPE_KW    — int float bool Mass Volume Count Temperature Duration Pinch (.value is str)

Action-verb keywords (spec §1, closed set):
  ACTION_KW  — combine mix pour melt whisk blend bake flip add
               sprinkle drizzle knead                           (.value is str)

Reserved keywords — token .type IS the keyword string, e.g. 'recipe':
  recipe  function  ingredient  step
  let  if  else
  repeat  times
  foreach  in
  at  for
  evaluate  scale  substitute
  serves  with  by  ratio
  return
  quantity_of

Operators:
  PLUS MINUS STAR SLASH
  EQ NEQ LT LTE GT GTE
  AND OR NOT ASSIGN

Separators:
  LPAREN RPAREN LBRACE RBRACE LBRACKET RBRACKET
  COMMA COLON ARROW

Special:
  EOF
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: str    # one of the constants below
    value: object  # Python value or lexeme string
    line: int
    col: int = 0

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------
INT_LIT    = 'INT_LIT'
FLOAT_LIT  = 'FLOAT_LIT'
STRING_LIT = 'STRING_LIT'
BOOL_LIT   = 'BOOL_LIT'

# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------
IDENT = 'IDENT'

# ---------------------------------------------------------------------------
# Keyword-class tokens (single token type, value carries the word)
# ---------------------------------------------------------------------------
UNIT_KW   = 'UNIT_KW'
TYPE_KW   = 'TYPE_KW'
ACTION_KW = 'ACTION_KW'

UNIT_KEYWORDS = frozenset({
    'mg', 'g', 'kg',
    'ml', 'l', 'tsp', 'tbsp', 'cup',
    '°C',
    'min', 'hr',
    'count', 'pinch',
})

TYPE_KEYWORDS = frozenset({
    'int', 'float', 'bool',
    'Mass', 'Volume', 'Count', 'Temperature', 'Duration', 'Pinch',
})

ACTION_KEYWORDS = frozenset({
    'combine', 'mix', 'pour', 'melt', 'whisk',
    'blend', 'bake', 'flip', 'add',
    'sprinkle', 'drizzle', 'knead',
})

# ---------------------------------------------------------------------------
# Reserved keywords — each is its own token type (type == lexeme)
# ---------------------------------------------------------------------------
RESERVED_KEYWORDS = frozenset({
    'recipe', 'function', 'ingredient', 'step',
    'let', 'if', 'else',
    'repeat', 'times',
    'foreach', 'in',
    'at', 'for',
    'evaluate', 'scale', 'substitute',
    'serves', 'with', 'by', 'ratio',
    'return',
    'quantity_of',
})

# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------
PLUS   = 'PLUS'
MINUS  = 'MINUS'
STAR   = 'STAR'
SLASH  = 'SLASH'
EQ     = 'EQ'
NEQ    = 'NEQ'
LT     = 'LT'
LTE    = 'LTE'
GT     = 'GT'
GTE    = 'GTE'
AND    = 'AND'
OR     = 'OR'
NOT    = 'NOT'
ASSIGN = 'ASSIGN'

# ---------------------------------------------------------------------------
# Separators
# ---------------------------------------------------------------------------
LPAREN   = 'LPAREN'
RPAREN   = 'RPAREN'
LBRACE   = 'LBRACE'
RBRACE   = 'RBRACE'
LBRACKET = 'LBRACKET'
RBRACKET = 'RBRACKET'
COMMA    = 'COMMA'
COLON    = 'COLON'
ARROW    = 'ARROW'

# ---------------------------------------------------------------------------
# Special
# ---------------------------------------------------------------------------
EOF = 'EOF'
