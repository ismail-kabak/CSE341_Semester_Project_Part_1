"""
DataScript AST Node definitions.

Every node has a `line` attribute for error reporting.
Every node implements __repr__ for the --dump-ast flag.

Node hierarchy:
  Statements:  Program, TableDecl, LetStmt, PrintStmt,
               IfStmt, FuncDecl, ReturnStmt
  Expressions: BinOp, UnaryOp, IntLit, FloatLit, StringLit, BoolLit,
               Ident, FuncCall, Aggregate, QueryExpr
"""


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Node:
    """Base class — provides indented pretty-printing for --dump-ast."""

    def dump(self, indent: int = 0) -> str:
        raise NotImplementedError

    def _ind(self, indent: int) -> str:
        return "  " * indent


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

class Program(Node):
    def __init__(self, statements: list):
        self.statements = statements

    def dump(self, indent=0):
        lines = [self._ind(indent) + "Program"]
        for s in self.statements:
            lines.append(s.dump(indent + 1))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

class TableDecl(Node):
    """table <name> = load "<file>" """
    def __init__(self, name: str, filepath: str, line: int):
        self.name = name
        self.filepath = filepath
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"TableDecl(name={self.name!r}, file={self.filepath!r})"


class LetStmt(Node):
    """let <name> = <expr>"""
    def __init__(self, name: str, value, line: int):
        self.name = name
        self.value = value
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + f"LetStmt(name={self.name!r})"]
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


class PrintStmt(Node):
    """print <expr>"""
    def __init__(self, value, line: int):
        self.value = value
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + "PrintStmt"]
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


class IfStmt(Node):
    """if <cond> then <then_block> [ else <else_block> ]"""
    def __init__(self, condition, then_block, else_block, line: int):
        self.condition = condition
        self.then_block = then_block   # list of statements
        self.else_block = else_block   # list of statements or None
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + "IfStmt"]
        lines.append(self._ind(indent + 1) + "condition:")
        lines.append(self.condition.dump(indent + 2))
        lines.append(self._ind(indent + 1) + "then:")
        for s in self.then_block:
            lines.append(s.dump(indent + 2))
        if self.else_block is not None:
            lines.append(self._ind(indent + 1) + "else:")
            for s in self.else_block:
                lines.append(s.dump(indent + 2))
        return "\n".join(lines)


class FuncDecl(Node):
    """function <name>(<params>) -> <return_type> { <body> }"""
    def __init__(self, name: str, params: list, return_type: str, body: list, line: int):
        self.name = name
        self.params = params         # list of (name_str, type_str) tuples
        self.return_type = return_type
        self.body = body             # list of statements
        self.line = line

    def dump(self, indent=0):
        param_str = ", ".join(f"{n}:{t}" for n, t in self.params)
        lines = [self._ind(indent) + f"FuncDecl(name={self.name!r}, params=[{param_str}], return={self.return_type!r})"]
        for s in self.body:
            lines.append(s.dump(indent + 1))
        return "\n".join(lines)


class ReturnStmt(Node):
    """return <expr>"""
    def __init__(self, value, line: int):
        self.value = value
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + "ReturnStmt"]
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Expressions — literals
# ---------------------------------------------------------------------------

class IntLit(Node):
    def __init__(self, value: int, line: int):
        self.value = value
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"IntLit({self.value})"


class FloatLit(Node):
    def __init__(self, value: float, line: int):
        self.value = value
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"FloatLit({self.value})"


class StringLit(Node):
    def __init__(self, value: str, line: int):
        self.value = value
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"StringLit({self.value!r})"


class BoolLit(Node):
    def __init__(self, value: bool, line: int):
        self.value = value
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"BoolLit({self.value})"


class Ident(Node):
    def __init__(self, name: str, line: int):
        self.name = name
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"Ident({self.name!r})"


# ---------------------------------------------------------------------------
# Expressions — operations
# ---------------------------------------------------------------------------

class BinOp(Node):
    """Binary operation: left <op> right"""
    def __init__(self, op: str, left, right, line: int):
        self.op = op
        self.left = left
        self.right = right
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + f"BinOp({self.op!r})"]
        lines.append(self.left.dump(indent + 1))
        lines.append(self.right.dump(indent + 1))
        return "\n".join(lines)


class UnaryOp(Node):
    """Unary operation: <op> operand  (only unary minus and NOT)"""
    def __init__(self, op: str, operand, line: int):
        self.op = op
        self.operand = operand
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + f"UnaryOp({self.op!r})"]
        lines.append(self.operand.dump(indent + 1))
        return "\n".join(lines)


class FuncCall(Node):
    """<name>(<args>)"""
    def __init__(self, name: str, args: list, line: int):
        self.name = name
        self.args = args
        self.line = line

    def dump(self, indent=0):
        lines = [self._ind(indent) + f"FuncCall(name={self.name!r})"]
        for a in self.args:
            lines.append(a.dump(indent + 1))
        return "\n".join(lines)


class Aggregate(Node):
    """COUNT(*), SUM(col), AVG(col), MIN(col), MAX(col)"""
    def __init__(self, func: str, column: str, line: int):
        self.func = func       # e.g. 'COUNT'
        self.column = column   # e.g. 'grade' or '*'
        self.line = line

    def dump(self, indent=0):
        return self._ind(indent) + f"Aggregate({self.func}, col={self.column!r})"


# ---------------------------------------------------------------------------
# Domain-specific construct: Query Expression
# ---------------------------------------------------------------------------

class QueryExpr(Node):
    """
    SELECT <select_list>
    FROM <table_name>
    [ WHERE <condition> ]
    [ GROUP BY <group_cols> [ HAVING <having_cond> ] ]
    [ ORDER BY <order_items> ]
    """
    def __init__(self, select_list, from_name: str,
                 where=None, group_by=None, having=None,
                 order_by=None, line: int = 0):
        self.select_list = select_list   # list of Ident or Aggregate, or ['*']
        self.from_name = from_name
        self.where = where               # expr Node or None
        self.group_by = group_by         # list of str (column names) or None
        self.having = having             # expr Node or None
        self.order_by = order_by         # list of (col_str, 'ASC'|'DESC') or None
        self.line = line

    def dump(self, indent=0):
        i = self._ind(indent)
        lines = [i + f"QueryExpr(from={self.from_name!r})"]
        lines.append(self._ind(indent + 1) + "select:")
        for col in self.select_list:
            if isinstance(col, str):
                lines.append(self._ind(indent + 2) + col)
            else:
                lines.append(col.dump(indent + 2))
        if self.where:
            lines.append(self._ind(indent + 1) + "where:")
            lines.append(self.where.dump(indent + 2))
        if self.group_by:
            lines.append(self._ind(indent + 1) + f"group_by: {self.group_by}")
        if self.having:
            lines.append(self._ind(indent + 1) + "having:")
            lines.append(self.having.dump(indent + 2))
        if self.order_by:
            lines.append(self._ind(indent + 1) + f"order_by: {self.order_by}")
        return "\n".join(lines)
