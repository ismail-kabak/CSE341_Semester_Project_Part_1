"""
Recipix entry point.
Usage:
    python main.py <file.rcx>
    python main.py --dump-ast <file.rcx>
"""
import sys
import os

# Make src/ importable for both lexer.py and the recipix package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from recipix.__main__ import main

if __name__ == '__main__':
    main()
