"""CLI entry point: python -m recipix <file.rcx> [--dump-ast | --typecheck | --run]

Modes (mutually exclusive — the first one supplied wins, with the
unflagged default being "parse only"):

* (no flag)      parse the file, print "OK — parsed <path>"
* --dump-ast     parse, pretty-print the AST to stdout
* --typecheck    parse + type-check, print "OK" or the type error
* --run          parse + type-check + interpret, print the rendered output

``--typecheck`` and ``--run`` will fail with NotImplementedError until
the Part 2 type checker and interpreter land; both stubs sit behind
:mod:`recipix.typechecker` and :mod:`recipix.interpreter`. The plumbing
is intentionally wired up now so the CLI works the moment those
modules are implemented.
"""

import sys
import os
import argparse

# Allow importing the sibling src/lexer.py when running from src/ or the project root
_src = os.path.dirname(os.path.dirname(__file__))
if _src not in sys.path:
    sys.path.insert(0, _src)

from .parser import parse
from .typechecker import check
from .interpreter import run
from .errors import ParseError, TypeCheckError, RuntimeRecipixError
from .pretty import dump


def _get_tokens(source: str, filename: str):
    """Tokenize source using the project's lexer (src/lexer.py)."""
    try:
        from lexer import Lexer, LexerError
    except ImportError:
        sys.exit(
            f"error: could not import 'lexer' from {_src!r}.\n"
            f"Make sure src/lexer.py exists (lexer team deliverable) and "
            f"you are running from the src/ directory or the project root."
        )
    try:
        return Lexer(source).tokenize()
    except LexerError as e:
        sys.exit(str(e))


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="recipix",
        description="Recipix front- and back-end driver — parse, type-check, and interpret .rcx files.",
    )
    ap.add_argument("file", help="Source file (.rcx)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dump-ast", action="store_true",
                      help="Pretty-print the AST to stdout (parse only).")
    mode.add_argument("--typecheck", action="store_true",
                      help="Parse and type-check; print 'OK' on success "
                           "or the first type error.")
    mode.add_argument("--run", action="store_true",
                      help="Parse, type-check, and interpret; print the "
                           "rendered output of each 'evaluate' statement.")
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
        return

    if args.typecheck:
        try:
            check(ast)
        except TypeCheckError as e:
            sys.exit(str(e))
        print(f"OK — type-checked {args.file}")
        return

    if args.run:
        try:
            check(ast)
        except TypeCheckError as e:
            sys.exit(str(e))
        try:
            outputs = run(ast)
        except RuntimeRecipixError as e:
            sys.exit(str(e))
        for line in outputs:
            print(line)
        return

    # default: parse-only success message
    print(f"OK — parsed {args.file}")


if __name__ == "__main__":
    main()
