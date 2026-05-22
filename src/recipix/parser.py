"""
Recipix recursive-descent parser.

Consumes an Iterable of token objects.  Each token must expose:
  .type  (str)  — token type constant
  .value        — Python value or lexeme string
  .line  (int)  — 1-based source line

Produces a Program AST.  Raises ParseError on any grammatical violation.

Spec corners enforced here (see task brief):
  #34  quantity_of  — dedicated unary production, NOT routed through primary
  #35  substitute   — ingredient slots are bare IDENTs, not expressions
  #7   quantity lit — INT_LIT/FLOAT_LIT optionally followed by UNIT_KW
  #17  comparisons  — non-associative; a < b < c is a parse error
  #20  if/else      — braces are mandatory on both branches
  #23  step mods    — [at <expr>] must precede [for <expr>]
  §7   serves       — expression parsed greedily; stops naturally at '{'
  §8   action verbs — own statement production, not a generic call
  §5   precedence   — separate production per level
  §9   evaluate     — parsed only at top-level program loop
  §10  no semantic  — single-assignment, shadowing, types deferred to Part 2
"""

from __future__ import annotations
from typing import Iterable

from .errors import ParseError
from .tokens import (
    INT_LIT, FLOAT_LIT, STRING_LIT, BOOL_LIT, IDENT,
    UNIT_KW, TYPE_KW, ACTION_KW,
    PLUS, MINUS, STAR, SLASH,
    EQ, NEQ, LT, LTE, GT, GTE,
    AND, OR, NOT, ASSIGN,
    LPAREN, RPAREN, LBRACE, RBRACE, LBRACKET, RBRACKET,
    COMMA, COLON, ARROW, EOF,
)
from .ast_nodes import (
    Program, Param,
    RecipeDecl, FunctionDecl, IngredientDecl, StepDecl,
    EvalStmt, LetStmt, IfStmt, RepeatStmt, ForeachStmt, ReturnStmt, ActionStmt,
    BinaryOp, CompareOp, UnaryOp, QuantityOf, SubstituteCall, ScaleCall,
    FunctionCall, RecipeCall, KwArg, AmbiguousCall,
    Identifier, IntLit, FloatLit, BoolLit, StringLit, QuantityLit, ListLit,
)


