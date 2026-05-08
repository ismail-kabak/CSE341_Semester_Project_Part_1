# Recipix — Part 1: Parser

Recursive-descent parser for the Recipix v4.1 DSL.  
Spec: `recipix_v4_1_spec.md` · Language design: **locked at v4.1**.

---

## Quick start

No third-party dependencies — Python 3.11+ and the stdlib are all you need.

```bash
# Parse a file (prints "OK" on success, error on failure)
python main.py <file.rcx>

# Pretty-print the AST
python main.py --dump-ast <file.rcx>

# Run the full test suite
python -m unittest discover tests
```

Run all commands from the **project root**. No third-party dependencies required.

---

## Repository layout

```
src/
  lexer.py              # Lexer team deliverable (not modified by the parser team)
  recipix/
    __init__.py
    __main__.py         # CLI: python -m recipix <file> [--dump-ast]
    tokens.py           # Parser's token contract (see below)
    ast_nodes.py        # All AST dataclasses
    parser.py           # Recursive-descent parser
    errors.py           # ParseError (line, col, message)
    pretty.py           # AST pretty-printer for --dump-ast

tests/
  fixtures/
    valid/
      sample1.rcx       # Spec §11 sample 1 — recipe + helper function
      sample2.rcx       # Spec §11 sample 2 — substitution at call site
      sample3.rcx       # Spec §11 sample 3 — type error (valid parse, Part 2 catches it)
    invalid/
      missing_brace_if.rcx       # if without braces (Decision #20)
      wrong_modifier_order.rcx   # for...at instead of at...for (Decision #23)
      substitute_expr_slot.rcx   # expression in substitute ingredient slot (Decision #35)
      nonassoc_comparison.rcx    # a < b < c chained comparison (Decision #17)
      quantity_of_no_paren.rcx   # quantity_of without parentheses (Decision #34)
  test_parser.py        # 48 unittest tests; no third-party deps
```

---

## Token contract (for the lexer team)

The parser consumes an `Iterable` of token objects.  
Each token must expose the following attributes:

| Attribute | Type  | Description |
|-----------|-------|-------------|
| `.type`   | `str` | One of the token-type constants listed below |
| `.value`  | any   | Python value (int/float/bool) or lexeme string |
| `.line`   | `int` | 1-based source line number |

Column information (`.col`) is optional; the parser defaults to `0` when absent.

### Token-type constants

These are the exact strings the parser checks against `.type`.  
They are defined in `src/recipix/tokens.py` — the single source of truth. The lexer imports from this same file.

#### Literals

| Constant     | `.value` type | Notes |
|-------------|---------------|-------|
| `INT_LIT`   | `int`         | e.g. `42` |
| `FLOAT_LIT` | `float`       | e.g. `3.14` |
| `STRING_LIT`| `str`         | Content only, without surrounding quotes |
| `BOOL_LIT`  | `bool`        | `True` or `False` (Python bool) |

#### Identifiers

| Constant | `.value` | Notes |
|----------|----------|-------|
| `IDENT`  | `str`    | User-defined name; never a reserved word |

#### Keyword classes (single `.type`, distinguishable by `.value`)

| Constant    | `.value` examples | Covered words |
|-------------|------------------|---------------|
| `UNIT_KW`   | `'g'`, `'ml'`, `'°C'` | `mg g kg ml l tsp tbsp cup °C min hr count pinch` |
| `TYPE_KW`   | `'int'`, `'Mass'` | `int float bool Mass Volume Count Temperature Duration Pinch` |
| `ACTION_KW` | `'combine'`, `'bake'` | `combine mix pour melt whisk blend bake flip add sprinkle drizzle knead` |

**`°C`** must be emitted as a single `UNIT_KW` token with `.value == '°C'`.  
The degree symbol cannot appear standalone.

#### Reserved keywords — `.type` IS the keyword string

Each keyword below produces a token whose `.type` equals the keyword text itself:

```
recipe   function  ingredient  step
let      if        else
repeat   times
foreach  in
at       for
evaluate scale     substitute
serves   with      by          ratio
return
quantity_of
```

`true` and `false` produce `BOOL_LIT` tokens, **not** keyword tokens.

#### Operators

| Constant | Lexeme |
|----------|--------|
| `PLUS`   | `+`    |
| `MINUS`  | `-`    |
| `STAR`   | `*`    |
| `SLASH`  | `/`    |
| `EQ`     | `==`   |
| `NEQ`    | `!=`   |
| `LT`     | `<`    |
| `LTE`    | `<=`   |
| `GT`     | `>`    |
| `GTE`    | `>=`   |
| `AND`    | `&&`   |
| `OR`     | `\|\|` |
| `NOT`    | `!`    |
| `ASSIGN` | `=`    |

#### Separators

