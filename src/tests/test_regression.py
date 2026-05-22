"""
Recipix parser regression tests.

These fixtures were harvested from the Part 1 exploratory test corpus
(originally ``src/test2/tests/tester/``) and parked here as a regression
net for Part 2. The directory layout is:

    regression/
        should_pass/    — must parse without error
        should_fail/    — must raise ParseError
        exploratory/    — Part 2 testbed (not walked by this file)

Same parser-driver pattern as ``test_parser.py``; stdlib unittest only.

Run from the project root:
    python -m unittest discover src/tests
"""

import os
import sys
import unittest

_here    = os.path.dirname(__file__)
_project = os.path.dirname(os.path.dirname(_here))
_src     = os.path.join(_project, "src")

for _p in (_src, os.path.dirname(_here)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lexer import Lexer, LexerError
from recipix.parser import parse
from recipix.errors import ParseError

# Lexer-level rejection and parser-level rejection are both
# "front-end refused this source", which is what should_fail expresses.
_REJECT_ERRORS = (ParseError, LexerError)


_REG_DIR    = os.path.join(_here, "regression")
_PASS_DIR   = os.path.join(_REG_DIR, "should_pass")
_FAIL_DIR   = os.path.join(_REG_DIR, "should_fail")


def _parse_file(path: str):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    return parse(Lexer(src).tokenize())


def _gather(subdir: str):
    if not os.path.isdir(subdir):
        return []
    return sorted(
        fn for fn in os.listdir(subdir)
        if fn.endswith(".rcx")
    )


class TestRegressionShouldPass(unittest.TestCase):
    """Each fixture under regression/should_pass/ must parse without error."""


class TestRegressionShouldFail(unittest.TestCase):
    """Each fixture under regression/should_fail/ must raise ParseError."""


def _make_pass_test(fname: str):
    def test(self):
        _parse_file(os.path.join(_PASS_DIR, fname))
    test.__name__ = f"test_pass_{fname.replace('.', '_').replace('-', '_')}"
    test.__doc__  = f"{fname} must parse successfully"
    return test


def _make_fail_test(fname: str):
    def test(self):
        with self.assertRaises(_REJECT_ERRORS,
                               msg=f"{fname} should have raised LexerError or ParseError"):
            _parse_file(os.path.join(_FAIL_DIR, fname))
    test.__name__ = f"test_fail_{fname.replace('.', '_').replace('-', '_')}"
    test.__doc__  = f"{fname} must raise ParseError"
    return test


for _fname in _gather(_PASS_DIR):
    _t = _make_pass_test(_fname)
    setattr(TestRegressionShouldPass, _t.__name__, _t)

for _fname in _gather(_FAIL_DIR):
    _t = _make_fail_test(_fname)
    setattr(TestRegressionShouldFail, _t.__name__, _t)


if __name__ == "__main__":
    unittest.main()