class Parser:
    # ------------------------------------------------------------------
    # Construction and token navigation
    # ------------------------------------------------------------------

    def __init__(self, tokens: Iterable):
        self._toks = list(tokens)
        self._pos  = 0

    def _peek(self, offset: int = 0):
        idx = self._pos + offset
        return self._toks[idx] if idx < len(self._toks) else self._toks[-1]

    def _advance(self):
        tok = self._toks[self._pos]
        if self._pos < len(self._toks) - 1:
            self._pos += 1
        return tok

    def _check(self, *types: str) -> bool:
        return self._peek().type in types

    def _match(self, *types: str):
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, typ: str, msg: str | None = None) -> object:
        tok = self._peek()
        if tok.type != typ:
            desc = msg or f"expected '{typ}'"
            raise ParseError(tok.line, getattr(tok, 'col', 0),
                             f"{desc}, got '{tok.type}' ('{tok.value}')",
                             expected=typ, got=tok.type)
        return self._advance()

    def _expect_kw(self, kw: str) -> object:
        """Expect a reserved keyword (token type == keyword string)."""
        return self._expect(kw, f"expected keyword '{kw}'")

    def _line(self) -> int:
        return self._peek().line

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def parse(self) -> Program:
        line = self._line()
        items = []
        while not self._check(EOF):
            if self._check('recipe'):
                items.append(self._parse_recipe_decl())
            elif self._check('function'):
                items.append(self._parse_function_decl())
            elif self._check('evaluate'):
                items.append(self._parse_eval_stmt())
            else:
                tok = self._peek()
                raise ParseError(tok.line, getattr(tok, 'col', 0),
                                 f"expected 'recipe', 'function', or 'evaluate' "
                                 f"at top level, got '{tok.type}' ('{tok.value}')")
        return Program(items=items, line=line)

    # ------------------------------------------------------------------
    # Top-level: evaluate statement
    # ------------------------------------------------------------------

    def _parse_eval_stmt(self) -> EvalStmt:
        tok = self._expect_kw('evaluate')
        expr = self._parse_expr()
        return EvalStmt(expr=expr, line=tok.line)

    # ------------------------------------------------------------------
    # Recipe declaration
    # ------------------------------------------------------------------

    def _parse_recipe_decl(self) -> RecipeDecl:
        tok = self._expect_kw('recipe')
        name_tok = self._expect(IDENT, "expected recipe name")
        name = name_tok.value

        self._expect(LPAREN, "expected '(' after recipe name")
        params = self._parse_param_list()
        self._expect(RPAREN, "expected ')' after parameter list")

        self._expect_kw('serves')
        serves = self._parse_expr()   # greedy; stops when '{' appears naturally

        self._expect(LBRACE, "expected '{' to open recipe body")

        ingredients = []
        while self._check('ingredient'):
            ingredients.append(self._parse_ingredient_decl())

        steps = []
        while self._check('step'):
            steps.append(self._parse_step_decl())

        if not self._check(RBRACE):
            t = self._peek()
            raise ParseError(t.line, getattr(t, 'col', 0),
                             f"unexpected token '{t.type}' ('{t.value}') in recipe body; "
                             f"expected 'ingredient', 'step', or '}}'")
        self._expect(RBRACE)

        return RecipeDecl(name=name, params=params, serves=serves,
                          ingredients=ingredients, steps=steps, line=tok.line)

    # ------------------------------------------------------------------
    # Function declaration
    # ------------------------------------------------------------------

    def _parse_function_decl(self) -> FunctionDecl:
        tok = self._expect_kw('function')
        name_tok = self._expect(IDENT, "expected function name")
        name = name_tok.value

        self._expect(LPAREN, "expected '(' after function name")
        params = self._parse_param_list()
        self._expect(RPAREN, "expected ')' after parameter list")

        self._expect(ARROW, "expected '->' after parameter list")
        ret_tok = self._expect(TYPE_KW, "expected return type after '->'")
        return_type = ret_tok.value

        self._expect(LBRACE, "expected '{' to open function body")
        body = self._parse_stmt_list()

        # Enforce: exactly one return, must be the last top-level statement (v1)
        return_indices = [i for i, s in enumerate(body) if isinstance(s, ReturnStmt)]
        if not return_indices:
            raise ParseError(
                self._line(), 0,
                "function body must end with a 'return' statement"
            )
        if return_indices[-1] != len(body) - 1:
            bad = body[return_indices[-1]]
            raise ParseError(
                bad.line, 0,
                "'return' must be the last statement in a function body "
                "(no early return in v1)"
            )
        if len(return_indices) > 1:
            bad = body[return_indices[0]]
            raise ParseError(
                bad.line, 0,
                "only one 'return' statement is allowed per function (no early return in v1)"
            )

        self._expect(RBRACE, "expected '}' to close function body")

        return FunctionDecl(name=name, params=params, return_type=return_type,
                            body=body, line=tok.line)

    # ------------------------------------------------------------------
    # Parameter list: (ident : type_name, ...)
    # ------------------------------------------------------------------

    def _parse_param_list(self) -> list:
        params = []
        if self._check(RPAREN):
            return params
        params.append(self._parse_param())
        while self._match(COMMA):
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> Param:
        name_tok = self._expect(IDENT, "expected parameter name")
        self._expect(COLON, "expected ':' after parameter name")
        type_tok = self._expect(TYPE_KW, "expected type name after ':'")
        return Param(name=name_tok.value, type_name=type_tok.value, line=name_tok.line)

    # ------------------------------------------------------------------
    # Ingredient declaration
    # ------------------------------------------------------------------

    def _parse_ingredient_decl(self) -> IngredientDecl:
        tok = self._expect_kw('ingredient')
        name_tok = self._expect(IDENT, "expected ingredient name")
        self._expect(COLON, "expected ':' after ingredient name")
        expr = self._parse_expr()
        return IngredientDecl(name=name_tok.value, expr=expr, line=tok.line)

    # ------------------------------------------------------------------
    # Step declaration
    # ------------------------------------------------------------------

    def _parse_step_decl(self) -> StepDecl:
        tok = self._expect_kw('step')
        desc_tok = self._expect(STRING_LIT, "expected step description string")
        description = desc_tok.value

        at_expr  = None
        for_expr = None

        # Decision #23: 'at' must precede 'for'; both optional
        if self._check('at'):
            self._advance()
            at_expr = self._parse_expr()

        if self._check('for'):
            self._advance()
            for_expr = self._parse_expr()
            # Guard: next token must be '{'; anything else means the modifier
            # order is wrong or the expression was mis-parsed.
            if not self._check(LBRACE):
                t = self._peek()
                if t.type == 'at':
                    raise ParseError(t.line, 0,
                        "'at' modifier must come before 'for' modifier in step declaration "
                        "(Decision #23)")
                raise ParseError(t.line, 0,
                    f"expected '{{' to open step body after 'for' modifier, "
                    f"got '{t.type}' ('{t.value}'). "
                    f"If your 'for' expression is complex, wrap it in parentheses.")

        if self._check('at'):
            t = self._peek()
            raise ParseError(t.line, getattr(t, 'col', 0),
                             "'at' modifier must come before 'for' modifier in step declaration "
                             "(Decision #23)")

        self._expect(LBRACE, "expected '{' to open step body")
        body = self._parse_stmt_list()
        self._expect(RBRACE, "expected '}' to close step body")

        return StepDecl(description=description, at_expr=at_expr,
                        for_expr=for_expr, body=body, line=tok.line)

    # ------------------------------------------------------------------
    # Statement lists and individual statements
    # ------------------------------------------------------------------

    def _parse_stmt_list(self) -> list:
        stmts = []
        while not self._check(RBRACE, EOF):
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_stmt(self) -> object:
        t = self._peek()
        if t.type == 'let':
            return self._parse_let_stmt()
        if t.type == 'if':
            return self._parse_if_stmt()
        if t.type == 'repeat':
            return self._parse_repeat_stmt()
        if t.type == 'foreach':
            return self._parse_foreach_stmt()
        if t.type == 'return':
            return self._parse_return_stmt()
        if t.type == ACTION_KW:
            return self._parse_action_stmt()
        if t.type == 'for':
            raise ParseError(t.line, 0,
                "'for' is not a statement keyword — did you mean 'foreach'? "
                "The 'for' keyword is only valid as a step modifier "
                "(e.g. step \"...\" for <expr> { }).")
        raise ParseError(t.line, getattr(t, 'col', 0),
                         f"unexpected token '{t.type}' ('{t.value}'); "
                         f"expected a statement (let, if, repeat, foreach, return, or action verb)")

    def _parse_let_stmt(self) -> LetStmt:
        tok = self._expect_kw('let')
        name_tok = self._expect(IDENT, "expected name after 'let'")
        self._expect(COLON, "expected ':' after name in 'let'")
        type_tok = self._expect(TYPE_KW, "expected type name after ':' in 'let'")
        self._expect(ASSIGN, "expected '=' after type in 'let'")
        expr = self._parse_expr()
        return LetStmt(name=name_tok.value, type_name=type_tok.value,
                       expr=expr, line=tok.line)

    def _parse_if_stmt(self) -> IfStmt:
        tok = self._expect_kw('if')
        condition = self._parse_expr()
        # Decision #20: braces are mandatory
        self._expect(LBRACE, "expected '{' after 'if' condition (braces are mandatory)")
        then_body = self._parse_stmt_list()
        self._expect(RBRACE, "expected '}' to close 'if' body")

        else_body = None
        if self._check('else'):
            self._advance()
            self._expect(LBRACE, "expected '{' after 'else' (braces are mandatory)")
            else_body = self._parse_stmt_list()
            self._expect(RBRACE, "expected '}' to close 'else' body")

        return IfStmt(condition=condition, then_body=then_body,
                      else_body=else_body, line=tok.line)

    def _parse_repeat_stmt(self) -> RepeatStmt:
        tok = self._expect_kw('repeat')
        count = self._parse_expr()
        self._expect_kw('times')
        self._expect(LBRACE, "expected '{' after 'times'")
        body = self._parse_stmt_list()
        self._expect(RBRACE, "expected '}' to close 'repeat' body")
        return RepeatStmt(count=count, body=body, line=tok.line)

    def _parse_foreach_stmt(self) -> ForeachStmt:
        tok = self._expect_kw('foreach')
        var_tok = self._expect(IDENT, "expected loop variable name after 'foreach'")
        self._expect_kw('in')
        iterable = self._parse_expr()
        self._expect(LBRACE, "expected '{' after 'foreach ... in ...'")
        body = self._parse_stmt_list()
        self._expect(RBRACE, "expected '}' to close 'foreach' body")
        return ForeachStmt(var_name=var_tok.value, iterable=iterable,
                           body=body, line=tok.line)

    def _parse_return_stmt(self) -> ReturnStmt:
        tok = self._expect_kw('return')
        expr = self._parse_expr()
        return ReturnStmt(expr=expr, line=tok.line)

    def _parse_action_stmt(self) -> ActionStmt:
        tok = self._advance()   # consume ACTION_KW token
        verb = tok.value
        self._expect(LPAREN, f"expected '(' after action verb '{verb}'")
        args = []
        if not self._check(RPAREN):
            args.append(self._parse_expr())
            while self._match(COMMA):
                args.append(self._parse_expr())
        self._expect(RPAREN, f"expected ')' to close '{verb}(...)' call")
        return ActionStmt(verb=verb, args=args, line=tok.line)

    # ------------------------------------------------------------------
    # Expressions — separate production per precedence level (spec §5)
    #
    # Level 7 (lowest):  ||
    # Level 6:           &&
    # Level 5:           == !=     (non-associative)
    # Level 4:           < <= > >= (non-associative)
    # Level 3:           + -       (binary, left-assoc)
    # Level 2:           * /       (left-assoc)
    # Level 1 (highest): unary -, !, quantity_of(...)
    # ------------------------------------------------------------------

    def _parse_expr(self):
        return self._parse_or()

    def _parse_or(self):
        line = self._line()
        left = self._parse_and()
        while self._check(OR):
            op_tok = self._advance()
            right = self._parse_and()
            left = BinaryOp(op='||', left=left, right=right, line=op_tok.line)
        return left

    def _parse_and(self):
        left = self._parse_eq()
        while self._check(AND):
            op_tok = self._advance()
            right = self._parse_eq()
            left = BinaryOp(op='&&', left=left, right=right, line=op_tok.line)
        return left

    def _parse_eq(self):
        """Level 5: == !=  — non-associative (Decision #17)."""
        left = self._parse_rel()
        if self._check(EQ, NEQ):
            op_tok = self._advance()
            right = self._parse_rel()
            # Non-associativity: a second comparison operator here is an error
            if self._check(EQ, NEQ, LT, LTE, GT, GTE):
                bad = self._peek()
                raise ParseError(bad.line, getattr(bad, 'col', 0),
                                 f"comparison operators are non-associative; "
                                 f"use parentheses to group comparisons (Decision #17)")
            _eq_map = {EQ: '==', NEQ: '!='}
            return CompareOp(op=_eq_map[op_tok.type], left=left, right=right, line=op_tok.line)
        return left

    def _parse_rel(self):
        """Level 4: < <= > >=  — non-associative (Decision #17)."""
        left = self._parse_add()
        if self._check(LT, LTE, GT, GTE):
            op_tok = self._advance()
            right = self._parse_add()
            # Non-associativity check
            if self._check(LT, LTE, GT, GTE, EQ, NEQ):
                bad = self._peek()
                raise ParseError(bad.line, getattr(bad, 'col', 0),
                                 f"comparison operators are non-associative; "
                                 f"use parentheses to group comparisons (Decision #17)")
            # Determine op string from token type
            _op_map = {LT: '<', LTE: '<=', GT: '>', GTE: '>='}
            return CompareOp(op=_op_map[op_tok.type], left=left, right=right,
                             line=op_tok.line)
        return left

    def _parse_add(self):
        left = self._parse_mul()
        while self._check(PLUS, MINUS):
            op_tok = self._advance()
            right = self._parse_mul()
            op = '+' if op_tok.type == PLUS else '-'
            left = BinaryOp(op=op, left=left, right=right, line=op_tok.line)
        return left

    def _parse_mul(self):
        left = self._parse_unary()
        while self._check(STAR, SLASH):
            op_tok = self._advance()
            right = self._parse_unary()
            op = '*' if op_tok.type == STAR else '/'
            left = BinaryOp(op=op, left=left, right=right, line=op_tok.line)
        return left

    def _parse_unary(self):
        """Level 1 (highest): unary -, !, quantity_of(...).  Right-associative."""
        tok = self._peek()

        if tok.type == MINUS:
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(op='-', operand=operand, line=tok.line)

        if tok.type == NOT:
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(op='!', operand=operand, line=tok.line)

        # Decision #34: quantity_of is a dedicated unary operator, NOT a function call.
        if tok.type == 'quantity_of':
            self._advance()
            self._expect(LPAREN, "expected '(' after 'quantity_of'")
            operand = self._parse_expr()
            self._expect(RPAREN, "expected ')' to close 'quantity_of(...)'")
            return QuantityOf(operand=operand, line=tok.line)

        return self._parse_primary()

    # ------------------------------------------------------------------
    # Primary expressions
    # ------------------------------------------------------------------

    def _parse_primary(self):
        tok = self._peek()

        # Integer or float literal — optionally followed by a unit keyword
        # (Decision #7: quantity literal is two tokens)
        if tok.type == INT_LIT:
            self._advance()
            if self._check(UNIT_KW):
                unit_tok = self._advance()
                return QuantityLit(number=tok.value, unit=unit_tok.value, line=tok.line)
            return IntLit(value=tok.value, line=tok.line)

        if tok.type == FLOAT_LIT:
            self._advance()
            if self._check(UNIT_KW):
                unit_tok = self._advance()
                return QuantityLit(number=tok.value, unit=unit_tok.value, line=tok.line)
            return FloatLit(value=tok.value, line=tok.line)

        if tok.type == BOOL_LIT:
            self._advance()
            return BoolLit(value=tok.value, line=tok.line)

        if tok.type == STRING_LIT:
            self._advance()
            return StringLit(value=tok.value, line=tok.line)

        # List literal
        if tok.type == LBRACKET:
            return self._parse_list_lit()

        # scale(...) — Decision #35 / spec §9
        if tok.type == 'scale':
            return self._parse_scale_call()

        # substitute(...) — Decision #35 / spec §9
        if tok.type == 'substitute':
            return self._parse_substitute_call()

        # Grouped expression
        if tok.type == LPAREN:
            self._advance()
            inner = self._parse_expr()
            self._expect(RPAREN, "expected ')' to close grouped expression")
            return inner

        # Action verbs cannot appear in expression position
        if tok.type == ACTION_KW:
            raise ParseError(tok.line, getattr(tok, 'col', 0),
                             f"action verb '{tok.value}' cannot appear in an expression; "
                             f"action verbs are statement-only (spec §8)")

        # Identifier — may be a call or a plain reference
        if tok.type == IDENT:
            return self._parse_ident_or_call()

        raise ParseError(tok.line, getattr(tok, 'col', 0),
                         f"unexpected token '{tok.type}' ('{tok.value}') in expression")

    # ------------------------------------------------------------------
    # scale call
    # ------------------------------------------------------------------

    def _parse_scale_call(self) -> ScaleCall:
        tok = self._expect_kw('scale')
        self._expect(LPAREN, "expected '(' after 'scale'")
        recipe = self._parse_expr()
        self._expect(COMMA, "expected ',' after recipe expression in 'scale'")
        self._expect_kw('by')
        self._expect(COLON, "expected ':' after 'by' in 'scale'")
        by = self._parse_expr()
        self._expect(RPAREN, "expected ')' to close 'scale(...)'")
        return ScaleCall(recipe=recipe, by=by, line=tok.line)

    # ------------------------------------------------------------------
    # substitute call — Decision #35: ingredient slots are bare IDENTs
    # ------------------------------------------------------------------

    def _parse_substitute_call(self) -> SubstituteCall:
        tok = self._expect_kw('substitute')
        self._expect(LPAREN, "expected '(' after 'substitute'")
        recipe = self._parse_expr()
        self._expect(COMMA, "expected ',' after recipe expression in 'substitute'")

        # original ingredient — must be a bare IDENT (Decision #35)
        orig_tok = self._peek()
        if orig_tok.type != IDENT:
            raise ParseError(orig_tok.line, getattr(orig_tok, 'col', 0),
                             f"substitute: original ingredient must be a bare identifier, "
                             f"not '{orig_tok.type}' (Decision #35 / error #17)")
        self._advance()
        original_name = orig_tok.value
        # If the token after the IDENT is not ',', the user wrote an expression
        if not self._check(COMMA):
            bad = self._peek()
            raise ParseError(bad.line, getattr(bad, 'col', 0),
                             f"substitute: original ingredient must be a bare identifier — "
                             f"expressions are not allowed here (Decision #35 / error #17); "
                             f"got '{bad.type}' after identifier '{original_name}'")

        self._expect(COMMA, "expected ',' after original ingredient name in 'substitute'")
        self._expect_kw('with')
        self._expect(COLON, "expected ':' after 'with' in 'substitute'")

        # replacement ingredient — must be a bare IDENT (Decision #35)
        repl_tok = self._peek()
        if repl_tok.type != IDENT:
            raise ParseError(repl_tok.line, getattr(repl_tok, 'col', 0),
                             f"substitute: replacement ingredient must be a bare identifier, "
                             f"not '{repl_tok.type}' (Decision #35 / error #17)")
        self._advance()
        replacement_name = repl_tok.value
        # Same guard: if next token is not ',', user wrote an expression
        if not self._check(COMMA):
            bad = self._peek()
            raise ParseError(bad.line, getattr(bad, 'col', 0),
                             f"substitute: replacement ingredient must be a bare identifier — "
                             f"expressions are not allowed here (Decision #35 / error #17); "
                             f"got '{bad.type}' after identifier '{replacement_name}'")

        self._expect(COMMA, "expected ',' after replacement name in 'substitute'")
        self._expect_kw('ratio')
        self._expect(COLON, "expected ':' after 'ratio' in 'substitute'")
        ratio = self._parse_expr()

        self._expect(RPAREN, "expected ')' to close 'substitute(...)'")
        return SubstituteCall(recipe=recipe, original_name=original_name,
                              replacement_name=replacement_name, ratio=ratio,
                              line=tok.line)

    # ------------------------------------------------------------------
    # List literal
    # ------------------------------------------------------------------

    def _parse_list_lit(self) -> ListLit:
        tok = self._advance()  # consume '['
        elements = []
        if not self._check(RBRACKET):
            elements.append(self._parse_expr())
            while self._match(COMMA):
                if self._check(RBRACKET):
                    break  # trailing comma
                elements.append(self._parse_expr())
        self._expect(RBRACKET, "expected ']' to close list literal")
        return ListLit(elements=elements, line=tok.line)

    # ------------------------------------------------------------------
    # Identifier — plain reference or call
    # ------------------------------------------------------------------

    def _parse_ident_or_call(self):
        name_tok = self._advance()   # consume IDENT
        name = name_tok.value

        # Not a call — plain identifier reference
        if not self._check(LPAREN):
            return Identifier(name=name, line=name_tok.line)

        # It's a call.  Determine if it's a recipe call (keyword args)
        # or a function call (positional args) by 2-token lookahead.
        self._advance()  # consume '('

        if self._check(RPAREN):
            # Zero-arg call — kind (recipe vs function) resolved by type checker
            self._advance()
            return AmbiguousCall(name=name, line=name_tok.line)

        # Peek to see if first arg is keyword style: IDENT ':'
        if (self._peek(0).type == IDENT and self._peek(1).type == COLON):
            # Recipe call with keyword arguments
            kwargs = self._parse_kwargs()
            self._expect(RPAREN, f"expected ')' to close '{name}(...)' call")
            return RecipeCall(name=name, kwargs=kwargs, line=name_tok.line)
        else:
            # Function call with positional arguments
            args = [self._parse_expr()]
            while self._match(COMMA):
                args.append(self._parse_expr())
            self._expect(RPAREN, f"expected ')' to close '{name}(...)' call")
            return FunctionCall(name=name, args=args, line=name_tok.line)

    def _parse_kwargs(self) -> list:
        kwargs = []
        kwargs.append(self._parse_kwarg())
        while self._match(COMMA):
            if self._check(RPAREN):
                break
            kwargs.append(self._parse_kwarg())
        return kwargs

    def _parse_kwarg(self) -> KwArg:
        name_tok = self._expect(IDENT, "expected keyword argument name")
        self._expect(COLON, "expected ':' after keyword argument name")
        value = self._parse_expr()
        return KwArg(name=name_tok.value, value=value, line=name_tok.line)

    # ------------------------------------------------------------------
    # Operator string helpers
    # ------------------------------------------------------------------

    def _op_str(self, tok) -> str:
        _map = {
            'PLUS': '+', 'MINUS': '-', 'STAR': '*', 'SLASH': '/',
            'EQ': '==', 'NEQ': '!=', 'LT': '<', 'LTE': '<=',
            'GT': '>', 'GTE': '>=', 'AND': '&&', 'OR': '||', 'NOT': '!',
        }
        return _map.get(tok.type, tok.type)


# ------------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------------

def parse(tokens: Iterable) -> Program:
    """Parse an iterable of tokens and return the Program AST."""
    return Parser(tokens).parse()
