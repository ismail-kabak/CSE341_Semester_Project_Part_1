"""
DataScript — entry point
Usage:
    python main.py <source_file>             # parse and check for errors
    python main.py --dump-ast <source_file>  # parse and print the AST
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lexer import Lexer, LexerError
from parser import Parser, ParseError


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: python main.py [--dump-ast] <source_file>")
        sys.exit(1)

    dump_ast = False
    if args[0] == '--dump-ast':
        dump_ast = True
        args = args[1:]

    if not args:
        print("Error: no source file provided")
        sys.exit(1)

    source_file = args[0]
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {source_file}")
        sys.exit(1)

    # --- Lex ---
    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        print(e)
        sys.exit(1)

    # --- Parse ---
    try:
        ast = Parser(tokens).parse()
    except ParseError as e:
        print(e)
        sys.exit(1)

    # --- Output ---
    if dump_ast:
        print(ast.dump())
    else:
        print("OK — program parsed successfully.")


if __name__ == '__main__':
    main()
