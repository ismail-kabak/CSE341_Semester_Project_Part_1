import sys
sys.path.insert(0, 'src')
from lexer import Lexer, LexerError

def run(label, source):
    print(f"\n--- {label} ---")
    try:
        tokens = Lexer(source).tokenize()
        for t in tokens:
            print(t)
    except LexerError as e:
        print(f"ERROR: {e}")

# Multi-character operators and arrow
run("operators", "a == b != c <= d >= e -> float")

# Float literals
run("floats", "3.14 0.5 99.0")

# Boolean literals (must NOT be IDENT)
run("booleans", "true false")

# Comments are skipped
run("comment", "let x = 42 -- this is ignored\nprint x")

# Function signature
run("function", "function avg(t: table) -> float { return 0.0 }")

# Unexpected character triggers LexerError with line number
run("bad char", "let x = @")

# Unterminated string
run("bad string", 'let s = "hello')
