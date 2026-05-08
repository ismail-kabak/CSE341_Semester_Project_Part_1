"""CLI entry point: python -m recipix <file.rcx> [--dump-ast]"""

import sys
import os
import argparse

# Allow importing the sibling src/lexer.py when running from src/ or the project root
_src = os.path.dirname(os.path.dirname(__file__))
if _src not in sys.path:
    sys.path.insert(0, _src)

from .parser import parse
from .errors import ParseError
from .pretty import dump


def _get_tokens(source: str, filename: str):
    """Tokenize source using the project's lexer (src/lexer.py).
    Falls back to a minimal stub if the lexer is not importable."""
    try:
        from lexer import Lexer
        return Lexer(source).tokenize()
    except ImportError:
        sys.exit(
            f"error: could not import 'lexer' from {_src!r}.\n"
            f"Make sure src/lexer.py exists (lexer team deliverable) and "
            f"you are running from the src/ directory or the project root."
        )


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="recipix",
        description="Recipix parser — parse a .rcx source file.",
    )
    ap.add_argument("file", help="Source file (.rcx)")
    ap.add_argument("--dump-ast", action="store_true",
                    help="Pretty-print the AST to stdout")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as fh:
            source = fh.read()
    except OSError as e:
        sys.exit(f"error: {e}")

    tokens = _get_tokens(source, args.file)

    try:
        ast = parse(tokens)
    except ParseError as e:
        sys.exit(str(e))

    if args.dump_ast:
        print(dump(ast))
    else:
        print(f"OK — parsed {args.file}")


if __name__ == "__main__":
    main()
