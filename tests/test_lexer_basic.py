import sys
sys.path.insert(0, 'src')
from lexer import Lexer

source = (
    'table students = load "students.csv"\n'
    '\n'
    'let result = SELECT name, grade\n'
    '             FROM students\n'
    '             WHERE grade > 70 AND grade < 90\n'
    '             ORDER BY grade DESC\n'
    '\n'
    'print result\n'
)

tokens = Lexer(source).tokenize()
for t in tokens:
    print(t)
