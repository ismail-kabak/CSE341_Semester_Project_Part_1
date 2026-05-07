import sys
sys.path.insert(0, 'src')
from lexer import Lexer, LexerError

def run(label, source):
    print(f"\n--- {label} ---")
    try:
        for t in Lexer(source).tokenize():
            print(t)
    except LexerError as e:
        print(f"ERROR: {e}")

# Test 1: degree C unit + step modifiers
run("degree C and step", 'step "Cook" at 180 °C for 3 min { bake() }')

# Test 2: boolean literals and logical operators
run("booleans and operators", 'let x : bool = true && false || !true')

# Test 3: float quantity
run("float quantity", 'ingredient milk : 1.5 kg')

# Test 4: substitute call structure
run("substitute", 'substitute(r, flour, with: oat_milk, ratio: 1.0)')

# Test 5: comment skipping
run("comment", '// this is a comment\nlet x : int = 42')

# Test 6: unexpected character
run("bad char", 'let x = @')

# Test 7: unterminated string
run("bad string", 'step "unclosed')

# Test 8: lone degree symbol
run("lone degree", 'let x = °')
