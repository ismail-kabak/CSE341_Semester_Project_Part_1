# CSE 341 — MOCK EXAM (Part 1)
### Recipix · Berk Hakan Öge · 90 minutes · Written, on paper

> Calibrated to the professor's actual question style from 6 semester
> quizzes: heavy on **mechanical execution** (~80% of points), every problem
> has **2–4 sub-parts**, every question uses **concrete given inputs**.
>
> **Grading total: 100 pts. Time: 90 min. ~9 min/question average.**
>
> Allowed: 3 sheets A4 handwritten notes, name on each.

---

## PART A — Project-Specific (62 pts, ~55 min)

---

### Q1. [15 pts, 12 min] AST construction

> Given the Recipix expression:
> ```
> quantity_of(flour) * 2 + 100 g
> ```

**(a)** Draw the AST your parser produces. Label every node with its AST
class name; write leaf values on the leaves. [6 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**(b)** Mark with ★ the node where Decision #34 is enforced. [2 pts]

**(c)** Mark with ✦ the node where Decision #7 is enforced. [2 pts]

**(d)** Write the EBNF production whose right-hand side produces the
**root** of this AST. [3 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**(e)** The expression `100 g + quantity_of(flour) * 2` evaluates to the
same value. State the **one structural difference** in its AST. [2 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Q2. [12 pts, 10 min] Malformed inputs

> For each Recipix input below, mark **OK** or **REJECT**. If REJECT,
> identify the Decision (#XX) or spec section (§N) violated AND the
> **parser function** where the error fires. [3 pts each]

```
┌───────────────────────────────────────────────┬──────────┬───────────────┐
│ Input                                         │ OK/REJECT│ Decision + fn │
├───────────────────────────────────────────────┼──────────┼───────────────┤
│ if x > 0 combine(flour)                       │          │               │
├───────────────────────────────────────────────┼──────────┼───────────────┤
│ substitute(r, milk + sugar, with:oat,ratio:1) │          │               │
├───────────────────────────────────────────────┼──────────┼───────────────┤
│ step "Mix" for 5 min at 180 °C { add(x) }     │          │               │
├───────────────────────────────────────────────┼──────────┼───────────────┤
│ a == b == c                                   │          │               │
└───────────────────────────────────────────────┴──────────┴───────────────┘
```

---

### Q3. [15 pts, 12 min] Scope, binding, lifetime

> Consider the Recipix program below.
>
> ```
>  1  function double(n: int) -> int {
>  2      return n * 2
>  3  }
>  4
>  5  recipe pancakes(servings: int) serves servings {
>  6      ingredient flour : 100 g * servings
>  7      ingredient sugar : double(servings) * 1 g
>  8
>  9      step "Mix" at 180 °C {
> 10          let total : Mass = flour + sugar
> 11          if servings > 4 {
> 12              let extra : int = 2
> 13          }
> 14      }
> 15  }
>
> 16  evaluate pancakes(servings: 6)
> ```

**(a)** Draw an arrow from each `servings` reference (lines 5-after-`serves`,
6, 7, 11, 16) to its **declaration**. [3 pts]

**(b)** Fill the binding-time table: write `compile` or `run`. [4 pts]

```
┌──────────────────────────────┬──────────────────┬───────────────────────┐
│ Entity                       │ TYPE bound at    │ VALUE bound at        │
├──────────────────────────────┼──────────────────┼───────────────────────┤
│ flour (L6)                   │                  │                       │
├──────────────────────────────┼──────────────────┼───────────────────────┤
│ total (L10)                  │                  │                       │
├──────────────────────────────┼──────────────────┼───────────────────────┤
│ extra (L12)                  │                  │                       │
├──────────────────────────────┼──────────────────┼───────────────────────┤
│ pancakes (declaration L5)    │                  │                       │
└──────────────────────────────┴──────────────────┴───────────────────────┘
```

**(c)** Fill the lifetime category (Sebesta §5.4.3): `static`,
`stack-dynamic`, or `explicit-heap`. [3 pts]

```
┌──────────────────────────────┬───────────────────────────────────────────┐
│ Entity                       │ Lifetime                                  │
├──────────────────────────────┼───────────────────────────────────────────┤
│ flour                        │                                           │
├──────────────────────────────┼───────────────────────────────────────────┤
│ extra                        │                                           │
├──────────────────────────────┼───────────────────────────────────────────┤
│ function double              │                                           │
└──────────────────────────────┴───────────────────────────────────────────┘
```

**(d)** Is `let extra : int = 2` on line 12 a shadowing violation?
(Yes / No + 1 sentence citing Decision #12.) [3 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**(e)** Name **one** identifier in this program whose binding is resolved
purely at **compile time**, AND **one** whose value is resolved at
**run time**. [2 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Compile-time:                                                            │
│ Run-time:                                                                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Q4. [12 pts, 10 min] Grammar modification

> The current Recipix expression cascade fragment is:
> ```
> <mul_expr> ::= <unary> { ("*" | "/") <unary> }
> <unary>    ::= "-" <unary> | "!" <unary>
>             |  "quantity_of" "(" <expr> ")"
>             |  <primary>
> <primary>  ::= INT_LIT [ UNIT_KW ] | FLOAT_LIT [ UNIT_KW ]
>             |  STRING_LIT | BOOL_LIT | IDENT
>             |  IDENT "(" [ <args> ] ")"
>             |  "(" <expr> ")"
> ```
>
> **Rewrite the above** to make TWO modifications:
>
> **(1)** Add a **postfix** `?` operator (boolean exists-check, e.g. `flour?`).
> It has the **highest precedence** — higher than `quantity_of`. Apply
> postfix to `<primary>` so that `quantity_of(flour)` is unchanged but
> `flour?` becomes a valid `<unary>` operand.
>
> **(2)** Add a **prefix** `sqrt` unary operator. It has **lower precedence**
> than unary `-` and `!`, but **higher precedence** than `*` and `/`.

Write the modified rules (you may rename productions if needed):

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Q5. [8 pts, 6 min] Code annotation

> For each marked line of parser code, write which **Decision (#XX)** is
> enforced. [2 pts each]

```
# In _parse_primary:
if tok.type == INT_LIT:
    self._advance()
    if self._check(UNIT_KW):                      ← (a) Decision #______
        unit_tok = self._advance()
        return QuantityLit(...)

# In _parse_unary:
if tok.type == 'quantity_of':                     ← (b) Decision #______
    self._advance()
    self._expect(LPAREN, ...)
    operand = self._parse_expr()

# In _parse_substitute_call:
orig_tok = self._peek()
if orig_tok.type != IDENT:                        ← (c) Decision #______
    raise ParseError("must be a bare identifier")

# In _parse_if_stmt:
self._expect(LBRACE, "...braces are mandatory")   ← (d) Decision #______
```

---

## PART B — General PL on Sebesta Ch. 1, 3, 4, 5 (38 pts, ~35 min)

---

### Q6. [10 pts, 8 min] Weakest preconditions (Sebesta §3.5.3)

> For each Recipix-style assignment with the given postcondition, compute
> the **weakest precondition**. Simplify where possible. [2.5 pts each]

```
┌──────────────────────────────────────────────────┬───────────────────────┐
│ Statement + postcondition                        │ Weakest precondition  │
├──────────────────────────────────────────────────┼───────────────────────┤
│ x = 2 * y - 3      { x > 5 }                     │                       │
├──────────────────────────────────────────────────┼───────────────────────┤
│ y = 3 * x + 1      { y < 10 }                    │                       │
├──────────────────────────────────────────────────┼───────────────────────┤
│ a = a + 2 * b      { a > 4 }                     │                       │
├──────────────────────────────────────────────────┼───────────────────────┤
│ z = (n + 6) / 2    { z >= 5 }                    │                       │
└──────────────────────────────────────────────────┴───────────────────────┘
```

---

### Q7. [12 pts, 10 min] Attribute grammar (Sebesta §3.4)

> Given the BNF below, write an **attribute grammar** for a language where
> data types **cannot be mixed in expressions**, but assignment statements
> **need not** have matching types on both sides.
>
> ```
> <assign>  →  <var> = <expr>
> <expr>    →  <var>[2] + <var>[3] | <var>
> <var>     →  A | B | C
> ```
>
> Assume each `<var>` has a synthesized attribute `.actualType` based on
> which letter it is (the lexer provides this).

**(a)** Write the semantic rule and predicate for `<expr> → <var>[2] + <var>[3]`: [5 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Semantic rule:                                                           │
│                                                                          │
│ Predicate:                                                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**(b)** Write the semantic rule for `<expr> → <var>`: [3 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Semantic rule:                                                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**(c)** Are there any predicates on `<assign>`? Yes / No + 1 sentence. [2 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**(d)** Is `.actualType` a **synthesized** or **inherited** attribute? (1 word) [2 pts]

```
┌────────────────────┐
│                    │
└────────────────────┘
```

---

### Q8. [10 pts, 10 min] State transition diagram (Sebesta Ch. 4)

> Draw a state transition diagram for a lexical analyzer that recognizes
> three Recipix token types:
> - `IDENT`     : `[a-zA-Z_][a-zA-Z0-9_]*`
> - `INT_LIT`   : `[0-9]+`
> - `FLOAT_LIT` : `[0-9]+\.[0-9]+`  (digit required on BOTH sides of the dot)
>
> Use character classes `letter`, `digit`, `_` for transitions. Show:
> the start state, all intermediate states, accepting states (labeled with
> their token type), and what happens if `.` is **not** followed by a digit.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Q9. [6 pts, 5 min] Static vs dynamic scoping

> Which scoping discipline does Recipix use, and what would break if you
> switched? (2–3 sentences, cite Sebesta §5.5.) [6 pts]

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

# 🛑 STOP — DO ALL QUESTIONS ON PAPER FIRST 🛑

---
---
---

# MODEL ANSWERS

> Each model is the **minimum** that earns full credit. Grading callouts
> below each show where points are awarded and where students typically
> lose them.

---

## Q1 Model Answer (15 pts)

**(a) AST [6 pts]:**

```
                       BinaryOp(+)
                      /           \
              BinaryOp(*)           QuantityLit ✦
              /         \           (100, 'g')
       QuantityOf  ★    IntLit
            |            (2)
       Identifier
        ('flour')
```

**Grading callouts:**
- 2 pts: root is `BinaryOp(+)` (not flat, not `*` at top — common mistake:
  forgetting `*` binds tighter than `+`)
- 2 pts: `QuantityOf` is a **dedicated node**, not `FunctionCall('quantity_of', ...)`
- 1 pt: `QuantityLit` carries both number and unit (not two separate nodes)
- 1 pt: all leaves correctly typed (`Identifier`, `IntLit`)

**(b) ★ on `QuantityOf` [2 pts]** — Decision #34 is enforced in `_parse_unary`'s
dedicated branch *before* `_parse_primary` is reached.

**(c) ✦ on `QuantityLit(100, 'g')` [2 pts]** — Decision #7: `_parse_primary`
saw `INT_LIT(100)` then peeked one token ahead for `UNIT_KW('g')`.

**(d) Production [3 pts]:**
```
<add_expr> ::= <mul_expr> { ("+" | "-") <mul_expr> }
```
The root `BinaryOp(+)` is produced by one iteration of the `{ ... }` loop.

**(e) Structural difference [2 pts]:** The left and right children of the
root `BinaryOp(+)` are **swapped** — the `QuantityLit(100,'g')` becomes the
left child and the `BinaryOp(*)` subtree becomes the right child. The
internal structure of each subtree is unchanged.

---

## Q2 Model Answer (12 pts, 3 each)

| Input | OK / REJECT | Decision + function |
|---|---|---|
| `if x > 0 combine(flour)` | **REJECT** | **Decision #20** — `_parse_if_stmt`'s `_expect(LBRACE, ...)` after the condition |
| `substitute(r, milk + sugar, with:oat, ratio:1)` | **REJECT** | **Decision #35** — `_parse_substitute_call`'s comma-lookahead guard fires at `+` (not at `,`) after the IDENT `milk` |
| `step "Mix" for 5 min at 180 °C { add(x) }` | **REJECT** | **Decision #23** — `_parse_step_decl` raises after seeing `at` following `for` |
| `a == b == c` | **REJECT** | **Decision #17** — `_parse_eq`'s non-associativity check fires at the second `==` |

**Grading callouts:**
- 1 pt each for OK/REJECT correct
- 1 pt each for naming the right Decision number
- 1 pt each for naming the right parser function (or close — `_parse_substitute_call` vs `parse_substitute` is fine)
- Common loss: confusing Decision #20 with mandatory-braces on `else` only,
  or confusing #17 with general operator precedence

---

## Q3 Model Answer (15 pts)

**(a) Arrows [3 pts]:** All four `servings` references on lines 5
(after `serves`), 6, 7, and 11 point to the **declaration on line 5**
(`recipe pancakes(servings: int)`). The reference on line 16
(`pancakes(servings: 6)`) is a **keyword argument**, not a reference to the
parameter — it is the *name* of the parameter at the call site, not a
resolution of the variable.

(Grading tip: drawing an arrow from L16's `servings` to L5's declaration is
not penalized as long as the student is consistent. The cleanest answer notes
the L16 case is a kwarg label.)

**(b) Binding times [4 pts, 0.5 each]:**

| Entity | TYPE | VALUE |
|---|---|---|
| `flour` (L6) | compile | run (recipe instantiation) |
| `total` (L10) | compile | run (when control reaches L10) |
| `extra` (L12) | compile | run (when control enters if-then) |
| `pancakes` decl (L5) | compile | compile |

**Grading callout:** the recipe **declaration** is bound at compile time
for both type and value — the recipe object itself is determined entirely
from program text. Confusing this with "the recipe is called at runtime"
is the most common mistake.

**(c) Lifetimes [3 pts]:**

| Entity | Lifetime |
|---|---|
| `flour` | stack-dynamic |
| `extra` | stack-dynamic |
| `function double` | static |

**(d) Shadowing? [3 pts]:** **No.** `extra` is not visible in any enclosing
scope — it is introduced for the first time on line 12. Decision #12
prohibits *redeclaring* an identifier visible in an enclosing scope, which
is not the case here (`n` from the `double` function is in a separate scope
entirely).

**(e) Compile-time / run-time [2 pts]:**
- Compile-time: `pancakes`, `double`, `flour` (the type, not value)
- Run-time: `servings` (parameter value), `extra` (value), `total` (value)

Any one from each list earns full credit.

---

## Q4 Model Answer (12 pts)

```
<mul_expr>  ::= <sqrt_expr> { ("*" | "/") <sqrt_expr> }

<sqrt_expr> ::= "sqrt" <sqrt_expr> | <unary>

<unary>     ::= "-" <unary> | "!" <unary>
             |  "quantity_of" "(" <expr> ")"
             |  <postfix>

<postfix>   ::= <primary> { "?" }

<primary>   ::= INT_LIT [ UNIT_KW ] | FLOAT_LIT [ UNIT_KW ]
             |  STRING_LIT | BOOL_LIT | IDENT
             |  IDENT "(" [ <args> ] ")"
             |  "(" <expr> ")"
```

**Grading callouts:**
- **4 pts** for `<postfix>` correctly between `<primary>` and `<unary>` —
  this ensures `?` has higher precedence than `quantity_of` because it's
  reached before `<unary>` falls through. Common mistake: putting `<postfix>`
  inside `<unary>` itself, which makes `?` same level as `quantity_of`, not
  higher.
- **4 pts** for `<sqrt_expr>` correctly between `<unary>` and `<mul_expr>`.
  Must reference `<sqrt_expr>` from `<mul_expr>` (not `<unary>`). Recursive
  call `"sqrt" <sqrt_expr>` makes it right-associative.
- **2 pts** for the `{ "?" }` loop form (left-associative postfix — correct
  for chained postfix operators like `x??`).
- **2 pts** for not breaking the existing precedence chain — every
  alternative must reach the level below it correctly.

**Common mistake:** writing `"sqrt" <unary>` instead of `"sqrt" <sqrt_expr>`.
That makes `sqrt sqrt x` parse weirdly (would go to `<unary>` which then
falls to `<sqrt_expr>` again via `<mul_expr>` — actually it would just
fail). Always use the **same** non-terminal for the recursive case in a
right-associative unary rule.

---

## Q5 Model Answer (8 pts, 2 each)

- (a) **Decision #7** — two-token quantity literal: an `INT_LIT` may be
  followed by an adjacent `UNIT_KW` to form a `QuantityLit`.
- (b) **Decision #34** — `quantity_of` as dedicated unary operator, NOT a
  function call; intercepted at the unary level before `_parse_primary` is
  reached.
- (c) **Decision #35** — `substitute` slots must be bare identifiers, not
  arbitrary expressions.
- (d) **Decision #20** — mandatory braces on `if`/`else` bodies; eliminates
  dangling-else ambiguity by construction.

---

## Q6 Model Answer (10 pts, 2.5 each)

| Statement | WP (substituted) | WP (simplified) |
|---|---|---|
| `x = 2*y - 3 {x > 5}` | `2*y - 3 > 5` | `y > 4` |
| `y = 3*x + 1 {y < 10}` | `3*x + 1 < 10` | `x < 3` |
| `a = a + 2*b {a > 4}` | `a + 2*b > 4` | `a + 2*b > 4` (no simpler form) |
| `z = (n+6)/2 {z >= 5}` | `(n+6)/2 >= 5` | `n + 6 >= 10` → `n >= 4` |

**Grading callouts:**
- The rule (Sebesta §3.5.3): `wp(x = E, R) = R[E/x]` — substitute every
  occurrence of `x` in `R` with `E`.
- 2 pts each for correct substitution; 0.5 pt each for simplification.
- **Common mistake on row 3:** confusing the `a` on the RHS with the
  post-assignment `a`. The `a` in `a + 2*b` is the **pre-assignment** value —
  the assignment hasn't happened yet, so this is the OLD `a`. The
  substitution is straightforward.
- **Common mistake on row 4:** simplifying integer division wrongly.
  `(n+6)/2 >= 5` ⟺ `n+6 >= 10` is valid for integer division because
  multiplying by the positive divisor preserves direction.

---

## Q7 Model Answer (12 pts)

**(a) [5 pts]:**
```
Semantic rule: <expr>.actualType ← <var>[2].actualType
Predicate:     <var>[2].actualType == <var>[3].actualType
```
**Grading callouts:**
- 2 pts for the semantic rule (correctly synthesizes from either child since
  they match by the predicate)
- 3 pts for the predicate (must use `==` and reference both children's
  `.actualType`)
- The predicate is what enforces "types cannot be mixed" — if it fails,
  the parse tree is rejected as semantically invalid.

**(b) [3 pts]:**
```
Semantic rule: <expr>.actualType ← <var>.actualType
```
Trivial pass-through synthesis from the single child.

**(c) [2 pts]:** **No.** The problem states that assignment statements need
**not** have matching types, so there is no type-equality predicate at the
`<assign>` level. (If the problem had said "must match," the predicate
would be `<var>.actualType == <expr>.actualType`.)

**(d) [2 pts]:** **Synthesized.** The attribute flows **up** the parse tree
from `<var>` leaves (where it's determined by the lexer) to `<expr>`
internal nodes. Inherited attributes flow *down* — not the case here.

---

## Q8 Model Answer (10 pts)

```
                  letter | _
              ┌─────────────────┐
              ↓                 │   letter | digit | _
            ┌───┐               │ ┌──────┐
            │ S₁│ ──────────────┘ │      │
   letter|_ │   │ ◀───────────────┘      │ (accept IDENT)
  ┌────────▶└───┘                        │
  │
[S₀ start]
  │           digit
  ├────────▶┌───┐ ───────┐ digit
  │ digit   │ S₂│  ◀─────┘
  │         └───┘  (accept INT_LIT)
  │           │
  │           │ '.'
  │           ↓
  │         ┌───┐  digit   ┌───┐ ────┐ digit
  │         │ S₃│ ────────▶│ S₄│ ◀───┘
  │         └───┘          └───┘  (accept FLOAT_LIT)
  │           │
  │           │ NOT digit
  │           ↓
  │         ┌───────┐
  │         │ ERROR │
  │         └───────┘
  │
  └─ other chars → outside this DFA
```

**Required elements (per the prompt) [grading]:**
- **2 pts** Start state `S₀` clearly marked.
- **2 pts** Accepting state for `IDENT` (S₁), with self-loop on `letter | digit | _`.
- **2 pts** Accepting state for `INT_LIT` (S₂), with self-loop on `digit`.
- **2 pts** Path from S₂ via `.` to S₃ (non-accepting), then S₃ via `digit`
  to S₄ (accepting `FLOAT_LIT`).
- **2 pts** S₃ → ERROR if `.` not followed by a digit (this is the
  Recipix-specific rule: `1.` is invalid; must have digit on both sides).

**Common mistakes:**
- Making S₃ accepting (it isn't — `1.` is not a valid FLOAT_LIT).
- Missing the self-loop on S₁ allowing digits and underscores after the
  first character.
- Confusing the regex `[0-9]+\.[0-9]+` with `[0-9]+\.[0-9]*` (the latter
  would accept `1.` which Recipix does not).

---

## Q9 Model Answer (6 pts)

Recipix uses **static (lexical) scoping** (Sebesta §5.5) — name resolution
follows the program's textual block-nesting structure. If we switched to
dynamic scoping, name resolution would follow the **call chain**, so a
function like `double(n: int)` would resolve `n` differently depending on
which recipe called it, breaking referential transparency. Static scoping
is essential to our **reliability** evaluation criterion: a reader must be
able to determine what `flour` refers to from the source text alone, not
from the runtime call path. Dynamic scoping would also conflict with
Decision #12 (no shadowing) because shadow-resolution under dynamic scoping
depends on call timing, not declaration position.

**Grading callouts:**
- **2 pts** for "static/lexical" (must use one of these terms)
- **2 pts** for explaining WHAT would break with dynamic — must reference
  call chain, runtime resolution, or similar
- **2 pts** for tying it to a Recipix evaluation criterion (reliability,
  no-shadowing, or referential transparency)

---

# Self-Grading Reference

| Q | Max | What "A" looks like |
|---|---|---|
| Q1 | 15 | AST correct (* below +), QuantityOf/QuantityLit as dedicated nodes, ★ and ✦ in right places, production for root, "children swapped" |
| Q2 | 12 | All 4 rejected, correct Decision number for each, correct parser function for each |
| Q3 | 15 | All arrows correct, full binding-time table, lifetime categories correct, "No shadowing — extra is fresh" |
| Q4 | 12 | `<sqrt_expr>` between unary and mul_expr (right-recursive), `<postfix>` between primary and unary with `{?}` |
| Q5 | 8 | All four Decisions correctly named (#7, #34, #35, #20) |
| Q6 | 10 | All four WPs correct via substitution; bonus for simplification |
| Q7 | 12 | Semantic rule + predicate correct; "synthesized" identified |
| Q8 | 10 | Start state, S₁/S₂/S₄ accepting with token labels, S₃ non-accepting, ERROR path for `1.` |
| Q9 | 6 | "Static" named, dynamic-scoping breakage explained, tied to reliability or Decision #12 |

**Pass threshold for A (Excellent): 85+ / 100**

---

# Final Pre-Exam Checklist

Before you start the real exam:

1. **Read every question's sub-parts FIRST** — underline each separate
   sub-ask. The professor stacks 2-4 asks per question; missing one is the
   #1 way to lose points.
2. **Budget time strictly:** 9 min/question average. After 9 minutes on
   a question, MOVE ON even if incomplete. Come back if time permits.
3. **For drawing questions:** make your trees BIG and use straight lines.
   Smudged or cramped trees get marked harshly even when correct.
4. **For "given input, what does parser do" questions:** name the *specific
   function* in your parser. Not "the parser rejects it" — "`_parse_rel`
   rejects it at the second `<` via the non-associativity check."
5. **For trade-off questions:** always mention an *alternative not taken*.
   Rubric reward.

You've prepared. Sleep more than you study tonight.