| Constant   | Lexeme |
|------------|--------|
| `LPAREN`   | `(`    |
| `RPAREN`   | `)`    |
| `LBRACE`   | `{`    |
| `RBRACE`   | `}`    |
| `LBRACKET` | `[`    |
| `RBRACKET` | `]`    |
| `COMMA`    | `,`    |
| `COLON`    | `:`    |
| `ARROW`    | `->`   |

#### Special

| Constant | Notes |
|----------|-------|
| `EOF`    | Must be the last token in every stream; `.value` may be `None` |

### Quantity literals (Decision #7)

Quantity literals are **two tokens**: a numeric literal (`INT_LIT` or `FLOAT_LIT`)
followed immediately by a `UNIT_KW`.  Only whitespace and `//` comments may
appear between them.  The parser combines them into a `QuantityLit` AST node.

```
200 g       → INT_LIT(200)   UNIT_KW('g')
1.5 kg      → FLOAT_LIT(1.5) UNIT_KW('kg')
180 °C      → INT_LIT(180)   UNIT_KW('°C')
1 pinch     → INT_LIT(1)     UNIT_KW('pinch')
```

---

## Spec decisions visible in the parser

| Decision | Where it shows up |
|----------|-------------------|
| **#34** `quantity_of` as unary operator | `Parser._parse_unary` — dedicated branch; never reaches `_parse_primary`. Produces `QuantityOf` AST node. |
| **#35** `substitute` ingredient slots as bare identifiers | `Parser._parse_substitute_call` — after consuming the IDENT, checks that the next token is `,`, not an operator. `SubstituteCall.original_name` and `.replacement_name` are `str`, not `Expr`. |
| **#7** Two-token quantity literals | `Parser._parse_primary` — after `INT_LIT`/`FLOAT_LIT`, peeks for `UNIT_KW`. |
| **#17** Non-associative comparisons | `Parser._parse_eq` / `Parser._parse_rel` — after consuming one comparison operator and its right operand, checks for a second comparison and raises `ParseError` if found. |
| **#20** Mandatory braces on if/else | `Parser._parse_if_stmt` — both branches use `_expect(LBRACE, ...)`. |
| **#23** Fixed modifier order (at before for) | `Parser._parse_step_decl` — `at` is consumed first if present; if `at` appears after `for` has been consumed, an explicit error is raised. |
| **§7** Serves expression greedy | The `serves` expression calls `_parse_expr()` normally; `{` is not a valid expression token so the expression parser stops naturally before the brace. |
| **§8** Action verbs as statement form | `Parser._parse_stmt` routes `ACTION_KW` to `_parse_action_stmt`. In `_parse_primary`, an `ACTION_KW` raises `ParseError` to block it in expression position. |
| **§5** Separate production per precedence level | `_parse_or` → `_parse_and` → `_parse_eq` → `_parse_rel` → `_parse_add` → `_parse_mul` → `_parse_unary` → `_parse_primary`. |
| **§9** `evaluate` top-level only | The top-level parsing loop in `Parser.parse()` is the only place that calls `_parse_eval_stmt()`. Inside recipe/function/step bodies, `evaluate` is not a recognised statement keyword. |
| **§10/§11** No semantic checks | Dimension mismatches, single-assignment, no-shadowing — none of these are checked. They are deferred to the Part 2 type checker. |

---

## ParseError format

```
parse error at line {line}, col {col}: {message}
```

Example:
```
parse error at line 7, col 0: 'at' modifier must come before 'for' modifier in step declaration (Decision #23)
```

---

## Spec ambiguities encountered

1. **`return` placement inside functions.** The spec says "Single `return` statement at the end of the body. No early return in v1." This is a *semantic* constraint (one return, at the end of the top-level body), not a *grammar* rule — the grammar permits `return` inside nested blocks (`if`, `repeat`, etc.) without ambiguity. The parser allows `return` anywhere inside a function body and defers the single-at-the-end constraint to the Part 2 type checker. PM should confirm whether this should be a parse error.

2. **`scale`/`substitute` in non-`evaluate` expression positions.** The spec says these are "call-site only" and "appear at the top level." The parser enforces that `evaluate` is top-level, and `scale`/`substitute` can appear in any expression (including inside `evaluate`). Whether `let x : Recipe = scale(r(), by: 2)` inside a recipe body should be a parse error is unresolved — flagged for PM to confirm with the spec author.

3. **Recipe vs. function call disambiguation.** The parser uses a 2-token lookahead: if the first argument token is `IDENT` followed by `:`, it's treated as a keyword-arg recipe call; otherwise it's a positional-arg function call. Mixed calls (some positional, some keyword) are not supported and would produce a parse error at the unexpected `:`.

4. **Zero-arg calls.** `f()` (zero arguments) is parsed as `FunctionCall`, not `RecipeCall`. If a zero-parameter recipe is called as `r()`, it becomes a `FunctionCall` node. The type checker distinguishes them by name resolution.
