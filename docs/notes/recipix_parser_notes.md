# Recipix Parser — Study Notes (your component, Berk)

> Your D5 retrospective: **"parser owner; PM-style orchestration."** All 48
> parser tests green. AST shapes match spec §14 exactly. Every enforced
> decision (#7, #17, #20, #23, #34, #35) lives at the right level of the
> recursive-descent stack. This file is *your defense kit* for tomorrow.

---

## 1. Parser strategy — the why

### Recursive descent — Sebesta §4.4

**What it is:** a top-down parser written as a set of mutually-recursive
functions, one per grammar non-terminal. Each function consumes tokens that
match its production and calls other parser functions for sub-non-terminals.

**Why we chose it over a parser generator (ANTLR / PEG):**
1. We can be asked to *defend every line* in the exam. Hand-written recursive
   descent means there's no generated code we don't understand.
2. The Recipix grammar is small enough (~30 productions) that the
   one-function-per-non-terminal mapping is direct.
3. Error messages are precise — we control exactly what to say at each
   `_expect` call (file:line:col + a tailored message).
4. The grammar is **LL(1)** almost everywhere (one place needs LL(2) — see §6).
   Recursive descent is the natural fit for LL(k) grammars.

**LL(1) requirements (Sebesta §4.4.1):**
- No left recursion — `A ::= A α` would cause infinite descent.
- Each alternative for a non-terminal must be distinguishable by its FIRST
  set with only the next token visible.

**How our grammar satisfies these:**
- Left recursion eliminated by using EBNF loops in productions like
  `<add_expr> ::= <mul_expr> { ("+" | "-") <mul_expr> }`, which the code
  implements as a `while` loop accumulating the left operand.
- Each statement keyword (`let`, `if`, `repeat`, `foreach`, `return`, action
  verbs) is uniquely distinguishable by its first token.

---

## 2. Architecture — what lives where

```
src/recipix/
├── tokens.py        — token-type string constants (shared contract w/ lexer)
├── ast_nodes.py     — every AST dataclass (Program, RecipeDecl, BinaryOp, ...)
├── errors.py        — ParseError(line, col, message, expected, got)
├── parser.py        — the Parser class (704 lines)
├── pretty.py        — pretty-printer for --dump-ast
└── __main__.py      — CLI: `python -m recipix <file> [--dump-ast]`
```

**Parser ↔ Lexer contract:** the parser consumes an `Iterable` of token
objects. Each token has `.type` (string constant), `.value` (Python value or
lexeme), `.line` (1-based). Column is optional. The `tokens.py` file is the
**single source of truth** — both the lexer and parser import the same
constants. This was negotiated before either side started writing code.

### The Parser class — navigation helpers

```python
_peek(offset=0)   # look at next token (or further ahead)
_advance()        # consume current token, return it
_check(*types)    # is next token's type in this set?
_match(*types)    # if so, advance; return matched token or None
_expect(typ, msg) # advance if matched; else raise ParseError
_expect_kw(kw)    # specialized _expect for reserved keywords
```

These five helpers do all the token I/O. The parsing methods compose them.

---

## 3. The precedence cascade — your most-likely exam target

Recursive descent encodes operator precedence and associativity **in the call
hierarchy itself**: the lower the precedence, the higher in the call stack.

```
_parse_expr
  → _parse_or          (||,  left-assoc, lowest precedence)
    → _parse_and       (&&,  left-assoc)
      → _parse_eq      (== !=, NON-ASSOCIATIVE — Decision #17)
        → _parse_rel   (< <= > >=, NON-ASSOCIATIVE — Decision #17)
          → _parse_add (+ -, left-assoc)
            → _parse_mul (* /, left-assoc)
              → _parse_unary (-, !, quantity_of — right-assoc, highest)
                → _parse_primary (literals, idents, calls, parens, list_lit,
                                  scale, substitute)
```

### Why this enforces precedence — the mechanism

When `_parse_add` parses `a + b * c`:
1. It calls `_parse_mul` for the **left** operand. `_parse_mul` parses `a`
   via `_parse_unary` → `_parse_primary`. Sees no `*` or `/`. Returns `a`.
2. Back in `_parse_add`, the while-loop sees `+`. Consumes it. Calls
   `_parse_mul` for the **right** operand.
3. `_parse_mul` parses `b`. Then sees `*`. Consumes it. Parses `c`.
   Returns `BinaryOp(*, b, c)`.
4. Back in `_parse_add`. The right operand is `BinaryOp(*, b, c)`. The
   loop sees no more `+`/`-`. Returns `BinaryOp(+, a, BinaryOp(*, b, c))`.

The AST shape `+(a, *(b, c))` **is** the precedence rule made physical.

### Why the while-loop enforces left-associativity

```python
def _parse_add(self):
    left = self._parse_mul()
    while self._check(PLUS, MINUS):
        op_tok = self._advance()
        right = self._parse_mul()
        left = BinaryOp(op=op, left=left, right=right, ...)
    return left
```

For `a - b - c`: parse `a`, see `-`, parse `b`, build `BinaryOp(-, a, b)`,
**reassign `left`**, loop again, parse `c`, build `BinaryOp(-, BinaryOp(-, a, b), c)`.
That is `(a - b) - c` — left-associative. If we recursed instead of looping,
we'd get `a - (b - c)`, which is wrong for subtraction.

### Why unary is right-associative

```python
def _parse_unary(self):
    if tok.type == MINUS:
        self._advance()
        operand = self._parse_unary()    # ← recurses on itself
        return UnaryOp(op='-', operand=operand, ...)
```

`!!x` parses as `!(!x)` because the recursion goes through `_parse_unary`
itself before reaching `_parse_primary`. Right-associativity by recursive call.

---

## 4. The five enforced decisions — where each one lives

### Decision #7 — quantity literals are two tokens
**Location:** `_parse_primary`, after `INT_LIT` / `FLOAT_LIT`:
```python
if tok.type == INT_LIT:
    self._advance()
    if self._check(UNIT_KW):
        unit_tok = self._advance()
        return QuantityLit(number=tok.value, unit=unit_tok.value, ...)
    return IntLit(value=tok.value, ...)
```
A numeric literal optionally consumes a following `UNIT_KW`. If no unit
follows, it's a plain `IntLit`/`FloatLit`. One-token lookahead.

**Defense:** keeps the lexer simple (numbers and keywords stay orthogonal);
the parser does the assembly. Trade-off: an expression cannot be followed
by a unit keyword to make a quantity — you must write `<expr> * 1 g` per
Decision #30.

### Decision #17 — comparisons are non-associative
**Location:** `_parse_eq` and `_parse_rel`. Both use **`if`, not `while`** —
after consuming one comparison, the parser checks that the next token isn't
another comparison.

```python
def _parse_rel(self):
    left = self._parse_add()
    if self._check(LT, LTE, GT, GTE):
        op_tok = self._advance()
        right = self._parse_add()
        if self._check(LT, LTE, GT, GTE, EQ, NEQ):    # second comparison?
            raise ParseError(..., "comparison operators are non-associative...")
        return CompareOp(...)
    return left
```

So `a < b < c` raises a parse error at the second `<`. Useful messages
include the Decision-#17 reference.

**⚠ Spec/code nuance your D5 flagged:** your retrospective said the *intended*
rule is "the *same* comparison cannot chain," meaning `a < b == c` should
parse as `(a < b) == c`. But the code as written checks `(LT, LTE, GT, GTE, EQ, NEQ)`
together in `_parse_rel`, so it rejects `a < b == c` too. If the examiner
asks "what does your parser do for `a < b == c`?" — **answer honestly:** the
current code rejects it because both `<` and `==` are flagged at the
non-associativity check; the spec intent is non-chaining of the *same*
comparison family, and this is on our Part 2 polish list. Don't try to claim
behavior the code doesn't have.

**Why non-associative at all?** `a < b < c` looks mathematically like
"a < b and b < c" but in most languages (C, Java) it parses as
`(a < b) < c`, where `(a < b)` is a bool and the comparison `bool < c` is
either meaningless or quietly coerces — a classic source of bugs. Making
chained comparisons a *parse error* eliminates the foot-gun entirely.

### Decision #20 — mandatory braces on if/else
**Location:** `_parse_if_stmt`:
```python
def _parse_if_stmt(self) -> IfStmt:
    tok = self._expect_kw('if')
    condition = self._parse_expr()
    self._expect(LBRACE, "expected '{' after 'if' condition (braces are mandatory)")
    then_body = self._parse_stmt_list()
    self._expect(RBRACE, "expected '}' to close 'if' body")
    if self._check('else'):
        self._advance()
        self._expect(LBRACE, "expected '{' after 'else' (braces are mandatory)")
        ...
```

**Defense:** eliminates the dangling-else ambiguity **structurally**, not
through a disambiguating rule. The grammar can't even *express* a brace-less
branch, so there's no ambiguity to resolve.

### Decision #23 — step modifiers in fixed order (`at` before `for`)
**Location:** `_parse_step_decl`:
```python
if self._check('at'):
    self._advance()
    at_expr = self._parse_expr()

if self._check('for'):
    self._advance()
    for_expr = self._parse_expr()
    if not self._check(LBRACE):
        t = self._peek()
        if t.type == 'at':
            raise ParseError(..., "'at' modifier must come before 'for' modifier ...")

if self._check('at'):    # second guard — at after for-only is also caught
    raise ParseError(..., "'at' modifier must come before 'for' modifier ...")
```

Both modifiers are optional, so all four combinations
`(at?, for?) × (at?, for?)` are valid. But order is fixed. Two guards catch
the inverted-order case from both directions.

**Defense:** grammar simplicity. Allowing arbitrary order would mean either
(a) writing a more complex production that accepts each modifier in any
position (and rejecting duplicates), or (b) doing it post-parse in a semantic
check. Locking the order in the grammar keeps the parser linear.

### Decision #34 — `quantity_of` is a unary operator, not a function
**Location:** `_parse_unary`, a **dedicated branch** that does NOT fall
through to `_parse_primary`:
```python
if tok.type == 'quantity_of':
    self._advance()
    self._expect(LPAREN, "expected '(' after 'quantity_of'")
    operand = self._parse_expr()
    self._expect(RPAREN, "expected ')' to close 'quantity_of(...)'")
    return QuantityOf(operand=operand, ...)
```

The reserved-keyword token `quantity_of` is intercepted at the unary level
before `_parse_primary` ever sees it. So `quantity_of` cannot be redefined,
assigned, or passed as an argument — there's no place in the grammar where
it would be parsed as an `Identifier`.

**Defense:** type-system reason. `quantity_of` has the type rule
`Ingredient → <dimension of its quantity field>`. There is no
`FunctionType` we could give it: the return type depends on the *type-level
structure* of the argument, which our `function` declaration form (which
requires a single fixed return-type annotation) cannot express. Making it
a unary operator avoids needing such a type at all.

**AST shape:** `QuantityOf(operand, line)` — a dedicated AST node, not a
`FunctionCall`. This is what the spec §14 requires.

### Decision #35 — `substitute` slots are bare identifiers
**Location:** `_parse_substitute_call`:
```python
orig_tok = self._peek()
if orig_tok.type != IDENT:
    raise ParseError(..., "substitute: original ingredient must be a bare identifier ...")
self._advance()
original_name = orig_tok.value
if not self._check(COMMA):           # guard: must be comma right after IDENT
    raise ParseError(..., "...expressions are not allowed here ...")
```

After consuming the ingredient-name `IDENT`, we explicitly **check that the
next token is a comma**. If it's anything else (an operator, a paren, etc.),
the user wrote an expression and we reject with a Decision-#35 reference.

**AST shape:** `SubstituteCall.original_name: str` — typed as `str`, not
`Expr`. The grammar guarantees the slot is an identifier, so the AST refuses
to pretend it could be anything else.

**Defense:** ingredient identity is the binding (Decision #28), not a runtime
value. By restricting the slot syntactically to a bare identifier, we make
that resolution rule **visible in the grammar itself** rather than punting
it to the type checker.

---

## 5. The 2-token lookahead — your one LL(2) place

**Where:** `_parse_ident_or_call`. After we see `IDENT (`, we need to
distinguish:
- `pancakes(servings: 4)` → **recipe call** with keyword args
- `half(servings)` → **function call** with positional args

We peek at two tokens past the `(`:
```python
if (self._peek(0).type == IDENT and self._peek(1).type == COLON):
    # First arg looks like  IDENT ":"  → keyword arg → recipe call
    kwargs = self._parse_kwargs()
    return RecipeCall(name=name, kwargs=kwargs, ...)
else:
    args = [self._parse_expr()]                   # positional → function call
    while self._match(COMMA):
        args.append(self._parse_expr())
    return FunctionCall(name=name, args=args, ...)
```

**Edge case — zero-arg calls:**
```python
if self._check(RPAREN):
    self._advance()
    return AmbiguousCall(name=name, ...)
```
For `r()` we can't tell at parse time whether `r` is a recipe or a function —
both are written the same with no args. We emit `AmbiguousCall` and defer
the disambiguation to the **type checker** (Part 2), which will resolve via
the symbol table.

**Why this isn't a problem for LL(1) "purity":** LL(2) is still
deterministic. We're not backtracking — we make a single decision based on
two tokens of lookahead and commit. The parser is linear-time.

---

## 6. Action verbs blocked in expression position (§8)

The 12 action verbs (`combine`, `mix`, `pour`, `melt`, `whisk`, `blend`,
`bake`, `flip`, `add`, `sprinkle`, `drizzle`, `knead`) are reserved keywords.
They have their own statement production (`_parse_action_stmt`) and they're
**explicitly blocked** from appearing in expressions:

```python
# in _parse_primary:
if tok.type == ACTION_KW:
    raise ParseError(..., "action verb '...' cannot appear in an expression; "
                          "action verbs are statement-only (spec §8)")
```

**Defense:** action verbs represent *physical operations* in a recipe (mixing,
baking, flipping). They have no return value semantically. Allowing them in
expression position would create the question of what `let x = combine(...)`
should mean, which has no natural answer. Restricting them to statement
position lets us give them per-verb signatures in Part 2 (#29) without
breaking the expression grammar.

**Also:** in `_parse_stmt`, `for` is intercepted with a friendly message
("did you mean `foreach`?") because `for` is only valid as a step modifier,
not a loop keyword.

---

## 7. Greedy `serves` expression — a subtle one

```python
self._expect_kw('serves')
serves = self._parse_expr()           # greedy expression parse
self._expect(LBRACE, "expected '{' to open recipe body")
```

The expression after `serves` is parsed *greedily* — `_parse_expr` consumes
as much as it can. The reason it stops at `{` is that `{` is not a valid
**expression token** anywhere in the grammar — no expression production
accepts `{` as a continuation. So `_parse_expr` returns naturally and
`_expect(LBRACE, ...)` consumes it.

**Why this is safe:** as long as the expression grammar contains no rule
that accepts `{`, parsing always stops at the brace and never "eats into"
the recipe body. This is brittle-by-design — change it carelessly and you
could break recipe parsing.

---

## 8. Error reporting

**Format:** `parse error at line {line}, col {col}: {message}`

Every `_expect` call provides a message; every Decision-#XX violation
references the decision number in its error string. This makes test
fixtures readable and exam discussion concrete:
- `parse error at line 7, col 0: 'at' modifier must come before 'for' modifier in step declaration (Decision #23)`
- `parse error at line 4, col 12: comparison operators are non-associative; use parentheses to group comparisons (Decision #17)`

---

## 9. Worked traces — practice these out loud

### Trace 1: `1 + 2 * 3`

| Step | Function | What it does |
|---|---|---|
| 1 | `_parse_expr` | calls `_parse_or` |
| 2 | `_parse_or` → ... → `_parse_add` | calls `_parse_mul` for left |
| 3 | `_parse_mul` | calls `_parse_unary` → `_parse_primary` → returns `IntLit(1)` |
| 4 | `_parse_mul` | sees no `*` or `/`, returns `IntLit(1)` |
| 5 | `_parse_add` | sees `+`, advances. Calls `_parse_mul` for right. |
| 6 | `_parse_mul` | parses `IntLit(2)` |
| 7 | `_parse_mul` | sees `*`, advances. Parses `IntLit(3)`. |
| 8 | `_parse_mul` | returns `BinaryOp(*, 2, 3)` |
| 9 | `_parse_add` | builds `BinaryOp(+, 1, BinaryOp(*, 2, 3))` |

**Final AST: `+(1, *(2, 3))`.**

### Trace 2: `quantity_of(flour) + 100 g * 2`

1. `_parse_expr` → ... → `_parse_add` → `_parse_mul` → `_parse_unary`.
2. `_parse_unary` sees `quantity_of`. Enters the dedicated branch.
   Consumes `quantity_of`, `(`. Calls `_parse_expr` for operand.
3. Operand: `flour` parses as `Identifier('flour')` via `_parse_primary` →
   `_parse_ident_or_call` (no `(` follows, plain ident).
4. `_parse_unary` consumes `)`. Returns `QuantityOf(operand=Identifier('flour'))`.
5. Back up to `_parse_mul`. No `*`/`/` yet — returns the `QuantityOf` node.
6. Back to `_parse_add`. Sees `+`. Advances. Calls `_parse_mul` for right.
7. `_parse_mul` → `_parse_unary` → `_parse_primary`. Sees `INT_LIT(100)`.
   Advances. Peeks: `UNIT_KW('g')`. Decision #7 fires. Returns
   `QuantityLit(100, 'g')`.
8. Back in `_parse_mul`. Sees `*`. Advances. Calls `_parse_unary` →
   `_parse_primary` → `IntLit(2)`.
9. `_parse_mul` returns `BinaryOp(*, QuantityLit(100, 'g'), IntLit(2))`.
10. `_parse_add` builds `BinaryOp(+, QuantityOf(flour), BinaryOp(*, 100g, 2))`.

**Final AST: `+(quantity_of(flour), *(100g, 2))`.**

### Trace 3: `if x > 0 { combine(flour) }`
1. `_parse_stmt` sees `if` → `_parse_if_stmt`.
2. `_expect_kw('if')`. Then `_parse_expr` for condition.
3. Condition path: `_parse_or → _and → _eq → _rel`.
   `_parse_rel` parses `x` via `_parse_add → _parse_mul → _parse_unary
   → _parse_primary → _parse_ident_or_call`. Returns `Identifier('x')`.
4. `_parse_rel` sees `>`. Advances. Parses `0` via `_parse_add` →
   eventually `IntLit(0)`.
5. `_parse_rel` returns `CompareOp(>, x, 0)`. Bubbles up to `condition`.
6. `_expect(LBRACE, "...braces are mandatory")` — Decision #20.
7. `_parse_stmt_list` parses the body. Sees `combine` (`ACTION_KW`), routes
   to `_parse_action_stmt`. Returns `ActionStmt('combine', [Identifier('flour')])`.
8. `_expect(RBRACE)`. No `else`. Returns `IfStmt(CompareOp(>,x,0), [ActionStmt(...)], None)`.

### Trace 4: malformed input `if x { ... } { ... }` (no else keyword)
After parsing the `if` body and consuming `}`, `_parse_if_stmt` checks for
`else`. The next token is `{` — not `else`. So `_parse_if_stmt` returns
with `else_body=None`. Control returns to whichever `_parse_stmt_list` is
the caller. That caller sees `{` next — but `{` is not a statement keyword.
`_parse_stmt` falls through to its final `raise ParseError(..., "expected a
statement (let, if, repeat, foreach, return, or action verb)")`.

**Useful exam point:** the parser reports the error *at the unexpected `{`*,
not retroactively at the `if`. This is why line-number error reporting must
follow the parser's actual position.

---

## 10. AST node menagerie (spec §14 + your additions)

Every AST node carries a `line: int`. Most are simple dataclasses.

| Node | Fields | Notes |
|---|---|---|
| `Program` | `items` | Top-level: recipe/function decls + eval stmts |
| `RecipeDecl` | `name, params, serves, ingredients, steps` |  |
| `FunctionDecl` | `name, params, return_type, body` | Exactly one `return`, last stmt |
| `Param` | `name, type_name` |  |
| `IngredientDecl` | `name, expr` |  |
| `StepDecl` | `description, at_expr, for_expr, body` | `at_expr`/`for_expr` are `Expr` or `None` |
| `LetStmt` | `name, type_name, expr` | Type annotation required |
| `IfStmt` | `condition, then_body, else_body` | `else_body` is `list` or `None` |
| `RepeatStmt` | `count, body` |  |
| `ForeachStmt` | `var_name, iterable, body` |  |
| `ReturnStmt` | `expr` |  |
| `ActionStmt` | `verb, args` |  |
| `EvalStmt` | `expr` | Top-level only |
| `BinaryOp` | `op, left, right` | `+ - * / && \|\|` |
| `CompareOp` | `op, left, right` | `== != < <= > >=` — separate from BinaryOp |
| `UnaryOp` | `op, operand` | `- !` |
| `QuantityOf` | `operand` | **Operator node, not call** — Decision #34 |
| `SubstituteCall` | `recipe, original_name: str, replacement_name: str, ratio` | `str` slots — Decision #35 |
| `ScaleCall` | `recipe, by` |  |
| `FunctionCall` | `name, args` | Positional args |
| `RecipeCall` | `name, kwargs` | Keyword args |
| `KwArg` | `name, value` |  |
| `AmbiguousCall` | `name` | Zero-arg calls; resolved by type checker |
| `Identifier`, `IntLit`, `FloatLit`, `BoolLit`, `StringLit`, `QuantityLit`, `ListLit` | (literals + plain ident reference) |  |

---

## 11. Likely exam questions — your answers

**Q: Walk me through how your parser handles `a + b * c - d`.**
A: `_parse_add` calls `_parse_mul` for the left operand. `_parse_mul`
returns `a` (no `*`/`/` follows). `_parse_add` sees `+`, advances, calls
`_parse_mul` for the right. `_parse_mul` parses `b`, sees `*`, advances,
parses `c`, returns `BinaryOp(*, b, c)`. Now `_parse_add`'s left becomes
`BinaryOp(+, a, BinaryOp(*, b, c))`. Loop again — sees `-`, advances, calls
`_parse_mul` which returns `d`. Final: `BinaryOp(-, BinaryOp(+, a, *(b,c)), d)`.
The `*` binds tighter because `_parse_mul` is *inside* `_parse_add`; the
`+` and `-` are left-associative because they're consumed in a while-loop
that reassigns `left`.

**Q: Why is your parser recursive descent and not LR?**
A: Three reasons. First, our grammar is small and naturally LL(1) for the
expression cascade — recursive descent is the simplest fit. Second, error
messages: hand-written `_expect` calls let us produce precise
line+column+rationale messages per failure, whereas an LR parser generator
produces generic "syntax error" messages. Third, we can be asked to defend
every line in the exam — there's no generated code we don't understand.

**Q: Is your grammar LL(1)?**
A: Almost everywhere. The one exception is `_parse_ident_or_call`: after
seeing `IDENT (`, we use 2-token lookahead to distinguish a keyword-arg
recipe call from a positional-arg function call. We peek for `IDENT` followed
by `:`. So strictly the parser is LL(2) at that point. It's still
deterministic and linear-time — no backtracking.

**Q: Where in your parser is Decision #34 (`quantity_of` as operator) enforced?**
A: In `_parse_unary`, in a dedicated branch *before* falling through to
`_parse_primary`. The token type `quantity_of` is intercepted at unary level;
the operand is parsed as a full expression inside required parens; we return
a `QuantityOf` AST node, not a `FunctionCall`. Because the token never
reaches `_parse_primary`, it cannot be parsed as an `Identifier` — `quantity_of`
is unredefinable by construction.

**Q: How does your parser produce a good error message for `200g`?**
A: That's actually rejected at the **lexer** level — Decision #7 says the
number and unit must be separated. The lexer's error includes a line number
and recommends the corrected `200 g` form. If the lexer instead emitted two
tokens, `_parse_primary` would peek for a `UNIT_KW` after the number and
combine them via Decision #7. Either way, the user gets a useful diagnostic.

**Q: What happens at parse time when you encounter `a < b < c`?**
A: `_parse_rel` parses `a` (via `_parse_add`), sees `<`, advances, parses `b`.
Then it checks whether the next token is another comparison operator — `<`
is. It raises `ParseError` with a Decision #17 reference: "comparison
operators are non-associative; use parentheses to group comparisons."

**Q: And what about `a < b == c`?**
A: Honest answer — the current code rejects this too because `_parse_rel`'s
non-associativity check includes both relational and equality operators in
the same set. The spec's *intent* was that only the *same* comparison family
shouldn't chain (so `(a < b) == c` would be legal), and my D5 retrospective
flagged this as a Part 2 polish item. The behavior as shipped is the stricter
one; the error message is the same.

**Q: How would you change your parser to support an `else if` chain?**
A: I wouldn't need a separate production. The current `_parse_if_stmt`
already handles it: after consuming `}` of the then-body and matching `else`,
I currently `_expect(LBRACE)`. If I instead checked for `if` first and
recursively called `_parse_if_stmt` when present, `else if` would compose
naturally — the AST would be an `IfStmt` whose `else_body` is a single-element
list containing another `IfStmt`. But Decision #20 (mandatory braces) was
chosen specifically because the brace-less form is what creates dangling-else;
adding `else if` re-introduces that surface complexity without buying much.

**Q: What's the role of `AmbiguousCall`?**
A: Zero-argument calls — `r()` — are syntactically indistinguishable between
a recipe with no params and a function with no params. The parser emits
`AmbiguousCall(name)` and the type checker (Part 2) resolves which one it
is via the symbol table. This is the parser's one explicit
disambiguation-by-deferring move: rather than guess, we record the ambiguity
in the AST and let the next phase resolve it from richer information.

**Q: How does your parser stop parsing the `serves` expression at the brace?**
A: `_parse_expr` calls down the precedence cascade. None of the expression
productions accept `{` as a continuation — `{` is not a valid operator,
literal, identifier, paren, or list bracket. So `_parse_expr` returns
naturally as soon as it sees `{`. Then `_expect(LBRACE, ...)` consumes it.
This relies on the invariant that `{` never appears inside an expression,
which is true throughout the grammar.

**Q: How do you handle EOF?**
A: Every token stream ends with an `EOF` token. `_advance()` does not advance
past EOF (it returns the last token without incrementing position) — this
means a runaway `_parse_stmt_list` will see EOF, exit its loop, and let the
outer caller raise a useful error like "expected `}` to close ... body".

---

## 12. Cheat-sheet seeds (raw material to copy by hand)

When you sit down for the handwritten cheat sheet, these blocks distill best:

**Block A — The precedence cascade (one tall column).**
Just the call hierarchy with operators and associativity, as in §3 above.

**Block B — The five decisions and one-line code reference each.**
- #7  `_parse_primary`  INT_LIT + optional UNIT_KW
- #17 `_parse_eq`/`_parse_rel`  `if`, not `while` (non-associative)
- #20 `_parse_if_stmt`  mandatory `_expect(LBRACE)` both branches
- #23 `_parse_step_decl`  `at` before `for`; two guards
- #34 `_parse_unary`  dedicated branch for `quantity_of`, never reaches primary
- #35 `_parse_substitute_call`  `IDENT` slot + comma-guard

**Block C — Sebesta scope/binding/lifetime table from spec §6.**
The two tables (binding times and lifetimes) verbatim — these are factual
and likely to appear directly on the exam.

**Block D — Operational semantics for `repeat` and `if`.**
Inference rules verbatim. Easy to lose marks here if mis-formatted.

**Block E — Ambiguity resolutions.**
- Precedence + associativity → separate productions per level
- Dangling-else → mandatory braces
- Comparison chains → non-associative (#17)

**Block F — Sebesta evaluation criteria table.**
Readability / Writability / Reliability / Cost with Recipix's stance on each.

---

## 13. Things to NOT spend time on tonight

- **Memorizing the type system internals** (Pinch ceremony, structural vs
  name equivalence, dimensional arithmetic table) — Ch. 6 stuff. You should
  be able to *defend* the design (one paragraph each) but don't memorize
  the per-operation tables. Exam 1 is Ch. 1, 3, 4, 5.
- **Memorizing every error number** from the spec's 18-item error list.
- **Pretty-printer internals** — pretty.py is not graded.

## 14. Things to ABSOLUTELY know cold

- The precedence cascade structure and *why* it enforces precedence
- Why left-assoc uses `while`, right-assoc uses recursion
- The Decision #20 (mandatory braces) defense — dangling-else **by construction**
- The Decision #34 defense — type-system reason `quantity_of` can't be a function
- The Decision #17 *honest* answer for `a < b == c` — your D5 already
  flagged this; don't get caught lying
- The binding-time table (compile vs runtime)
- The lifetime table (static vs stack-dynamic)
- The two-token quantity literal mechanism and its trade-off
- Static scoping defense and what would break under dynamic
- Operational semantics for `repeat` and `if`
- One worked trace of a non-trivial expression like `quantity_of(flour) + 100 g * 2`

Sleep when these feel automatic. The exam can't trick you if you can speak
each of these without the paper in front of you.
