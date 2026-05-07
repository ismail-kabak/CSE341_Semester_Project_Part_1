"""
Recipix — Token definitions (shared between lexer and parser)

The parser imports Token and token-type constants from this module.
The lexer produces Token objects using these same constants.
Both modules must import from here — never define token types in two places.
"""


# ---------------------------------------------------------------------------
# Token class
# ---------------------------------------------------------------------------

class Token:
    def __init__(self, type: str, value, line: int):
        self.type  = type    # one of the constants below
        self.value = value   # Python value: int, float, str, bool, or lexeme str
        self.line  = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------
INT_LIT    = 'INT_LIT'      # 42
FLOAT_LIT  = 'FLOAT_LIT'   # 3.14
STRING_LIT = 'STRING_LIT'  # "Cook the pasta"
BOOL_LIT   = 'BOOL_LIT'    # true / false

# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------
IDENT = 'IDENT'

# ---------------------------------------------------------------------------
# Unit keywords  (lexer emits UNIT_KW; value is the unit string e.g. 'g')
# The parser combines  INT_LIT/FLOAT_LIT + UNIT_KW  into a QuantityLit node.
# ---------------------------------------------------------------------------
UNIT_KW = 'UNIT_KW'

UNIT_KEYWORDS = {
    'mg', 'g', 'kg',
    'ml', 'l', 'tsp', 'tbsp', 'cup',
    '°C',
    'min', 'hr',
    'count', 'pinch',
}

# ---------------------------------------------------------------------------
# Type-name keywords
# ---------------------------------------------------------------------------
TYPE_KW = 'TYPE_KW'   # value is the type name string e.g. 'Mass'

TYPE_KEYWORDS = {
    'int', 'float', 'bool',
    'Mass', 'Volume', 'Count', 'Temperature', 'Duration', 'Pinch',
}

# ---------------------------------------------------------------------------
# Action-verb keywords  (closed set of step actions)
# ---------------------------------------------------------------------------
ACTION_KW = 'ACTION_KW'   # value is the verb string e.g. 'combine'

ACTION_KEYWORDS = {
    'combine', 'mix', 'pour', 'melt', 'whisk',
    'blend', 'bake', 'flip', 'add',
    'sprinkle', 'drizzle', 'knead',
}

# ---------------------------------------------------------------------------
# Reserved keywords  (each gets its own token type = the keyword string)
# Parser matches on tok.type == 'recipe', tok.type == 'if', etc.
# ---------------------------------------------------------------------------
RESERVED_KEYWORDS = {
    'recipe', 'function', 'ingredient', 'step',
    'let', 'if', 'else',
    'repeat', 'times',
    'foreach', 'in',
    'at', 'for',
    'evaluate', 'scale', 'substitute',
    'serves', 'with', 'by', 'ratio',
    'return',
    'quantity_of',
}
# 'true' and 'false' are reserved but produce BOOL_LIT tokens, not keyword tokens.

# All reserved words the lexer must not treat as IDENT:
ALL_RESERVED = (
    RESERVED_KEYWORDS
    | TYPE_KEYWORDS
    | ACTION_KEYWORDS
    | UNIT_KEYWORDS
    | {'true', 'false'}
)

# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------
PLUS    = 'PLUS'    # +
MINUS   = 'MINUS'   # -
STAR    = 'STAR'    # *
SLASH   = 'SLASH'   # /
EQ      = 'EQ'      # ==
NEQ     = 'NEQ'     # !=
LT      = 'LT'      # <
LTE     = 'LTE'     # <=
GT      = 'GT'      # >
GTE     = 'GTE'     # >=
AND     = 'AND'     # &&
OR      = 'OR'      # ||
NOT     = 'NOT'     # !
ASSIGN  = 'ASSIGN'  # =

# ---------------------------------------------------------------------------
# Separators
# ---------------------------------------------------------------------------
LPAREN  = 'LPAREN'   # (
RPAREN  = 'RPAREN'   # )
LBRACE  = 'LBRACE'   # {
RBRACE  = 'RBRACE'   # }
LBRACKET = 'LBRACKET' # [
RBRACKET = 'RBRACKET' # ]
COMMA   = 'COMMA'    # ,
COLON   = 'COLON'    # :
ARROW   = 'ARROW'    # ->

# ---------------------------------------------------------------------------
# Special
# ---------------------------------------------------------------------------
EOF = 'EOF'
