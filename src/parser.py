"""
DataScript Recursive-Descent Parser

Consumes a token list from the Lexer and produces a Program AST node.
Each non-terminal in the EBNF grammar (D1 §4.3) maps to one method here.
Raises ParseError with a line number on any syntax violation.
"""

from ast_nodes import (
    Program, TableDecl, LetStmt, PrintStmt, IfStmt, FuncDecl, ReturnStmt,
    IntLit, FloatLit, StringLit, BoolLit, Ident,
    BinOp, UnaryOp, FuncCall, Aggregate, QueryExpr,
)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Parse error at line {line}: {message}")
        self.line = line


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """
    Recursive-descent parser for DataScript.

    Design (Sebesta §4.4 — recursive descent):
    - One method per non-terminal in the grammar.
    - self.pos points to the current token in self.tokens.
    - _peek() looks at the current token without consuming it.
    - _expect(type) consumes the current token and raises ParseError
      if it doesn't match.
    - EBNF { X } loops are implemented as while loops.
    - EBNF [ X ] optionals are implemented as if-peeks.
    """

    def __init__(self, tokens: list):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _peek(self):
        return self.tokens[self.pos]

    def _peek_type(self):
        return self.tokens[self.pos].type

    def _advance(self):
        tok = self.tokens[self.pos]
        if tok.type != 'EOF':
            self.pos += 1
        return tok

    def _expect(self, token_type: str):
        tok = self._peek()
        if tok.type != token_type:
            raise ParseError(
                f"Expected {token_type!r} but got {tok.type!r} ({tok.value!r})",
                tok.line,
            )
        return self._advance()

    def _match(self, *types) -> bool:
        """Return True if current token type is in types (does NOT consume)."""
        return self._peek_type() in types

    # ------------------------------------------------------------------
    # Entry point
    # ---------------------  -------------------------------------------

    def parse(self) -> Program:
        """<program> ::= { <statement> }"""
        statements = []
        while not self._match('EOF'):
            statements.append(self._parse_statement())
        return Program(statements)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _parse_statement(self):
        """
        <statement> ::= <table_decl> | <let_stmt> | <print_stmt>
                      | <if_stmt> | <func_decl> | <return_stmt>
        """
        t = self._peek()

        if t.type == 'table':
            return self._parse_table_decl()
        if t.type == 'let':
            return self._parse_let_stmt()
        if t.type == 'print':
            return self._parse_print_stmt()
        if t.type == 'if':
            return self._parse_if_stmt()
        if t.type == 'function':
            return self._parse_func_decl()
        if t.type == 'return':
            return self._parse_return_stmt()

        raise ParseError(
            f"Unexpected token {t.type!r} ({t.value!r}) — expected a statement",
            t.line,
        )

    def _parse_table_decl(self):
        """<table_decl> ::= "table" IDENT "=" "load" STRING_LIT"""
        line = self._peek().line
        self._expect('table')
        name_tok = self._expect('IDENT')
        self._expect('ASSIGN')
        self._expect('load')
        path_tok = self._expect('STRING_LIT')
        return TableDecl(name_tok.value, path_tok.value, line)

    def _parse_let_stmt(self):
        """<let_stmt> ::= "let" IDENT "=" <expr>"""
        line = self._peek().line
        self._expect('let')
        name_tok = self._expect('IDENT')
        self._expect('ASSIGN')
        value = self._parse_expr()
        return LetStmt(name_tok.value, value, line)

    def _parse_print_stmt(self):
        """<print_stmt> ::= "print" <expr>"""
        line = self._peek().line
        self._expect('print')
        value = self._parse_expr()
        return PrintStmt(value, line)

    def _parse_if_stmt(self):
        """<if_stmt> ::= "if" <expr> "then" <block> [ "else" <block> ]"""
        line = self._peek().line
        self._expect('if')
        condition = self._parse_expr()
        self._expect('then')
        then_block = self._parse_block()
        else_block = None
        if self._match('else'):
            self._advance()
            else_block = self._parse_block()
        return IfStmt(condition, then_block, else_block, line)

    def _parse_func_decl(self):
        """<func_decl> ::= "function" IDENT "(" [ <param_list> ] ")" "->" <type> <block>"""
        line = self._peek().line
        self._expect('function')
        name_tok = self._expect('IDENT')
        self._expect('LPAREN')
        params = []
        if not self._match('RPAREN'):
            params = self._parse_param_list()
        self._expect('RPAREN')
        self._expect('ARROW')
        ret_type = self._parse_type()
        body = self._parse_block()
        return FuncDecl(name_tok.value, params, ret_type, body, line)

    def _parse_param_list(self) -> list:
        """<param_list> ::= <param> { "," <param> }"""
        params = [self._parse_param()]
        while self._match('COMMA'):
            self._advance()
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> tuple:
        """<param> ::= IDENT ":" <type>  — returns (name_str, type_str)"""
        name_tok = self._expect('IDENT')
        self._expect('COLON')
        type_str = self._parse_type()
        return (name_tok.value, type_str)

    def _parse_return_stmt(self):
        """<return_stmt> ::= "return" <expr>"""
        line = self._peek().line
        self._expect('return')
        value = self._parse_expr()
        return ReturnStmt(value, line)

    def _parse_block(self) -> list:
        """<block> ::= "{" { <statement> } "}"""
        self._expect('LBRACE')
        stmts = []
        while not self._match('RBRACE', 'EOF'):
            stmts.append(self._parse_statement())
        self._expect('RBRACE')
        return stmts

    def _parse_type(self) -> str:
        """<type> ::= "int" | "float" | "string" | "bool" | "table" """
        t = self._peek()
        if t.type in ('int', 'float', 'string', 'bool', 'table'):
            self._advance()
            return t.type
        raise ParseError(
            f"Expected a type keyword but got {t.type!r} ({t.value!r})",
            t.line,
        )

    # ------------------------------------------------------------------
    # Expressions — grammar layers encode operator precedence
    # Each layer calls the next-higher-precedence layer.
    # ------------------------------------------------------------------

    def _parse_expr(self):
        """<expr> ::= <or_expr>"""
        return self._parse_or_expr()

    def _parse_or_expr(self):
        """<or_expr> ::= <and_expr> { "OR" <and_expr> }"""
        left = self._parse_and_expr()
        while self._match('OR'):
            op_tok = self._advance()
            right = self._parse_and_expr()
            left = BinOp('OR', left, right, op_tok.line)
        return left

    def _parse_and_expr(self):
        """<and_expr> ::= <not_expr> { "AND" <not_expr> }"""
        left = self._parse_not_expr()
        while self._match('AND'):
            op_tok = self._advance()
            right = self._parse_not_expr()
            left = BinOp('AND', left, right, op_tok.line)
        return left

    def _parse_not_expr(self):
        """<not_expr> ::= "NOT" <not_expr> | <compare_expr>"""
        if self._match('NOT'):
            op_tok = self._advance()
            operand = self._parse_not_expr()
            return UnaryOp('NOT', operand, op_tok.line)
        return self._parse_compare_expr()

    def _parse_compare_expr(self):
        """
        <compare_expr> ::= <add_expr> [ ("==" | "!=" | "<" | "<=" | ">" | ">=") <add_expr> ]
        Non-associative: a < b < c is a parse error.
        """
        left = self._parse_add_expr()
        if self._match('EQ', 'NEQ', 'LT', 'LTE', 'GT', 'GTE'):
            op_tok = self._advance()
            right = self._parse_add_expr()
            return BinOp(op_tok.type, left, right, op_tok.line)
        return left

    def _parse_add_expr(self):
        """<add_expr> ::= <mul_expr> { ("+" | "-") <mul_expr> }  — left-associative"""
        left = self._parse_mul_expr()
        while self._match('PLUS', 'MINUS'):
            op_tok = self._advance()
            right = self._parse_mul_expr()
            left = BinOp(op_tok.type, left, right, op_tok.line)
        return left

    def _parse_mul_expr(self):
        """<mul_expr> ::= <unary_expr> { ("*" | "/") <unary_expr> }  — left-associative"""
        left = self._parse_unary_expr()
        while self._match('STAR', 'SLASH'):
            op_tok = self._advance()
            right = self._parse_unary_expr()
            left = BinOp(op_tok.type, left, right, op_tok.line)
        return left

    def _parse_unary_expr(self):
        """<unary_expr> ::= "-" <unary_expr> | <primary>  — right-assoc via recursion"""
        if self._match('MINUS'):
            op_tok = self._advance()
            operand = self._parse_unary_expr()
            return UnaryOp('MINUS', operand, op_tok.line)
        return self._parse_primary()

    # ------------------------------------------------------------------
    # Primary expressions
    # ------------------------------------------------------------------

    def _parse_primary(self):
        """
        <primary> ::= INT_LIT | FLOAT_LIT | STRING_LIT | BOOL_LIT
                    | <aggregate> | <func_call> | <query_expr>
                    | IDENT | "(" <expr> ")"

        Disambiguation:
        - Aggregate: current token is COUNT/SUM/AVG/MIN/MAX
        - Query:     current token is SELECT
        - FuncCall:  current token is IDENT and next is LPAREN  (1 token lookahead)
        - Ident:     current token is IDENT (fallthrough)
        """
        t = self._peek()

        if t.type == 'INT_LIT':
            self._advance()
            return IntLit(t.value, t.line)

        if t.type == 'FLOAT_LIT':
            self._advance()
            return FloatLit(t.value, t.line)

        if t.type == 'STRING_LIT':
            self._advance()
            return StringLit(t.value, t.line)

        if t.type == 'BOOL_LIT':
            self._advance()
            return BoolLit(t.value, t.line)

        if t.type in ('COUNT', 'SUM', 'AVG', 'MIN', 'MAX'):
            return self._parse_aggregate()

        if t.type == 'SELECT':
            return self._parse_query_expr()

        if t.type == 'IDENT':
            # 1-token lookahead: is the next token LPAREN?
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok.type == 'LPAREN':
                return self._parse_func_call()
            self._advance()
            return Ident(t.value, t.line)

        if t.type == 'LPAREN':
            self._advance()
            expr = self._parse_expr()
            self._expect('RPAREN')
            return expr

        raise ParseError(
            f"Expected an expression but got {t.type!r} ({t.value!r})",
            t.line,
        )

    def _parse_func_call(self):
        """<func_call> ::= IDENT "(" [ <arg_list> ] ")" """
        name_tok = self._expect('IDENT')
        self._expect('LPAREN')
        args = []
        if not self._match('RPAREN'):
            args.append(self._parse_expr())
            while self._match('COMMA'):
                self._advance()
                args.append(self._parse_expr())
        self._expect('RPAREN')
        return FuncCall(name_tok.value, args, name_tok.line)

    def _parse_aggregate(self):
        """<aggregate> ::= ("COUNT"|"SUM"|"AVG"|"MIN"|"MAX") "(" (IDENT | "*") ")" """
        func_tok = self._advance()
        self._expect('LPAREN')
        col_tok = self._peek()
        if col_tok.type == 'STAR':
            col = '*'
            self._advance()
        elif col_tok.type == 'IDENT':
            col = col_tok.value
            self._advance()
        else:
            raise ParseError(
                f"Expected column name or '*' inside aggregate, got {col_tok.type!r}",
                col_tok.line,
            )
        self._expect('RPAREN')
        return Aggregate(func_tok.type, col, func_tok.line)

    # ------------------------------------------------------------------
    # Query expression (domain-specific construct)
    # ------------------------------------------------------------------

    def _parse_query_expr(self):
        """
        <query_expr> ::= "SELECT" <select_list>
                         "FROM" IDENT
                         [ "WHERE" <expr> ]
                         [ "GROUP" "BY" <col_list> [ "HAVING" <expr> ] ]
                         [ "ORDER" "BY" <order_list> ]
        """
        line = self._peek().line
        self._expect('SELECT')
        select_list = self._parse_select_list()
        self._expect('FROM')
        from_tok = self._expect('IDENT')

        where = None
        if self._match('WHERE'):
            self._advance()
            where = self._parse_expr()

        group_by = None
        having = None
        if self._match('GROUP'):
            self._advance()
            self._expect('BY')
            group_by = self._parse_col_list()
            if self._match('HAVING'):
                self._advance()
                having = self._parse_expr()

        order_by = None
        if self._match('ORDER'):
            self._advance()
            self._expect('BY')
            order_by = self._parse_order_list()

        return QueryExpr(select_list, from_tok.value, where, group_by, having, order_by, line)

    def _parse_select_list(self) -> list:
        """<select_list> ::= "*" | <col_expr> { "," <col_expr> }"""
        if self._match('STAR'):
            self._advance()
            return ['*']
        cols = [self._parse_col_expr()]
        while self._match('COMMA'):
            self._advance()
            cols.append(self._parse_col_expr())
        return cols

    def _parse_col_expr(self):
        """<col_expr> ::= IDENT | <aggregate>"""
        if self._match('COUNT', 'SUM', 'AVG', 'MIN', 'MAX'):
            return self._parse_aggregate()
        tok = self._expect('IDENT')
        return Ident(tok.value, tok.line)

    def _parse_col_list(self) -> list:
        """<col_list> ::= IDENT { "," IDENT }  — returns list of name strings"""
        cols = [self._expect('IDENT').value]
        while self._match('COMMA'):
            self._advance()
            cols.append(self._expect('IDENT').value)
        return cols

    def _parse_order_list(self) -> list:
        """
        <order_list>  ::= <order_item> { "," <order_item> }
        <order_item>  ::= IDENT [ "ASC" | "DESC" ]
        Returns list of (col_str, direction_str) where direction defaults to 'ASC'.
        """
        items = [self._parse_order_item()]
        while self._match('COMMA'):
            self._advance()
            items.append(self._parse_order_item())
        return items

    def _parse_order_item(self) -> tuple:
        col_tok = self._expect('IDENT')
        direction = 'ASC'
        if self._match('ASC', 'DESC'):
            direction = self._advance().type
        return (col_tok.value, direction)
