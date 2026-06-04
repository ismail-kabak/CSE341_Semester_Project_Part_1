# CSE 341 — Exam 2 Study Notes
### Recipix · Berk Hakan Öge (210104004132) · 28 May 2026, 90 min written

> **Exam scope (handout §3.3):** Sebesta **Ch. 6 (Types)** and **Ch. 7
> (Expressions & Assignment)**, with possible reference back to
> Ch. 1, 3, 4, 5. Personalised paper — questions about *your* project
> components (parser P1, interpreter, rendering, D1 §4.3 / §4.4 / §4.7,
> your four §4.8 rationale paragraphs).
>
> **You may bring 3 sheets of A4 handwritten notes, one side each.**
>
> ---
>
> **This document has three parts:**
>
> - **Part 1** — Read-through material. Sebesta Ch. 1 to Ch. 7 mapped
>   to Recipix's design decisions, with the *why* behind each. Read
>   this end to end at least twice before the exam.
> - **Part 2** — Cheat-sheet material. The dense reference content
>   you'll copy onto your three A4 sheets.
> - **Part 3** — Practice Q&A. 25 questions with worked answers,
>   covering project-specific defenses, Sebesta cold questions, and
>   trace-through questions.

---
---

# PART 1 — Sebesta Read-Through (Ch. 1 to Ch. 7, mapped to Recipix)

## Chapter 1 — Preliminaries

### 1.1 Why programming languages? (§1.1)

Programming languages exist to express computation in a form that
*humans can write* and *machines can execute*. The trade-offs between
these two goals shape every design decision.

### 1.2 The four evaluation criteria (§1.3)

Sebesta names four orthogonal criteria for evaluating a language:

| Criterion | Definition | Recipix's stance |
|---|---|---|
| **Readability** | How easily the program can be read and understood | Good — domain-specific keywords (`serves`, `at`, `for`, action verbs); mandatory braces (#20); explicit `quantity_of` for clarity |
| **Writability** | How easily the language can be used to create programs | High for domain users — implicit `Ingredient → Quantity` projection (#31), keyword-argument recipe calls |
| **Reliability** | How likely is program to perform its specifications | **Highest priority** — strong typing (#8), no shadowing (#12), single-assignment (#13), dimensional discipline, non-associative comparison (#17), `evaluate`-only constraint on `scale`/`substitute` |
| **Cost** | Training, writing, compiling, executing, maintaining cost | **Deprioritized** — interpreter is tree-walking; no optimization; type checker over-checks for safety |

### 1.3 Language categories (§1.4)

| Category | Examples | Recipix? |
|---|---|---|
| Imperative | C, Java, Python | Mostly — statements drive execution |
| Functional | Haskell, ML | Hybrid — every expression is referentially transparent (no mutation), so functional flavor |
| Object-oriented | Smalltalk, Java | No — no classes, no inheritance |
| Logic | Prolog | No |

Recipix is **imperative with strong functional discipline** — the
statements drive control flow, but every expression is referentially
transparent because there is no mutation (decision #16 collapses
parameter passing, decision #25 forces functional `scale`/`substitute`,
decision #27 forbids assignment-as-expression).

### 1.4 The one-liner you must be able to say cold

> **"What makes Recipix a DSL and not a generic scripting language?"**
>
> **Dimensional type discipline.** A general-purpose language treats
> `200` and `500` as raw numbers. Recipix lifts the dimensional
> structure into the type system — adding grams to milliliters is a
> compile-time error. The three domain-specific operations
> (`evaluate`, `scale`, `substitute`) and the structured types
> (`Recipe`, `Ingredient`) all exist to preserve this invariant.

---

## Chapter 3 — Describing Syntax and Semantics

### 3.1 BNF and EBNF (§3.1, §3.2)

**BNF** defines context-free grammars: nonterminals, terminals,
productions, and the `::=` form. **EBNF** extends BNF with optional
groups `[ ... ]`, repetition `{ ... }`, and choice `|`.

Recipix's grammar uses EBNF (D1 §4.3). Example productions:

```
<expr>      ::= <or_expr>
<or_expr>   ::= <and_expr> { "||" <and_expr> }     // repetition
<if_stmt>   ::= "if" <expr> <block> [ "else" <block> ]   // optional
<unary>     ::= "-" <unary>
              | "!" <unary>
              | "quantity_of" "(" <expr> ")"        // choice
              | <primary>
```

### 3.2 Grammar properties (§3.3)

- **Unambiguous**: every legal program has exactly one parse tree.
  Recipix's grammar is unambiguous on the implemented subset because
  precedence is encoded directly in the production ladder, comparisons
  are non-associative (no `a < b < c` ambiguity), and `if/else`
  blocks are mandatory-braced (no dangling-else).
- **Left-recursive vs. right-recursive**: recursive-descent parsers
  cannot handle direct left recursion. Recipix uses *iteration* for
  left-associative binary operators (`{ ... }`) and *right recursion*
  for unary prefix operators.

### 3.3 Operational semantics (§3.5)

There are three common ways to describe meaning:

| Style | Description | Recipix uses? |
|---|---|---|
| **Operational** | Defines meaning by abstract-machine transitions | Yes — D1 §4.4 uses big-step operational |
| **Denotational** | Maps programs to mathematical functions | No |
| **Axiomatic** | Uses preconditions/postconditions (Hoare logic) | No, and handout forbids it for the project |

**Big-step operational** writes rules like:

```
   <r, S> -> RtRecipe(name, n, ingredients, ...)
   <k, S> -> k : (int | float),  k > 0
   n' = int(round(n * k))
   ... ingredients' computed ...
   ... step bodies re-executed under S_scaled with servings = n' ...
   ───────────────────────────────────────────────────────────────
   <scale(r, by: k), S> -> RtRecipe(name, n', ingredients', steps', ...)
```

You read this as: "given the premises above the line, the conclusion
below the line holds." The state `S` is an environment; the relation
`→` is "evaluates to." Recipix's D1 §4.4 gives big-step operational
semantics for `scale` and `foreach`.

---

## Chapter 4 — Lexical and Syntax Analysis

### 4.1 Lexer / Parser separation

- **Lexer**: source string → token stream.
- **Parser**: token stream → AST.

Recipix's `src/lexer.py` (İsmail) produces tokens consumed by
`src/recipix/parser.py` (Berk). The token contract is defined in
`src/recipix/tokens.py`.

### 4.2 Token categories in Recipix

| Category | Examples |
|---|---|
| Identifier | `flour`, `pancakes`, `oat_milk` |
| Integer literal | `200`, `0`, `42` |
| Float literal | `1.5`, `0.5` |
| String literal | `"Cook batches"` |
| Boolean | `true`, `false` (produce `BOOL_LIT`, not keyword tokens) |
| Reserved keyword | `recipe`, `function`, `let`, `if`, `else`, `repeat`, `foreach`, `scale`, ... |
| Type-name keyword | `int`, `float`, `bool`, `Mass`, `Volume`, ... |
| Action-verb keyword | `combine`, `mix`, `pour`, `bake`, `flip`, ... |
| Unit keyword | `g`, `kg`, `ml`, `°C`, `min`, `pinch`, ... |
| Operator | `+ - * / == != < <= > >= && || ! =` |
| Separator | `( ) { } [ ] , : ->` |

### 4.3 Recursive-descent parsing (§4.4)

A recursive-descent parser has *one function per nonterminal*. The
function consumes tokens and returns an AST node. Recipix's parser
follows this pattern:

```
_parse_or      → _parse_and    → _parse_eq → _parse_rel
              → _parse_add    → _parse_mul → _parse_unary → _parse_primary
```

The precedence ladder is **encoded in the call order** — `_parse_or`
calls `_parse_and`, which calls `_parse_eq`, etc. Higher-precedence
operators bind tighter because they sit closer to `_parse_primary`
in the call chain.

### 4.4 Two-token quantity literals (decision #7)

Quantity literals are **two tokens**: a numeric literal followed by a
unit keyword. The lexer never combines them. The parser, at
`_parse_primary`, peeks the next token after an `INT_LIT` or
`FLOAT_LIT`: if it's a `UNIT_KW`, both get consumed into a
`QuantityLit` AST node.

**Why two tokens?** A single-token approach would force the lexer to
know every unit keyword (fragile); two-token form lets the parser
glue them in one production. Trade-off: `200g` (no separator) is a
lexer error, slightly verbose for users.

---

## Chapter 5 — Names, Bindings, and Scopes

### 5.1 Identifier rules (§5.2)

Recipix identifiers match `[a-zA-Z_][a-zA-Z0-9_]*`, ASCII only,
case-sensitive, no hyphens. They cannot collide with reserved
keywords, type-name keywords, action-verb keywords, or unit keywords.

### 5.2 Binding times (§5.3)

| Binding | Time | Recipix instance |
|---|---|---|
| Language definition | Language design | The 35 decisions in spec §12 |
| Language implementation | Compiler/interpreter design | Python 3.11+, no third-party deps |
| Compile time | When the source is processed | Recipe/function names + signatures; ingredient *types*; `let`-bound *types* |
| Link time | When code is linked | Not applicable in Recipix |
| Load time | When the program loads | Not applicable |
| Run time | When execution begins | Ingredient *values*; recipe/function *parameters*; `foreach` loop variables; `let`-bound *values* |

### 5.3 Static vs. dynamic scoping (§5.5)

**Static (lexical) scoping**: a name's binding is determined by the
program text where it appears. Resolution walks the lexical parent
chain.

**Dynamic scoping**: a name's binding is determined by the most recent
caller at run time. Resolution walks the call stack.

**Recipix uses static scoping (decision #11).** Each block opens a
fresh scope; inner scopes see outer-scope names; lookup walks the
parent-pointer chain in the `Environment` class.

**What would break under dynamic scoping?** Two things:

1. `quantity_of(flour)` would resolve `flour` through whichever scope
   happened to be active at run time — destroying the type rule that
   `quantity_of` returns the dimension of the operand's quantity field.
2. `substitute(r, milk, with: oat_milk, ratio: 1.0)` would resolve
   `milk` against the caller's scope, not the recipe's — contradicting
   decision #28 (ingredient identity is the symbol-table binding).

### 5.4 No shadowing + single-assignment (#12, #13)

- **No shadowing (#12)**: declaring an identifier already visible in
  any enclosing scope is a compile-time error. Enforced by
  `Environment.declare_check()` which walks the parent chain.
- **Single-assignment (#13)**: `let`-bound names, ingredient names,
  and parameters are bound exactly once. Loop variables in `foreach`
  rebind across iterations but are immutable within a single
  iteration.

### 5.5 Lifetime (§5.4)

| Entity | Lifetime |
|---|---|
| Recipe / function declarations | Static (whole program) |
| Recipe parameters | Stack-dynamic, per instantiation |
| Function parameters | Stack-dynamic, per call |
| Ingredients within a recipe | Stack-dynamic, per instantiation |
| `let`-bound names | Stack-dynamic, per enclosing scope |
| `foreach` loop variables | Stack-dynamic, per iteration |

No **explicit-heap-dynamic** lifetimes exist in Recipix v1: no `new`
operator, no malloc-style allocation exposed to the user.

---

## Chapter 6 — Data Types

### 6.1 Primitive types (§6.2)

A primitive type is one whose values are not composed of other types
in the language definition. Recipix has:

- `int` — 64-bit signed integer, value set $[-2^{63}, 2^{63} - 1]$.
- `float` — IEEE 754 double.
- `bool` — $\{\text{true}, \text{false}\}$.
- Five **Quantity types**: `Mass`, `Volume`, `Count`, `Temperature`,
  `Duration`. Each has an internal numeric value (in the dimension's
  base unit) and a dimension tag. Sebesta's framing: a primitive type
  is defined by *the operations it supports*, not what it stores.
  Quantities support arithmetic with same-dimension operands and
  scalar multiplication.
- `Pinch` — separate primitive (decision #4). Admits no arithmetic,
  no comparison, no scaling, no substitution-by-ratio. Constructed
  only by the literal `1 pinch`.

**Why is Pinch a separate primitive rather than `Quantity<Pinch>`?**
Because as `Quantity<D>` with `D = Pinch`, every operation on
`Quantity<D>` would need a `Pinch` branch in its type rule. As a
separate primitive, the carve-out lives in the type checker's
per-operation entry points (`_check_BinaryOp` calls `_reject_pinch`),
and the rest of the code never sees Pinch.

### 6.2 Structured types (§6.5 – §6.7)

A structured type is built from other types. Recipix has:

- **`Ingredient`** — a record with `name : str` and `quantity :
  Quantity<D> | Pinch`.
- **`Recipe`** — a record `{name, servings, ingredients, steps}`.
- **`Step`** — a record `{description, temperature?, duration?, actions}`.
- **`List<T>`** — homogeneous list of `T`. No user-facing indexing.
  `foreach` is the only iteration form.

**List design decisions** (Sebesta §6.5):

| Decision | Choice |
|---|---|
| Element type | Homogeneous — every element same type |
| Index range | Not user-facing — no `list[i]` |
| Subscript-check semantics | Not applicable |
| Static vs. dynamic | Element type **inferred** at literal construction |
| User-writable type annotation | **Not allowed** in v1 (decision #32) |
| Empty-list behavior | `foreach` produces zero iterations, no error |

### 6.3 Type equivalence (§6.14)

Sebesta typically frames type equivalence as a *one-rule-per-language*
choice:

- **Name equivalence**: two types are the same only if they have the
  same declared name. Strict; predictable; can require redundant
  re-declaration.
- **Structural equivalence**: two types are the same if they have the
  same shape (field types and order). Flexible; can cause accidental
  collisions when two different records happen to share a shape.

**Recipix uses a deliberate split (decision #10):**

| Type | Rule | Reasoning |
|---|---|---|
| `Quantity<D>` | structural | Dimension is what matters; unit is representation |
| `Ingredient` | structural | Transparent two-field record; v1's closed type-name set forecloses collisions |
| `List<T>` | structural in parameter, nominal in constructor | Standard treatment for parametric types (ML, Haskell, Java generics) |
| `Recipe` | **name** | Identity matters; `pancakes` and `crepes` should never be interchangeable |

The split is defensible because **records modeling data shape** want
structural (the field set carries meaning), while **records modeling
identity** want name (the declaration site carries meaning).

### 6.4 Coercion (§7.4)

A **coercion** is an implicit type conversion. There are two
directions:

- **Widening**: information-preserving (e.g. `int → float` for values
  ≤ 2^53).
- **Narrowing**: information-losing (e.g. `float → int` — truncates
  the fractional part).

Sebesta §7.4 flags narrowing coercions as the **dangerous kind**
because they can cause silent data loss.

**Recipix's coercion rules:**

- `int → float` widening: **allowed** in mixed-mode arithmetic.
- Within-dimension unit coercion (`g ↔ kg`, `ml ↔ l`): **allowed**.
  This is representation-only — the dimension is preserved.
- `float → int` narrowing: **never** implicit. A v2 `to_int(x)`
  builtin is reserved for explicit conversion.
- Cross-dimension coercion: **never**. There is no implicit `Mass → Volume`
  even with a density.

### 6.5 Type checking (§6.13)

Recipix does **compile-time** (static) type checking. The type
checker walks the AST after parsing and:

1. Builds top-level symbol tables (recipes, functions).
2. Rewrites `AmbiguousCall` nodes to `FunctionCall` or `RecipeCall`
   via name lookup.
3. Walks each declaration's body, opening fresh scopes, declaring
   names via `Environment.declare_check + define`, annotating every
   Expr node with `.inferred_type`.
4. Raises `TypeCheckError(error_code=N, line, col, message)` on the
   first violation of any of the 19 spec §10 errors.

---

## Chapter 7 — Expressions and Assignment

### 7.1 Operator precedence (§7.2)

**Precedence** determines which operator binds tighter when multiple
operators appear without explicit grouping. Recipix's seven-level
ladder (D1 §4.7):

| Level | Operators | Associativity |
|---|---|---|
| 1 | unary `-`, `!`, `quantity_of(...)` | right |
| 2 | `*`, `/` | left |
| 3 | `+`, `-` (binary) | left |
| 4 | `<`, `<=`, `>`, `>=` | **non-associative** |
| 5 | `==`, `!=` | **non-associative** |
| 6 | `&&` | left |
| 7 | `||` | left |

Higher level = tighter binding. `1 + 2 * 3` parses as `1 + (2 * 3)`
because level 2 (`*`) is tighter than level 3 (`+`).

### 7.2 Associativity (§7.2)

**Associativity** determines the grouping when the same-precedence
operator appears twice. Three options:

- **Left-associative**: `a OP b OP c` = `(a OP b) OP c`. Standard
  for `+`, `-`, `*`, `/`, `&&`, `||`.
- **Right-associative**: `a OP b OP c` = `a OP (b OP c)`. Standard
  for prefix unary operators and for `?:` in C.
- **Non-associative**: `a OP b OP c` is a **parse error**. The user
  must parenthesize.

Recipix uses non-associative for comparisons (#17) to catch chained-
comparison bugs at parse time.

### 7.3 Operand evaluation order (§7.6)

In an expression like `f() + g()`, which operand is evaluated first?

- **Unspecified**: C, C++. Compilers can reorder for optimization.
  The same program can produce different results on different
  platforms if either operand has side effects.
- **Left-to-right**: Java, Python.
- **Right-to-left**: rare.

**Recipix locks left-to-right, fully defined (decision #18).**
Stronger than C; weaker than nothing-could-be-different (because in
absence of side effects, order is unobservable). The reason this
matters: error reporting. `let x : int = f(a/0) + g(b/0)` raises
division-by-zero from `a/0` first, predictably.

### 7.4 Short-circuit evaluation (§7.5)

`&&` and `||` can either:

- **Eagerly evaluate** both operands.
- **Short-circuit**: if the left operand determines the result, skip
  the right.

Recipix uses short-circuit (left-to-right). This is the standard
choice — eager `&&` would force `if x != null && x.field > 0` to
nest as two `if`s.

### 7.5 Assignment (§7.6)

In some languages (C, C++, Java), assignment is an **expression**:
`x = y + 1` has a value (the new value of `x`) and can appear inside
other expressions. This enables `while ((line = read()) != null)`
patterns but also `if (x = 0)` bug patterns.

In other languages (Pascal, Python's statement form), assignment is a
**statement** with no value.

**Recipix: assignment is a statement, not an expression (decision #27).**
The only binding form is `let <name> : <type> = <expr>`. There is no
compound assignment (`+=`, `*=`), no increment (`++`), and no
augmented assignment. Combined with no-shadowing (#12) and
single-assignment (#13), every name's value is determined entirely by
its initializer expression. **Every expression in Recipix v1 is
referentially transparent.**

### 7.6 The "what's an expression" inventory in Recipix

| Expression form | Spec section | Example |
|---|---|---|
| Literal | §1 | `200`, `1.5`, `"Mix dry"`, `true`, `1 pinch` |
| Quantity literal (two tokens) | §1 decision #7 | `200 g`, `180 °C` |
| Identifier | §1 | `flour`, `servings` |
| Binary arithmetic | §3 | `flour + 100 g` |
| Comparison | §4 | `flour > 100 g` |
| Logical | §4 | `x && y`, `!x` |
| Unary minus / not | §5 | `-x`, `!y` |
| `quantity_of(<expr>)` | §2 #34 | `quantity_of(flour)` |
| Function call | §7 | `half(servings)` |
| Recipe call | §7 | `pancakes(servings: 4)` |
| `scale(<recipe>, by: <scalar>)` | §9 | `scale(pancakes(servings: 4), by: 1.5)` |
| `substitute(<recipe>, IDENT, with: IDENT, ratio: <scalar>)` | §9 #35 | `substitute(smoothie(servings: 2), milk, with: oat_milk, ratio: 1.0)` |
| List literal | §1 | `[200 g, 500 g]` |
| Parenthesized expression | §3, §5 | `(1 + 2)` |

---
---

# PART 2 — Cheat-Sheet Material (for your 3 A4 sheets)

What follows is **everything you might need on paper**, organized into
three sheets. Each sheet is sized for a tight handwritten A4. Skip
the lines you've already memorised; copy what you tend to forget.

---

## ⚠️ READ THIS FIRST — what actually fits on 3 sides of A4

Single-side handwritten A4 fits **~30-35 lines** of dense text. Three
sides = **~90 lines total**. The expanded "Sheet 1 / 2 / 3" sections
below are REFERENCE material for study — **way too much** to fit on
paper. Use them to *understand* the content; then transcribe only the
**compact version below** onto your three sheets.

---

## ⚡ COMPACT VERSION — the actual cheat sheet (3 × A4, one side each)

### COMPACT SHEET 1 (one A4 side) — Reference card

```
PRECEDENCE LADDER (high → low, associativity right column)
  1  -x  !x  quantity_of(...)             RIGHT
  2  *  /                                  LEFT
  3  +  -                                  LEFT
  4  < <= > >=                             NON-ASSOC = parse error
  5  == !=                                 NON-ASSOC = parse error
  6  &&                                    LEFT short-circuit
  7  ||                                    LEFT short-circuit

TOP DECISIONS — WHAT it is | WHY chosen (the trade-off / Sebesta hook)
  #4  Pinch own primitive       | avoids per-op carve-outs in Quantity<D>
  #7  Quantity = 2 tokens        | unambiguous lex; allows /*comments*/ between
  #10 Equiv split (struct/name)  | data shape (Q/I/L) vs identity (Recipe)
  #11 Static lexical scoping     | compile-time refs; #28 + q_of need it
  #12 No shadowing               | catches bugs at compile time (#6 error)
  #13 Single-assignment          | immutability → referential transparency
  #16 Param semantic by-value    | no mutation in v1 → §9.5 modes collapse
  #17 Cmp non-associative        | parse-time catch beats runtime type err
  #18 L→R operand eval, locked   | predictable line numbers in error msgs
  #19 && || short-circuit L→R    | user expectation + safety (skip /0 etc)
  #20 Mandatory if/else braces   | eliminates dangling-else by construction
  #25 scale/sub functional       | ref-transparency: fresh value, no mutation
  #27 Assignment is statement    | every expression ref-transparent in v1
  #29 Verbs are hetero exception | decision-#29 carve-out to homogeneous rule
  #31 Implicit Ing → Q project   | ergonomic step bodies; no q_of() noise
  #34 quantity_of = unary op     | return type depends on operand's dim
  #35 sub slots = bare IDENT     | identity = binding (#28) visible in grammar

SEBESTA §-MAP
  §3.5  semantics: operational/denotational/axiomatic
  §5.5  static (lexical) scoping
  §6.2  primitives defined by operations
  §6.12 strong typing
  §6.14 name vs structural equivalence
  §7.2  precedence + associativity
  §7.4  coercion (narrowing = dangerous)
  §7.5  short-circuit evaluation
  §7.6  operand order + assignment
  §9.5  param modes collapse w/o mutation
```

### COMPACT SHEET 2 (one A4 side) — Mechanics & Errors

```
scale(r, by: k)   WHY: "doubling a recipe doubles the work, not just header"
  <r,S> → RtRecipe(n, ings, step_decls, cap_params)
  <k,S> → k > 0 else RuntimeError
  n' = int(round(n*k))                    banker's rounding
  ings': Mass/Vol/Count *= k
         Temp/Dur/Pinch unchanged
  S_scaled: servings → n', ings rebound to scaled
  step bodies RE-EXECUTED under S_scaled
  return FRESH RtRecipe (#25, no mutation)

substitute(r, x, with: y, ratio: k)   WHY: identity = binding (#28); no `this`
  x, y are bare IDENT (#35)
  new_q = orig.q * k
  new_ings[x] = (label=y, new_q)
  if y ≠ x: POP standalone y     (consumed)
  return FRESH RtRecipe

foreach x in L { body }   WHY: intrinsically bounded; no mutation needed
  <L,S> → RtList(elems, T); x typed T
  ∀ i: S_i' = S_i[x→elems[i]]
       <body, S_i'> → S_{i+1}''
       S_{i+1} = S_{i+1}'' \ {x}
  list evaluated ONCE upfront (#18)

19 §10 ERRORS   WHY: every error has one code; messages format identically
 1 dim mismatch    2 Pinch arith    3 hetero list
 4 unknown id      5 redecl         6 shadow
 7 if non-bool     8 rep non-int    9 foreach non-list
10 at non-Temp    11 for non-Dur   12 wrong arity
13 wrong types   14 sub unknown   15 float→int
16 Pinch↔Q sub   17 sub non-IDENT 18 q_of non-Ingr
19 ret not last  (#19 added by us, not original spec)

PHASE BOUNDARIES   WHY: catch errors at earliest possible phase
  lex   → bad char, "200g" no space
  parse → grammar (a<b<c, brace, sub-expr)
  type  → errors #1–#19
  runtime → div 0, neg repeat, scale.by ≤ 0,
            ambiguous-call leak (loud raise)
```

### COMPACT SHEET 3 (one A4 side) — Vocab, Defenses, Gotchas

```
COERCION TABLE   WHY: narrowing = silent data loss (Sebesta §7.4 danger)
  int → float           OK     widening; every int ≤ 2^53 exact in float
  unit ↔ unit (same D)  OK     representation-only; dim preserved
  Ingredient<D> → D     OK     projection #31; step-body ergonomics
  float → int           ERR    #15 narrowing; silent truncation = danger
  cross-dimension       ERR    #1 the DSL's reason to exist
  any with Pinch        ERR    #2 ceremonial — no arithmetic allowed

EQUIVALENCE SPLIT (Sebesta §6.14, dec #10)   WHY: shape vs identity records
  Quantity / Ingredient / List → STRUCTURAL    data shape carries meaning
  Recipe                       → NAME          identity: pancakes ≠ crepes

5 KEY SEBESTA DEFINITIONS   (def | Recipix use)
  STRONG TYPING (§6.12)      type errors always detected
    | Recipix yes; 2 named v1 gaps (neg qty, empty list)
  COERCION (§7.4)            implicit type conversion;
    NARROWING loses info, WIDENING preserves
    | Recipix: int→float OK; float→int FORBIDDEN
  REF TRANSPARENCY            same expr → same value, always
    | Recipix v1: guaranteed by #16 + #25 + #27 together
  STATIC SCOPING (§5.5)       lookup by lexical text;
    refs resolved at compile time
    | Recipix #11; Environment walks parent-pointer chain
  SHORT-CIRCUIT (§7.5)        skip 2nd operand if 1st decides
    | Recipix && and || L→R (#19); safety for /0 guards

DEFENSE TEMPLATE (use for any "defend decision X")
  1. State decision # + one-line claim
  2. Cite Sebesta §
  3. State what spec/code actually does
  4. State alternative NOT chosen
  5. State trade-off ACCEPTED (cost for benefit)

DSL ONE-LINER (memorise verbatim)
  "Dimensional type discipline. A general-purpose language treats
  200 and 500 as raw numbers. Recipix lifts dimensional structure
  into the type system — adding g to ml is a compile-time error.
  evaluate, scale, substitute exist to preserve this invariant."

GOTCHA ANSWERS (pre-loaded)
  • pour(flour:Mass) OK: 3-class collapse honors #29 carve-out;
    single-arg trivially satisfies homogeneity; v2 refinement.
  • Sample 1 = 6 cycles (not 4): scale re-executes step bodies
    under S_scaled where servings=n' (D1 §4.4).
  • Negative quantity: v1 scoped-out exception in D1 §4.5;
    sign discipline doubles lattice; D5 v2 candidate.
  • Sample 3 trace: "type error at line 13, col 0: dimension
    mismatch: cannot + Mass and Volume" (spec #1).
```

---

## 📚 REFERENCE DETAIL (below) — for understanding, do NOT transcribe

Everything from this point through the end of Part 2 is **expanded
reference material** for study. Read it to understand the content;
**copy only the compact version above** onto your three A4 sheets.

---

## SHEET 1 — Language & Decisions Reference

### 1.1 Sebesta chapter quick-map (memorise: number → topic → Recipix)

```
§1.3   Eval criteria: readability / writability / reliability / cost
        Recipix order: RELIABILITY > writability > readability >> cost
§1.4   Categories: imperative + functional flavor (ref-transparent v1)
§3.1   BNF/EBNF: {}, [], |, "literal", <nonterm>, UPPERCASE_TOKEN
§3.5   Semantics: operational / denotational / axiomatic
        Recipix uses big-step OPERATIONAL (D1 §4.4)
§4.4   Recursive descent: 1 function per nonterminal
        Recipix: _parse_or → _and → _eq → _rel → _add → _mul → _unary → _primary
§5.2   Identifier rules: [a-zA-Z_][a-zA-Z0-9_]*, ASCII, case-sensitive
§5.3   Binding times: language design / compile / run
§5.4   Lifetime: static / stack-dynamic / heap-dynamic
        Recipix: recipe+fn STATIC; everything else STACK-DYNAMIC
§5.5   STATIC (lexical) scoping vs dynamic
        Recipix decision #11: static; lookup walks parent chain
§6.2   Primitive types defined by OPERATIONS, not storage
§6.5   Lists: element type, index, static/dynamic, subscript-check
§6.7   Records: structural component
§6.12  STRONG typing: every type error detected
        Recipix: yes (2 v1 exceptions: neg quantities, empty list)
§6.13  Compile-time (static) type checking
§6.14  Type equivalence: NAME vs STRUCTURAL
        Recipix #10: split — struct for Q/I/L, name for Recipe
§7.2   Precedence + associativity table
§7.4   Coercion: widening (safe) vs narrowing (dangerous)
§7.5   Short-circuit: && and || skip 2nd if 1st determines result
§7.6   Operand evaluation order
        Recipix #18: L-to-R FULLY DEFINED
§7.6   Assignment: statement OR expression
        Recipix #27: STATEMENT only (let)
§9.5   Param passing: by-value / by-ref / by-result / by-value-result
        Recipix #16: collapses to by-value (no mutation in v1)
```

### 1.2 Full 7-level precedence ladder (with associativity)

```
LEVEL  OPERATORS                               ASSOCIATIVITY
  1    unary - , !, quantity_of(...)           RIGHT
  2    *  /                                    LEFT
  3    +  -  (binary)                          LEFT
  4    <  <=  >  >=                            NON-ASSOC (parse error)
  5    ==  !=                                  NON-ASSOC (parse error)
  6    &&                                      LEFT (short-circuit)
  7    ||                                      LEFT (short-circuit)

Higher LEVEL = tighter binding.
1 + 2 * 3   parses as 1 + (2 * 3)            (level 2 tighter than 3)
-quantity_of(flour) * 2  parses as (-(quantity_of(flour))) * 2
1 kg < flour < 2 kg      => PARSE ERROR     (non-assoc level 4)
flour < salt == cinnamon => PARSE ERROR     (mixed non-assoc 4 & 5)
```

### 1.3 Top-15 decisions (number + one-liner — must know cold)

```
#1   3 primitive types: int / float / bool
#3   5 quantity dimensions: Mass / Volume / Count / Temperature / Duration
#4   Pinch is its OWN primitive (not Quantity<Pinch>) — no arithmetic
#5   Structured types: Ingredient / Recipe / Step / List<T>
#6   Lists are HOMOGENEOUS (all elements same type)
#7   Quantity literals = TWO tokens (NUMBER + UNIT)
        invalid: 200g  valid: 200 g  also valid: 200 /* note */ g
#8   STRONG typing (yes)
#9   Coercion: within-dim unit + int→float widening; NEVER float→int
#10  Equivalence SPLIT: struct for Quantity/Ingredient/List; NAME for Recipe
#11  STATIC (lexical) scoping
#12  Shadowing FORBIDDEN (compile-time error #6)
#13  SINGLE-ASSIGNMENT (let names immutable in their scope)
#15  Parameterized recipes (primary abstraction) + scalar functions (helpers)
#16  Parameter passing: SEMANTICALLY BY-VALUE (no mutation in v1)
#17  Comparison NON-ASSOCIATIVE (no chaining)
#18  Operand eval: L-to-R FULLY DEFINED
#19  Short-circuit && and || left-to-right
#20  Mandatory braces on if/else (no dangling-else)
#21  Loops: repeat <int> times { } and foreach <id> in <list> { }
#23  Step modifiers: [at <expr>] [for <expr>] in FIXED order
#25  scale/substitute FUNCTIONAL: fresh value, no mutation, no `this`
#26  No recipe composition (removed from v1)
#27  Assignment is a STATEMENT, not an expression
#28  Ingredient identity = the BINDING (not the name field)
#29  Action verbs are an EXCEPTION to homogeneous-list rule
#30  No expr-then-unit: use <expr> * 1 <unit> to build from computed value
#31  Implicit Ingredient → Quantity projection in arith/cmp/sub context
#32  Closed type-name set; NO List<T> annotation in user source
#34  quantity_of is a UNARY OPERATOR, not a function
#35  substitute slots are BARE IDENT terminals (not <expr>)
```

### 1.4 Coercion rules (§7.4)

```
ALLOWED implicitly:
  int + float       → float    (widening, info-preserving, dec #9)
  200 g + 1 kg      → 1200 g   (within-dim unit, representation-only)
  Ingredient<D>     → D        (projection in arith ctx, dec #31)

FORBIDDEN implicitly (must be explicit):
  float → int       NEVER       (narrowing; reserved for v2 to_int())
  Mass  → Volume    NEVER       (cross-dim)
  Pinch → anything  NEVER       (ceremonial discipline)

QUANTITY ARITHMETIC TABLE:
  mass + mass (same dim)        OK, with unit conversion
  mass + volume                  ERROR #1 (dimension mismatch)
  quantity * scalar              OK (dim preserved): 200 g * 2 = 400 g
  scalar * quantity              OK (commutative)
  quantity * quantity            ERROR #1 (no dim products v1)
  quantity / scalar              OK (dim preserved)
  quantity / quantity (same dim) OK → UNITLESS scalar: 1 kg / 200 g = 5
  quantity / quantity (diff dim) ERROR #1
  unary -quantity                OK syntactically (interpreter accepts;
                                 checker doesn't flag neg in v1 — gap)
  any op involving Pinch         ERROR #2
```

### 1.5 Type equivalence split (#10, Sebesta §6.14)

```
TYPE             RULE                                    DOMAIN MEANING
Quantity<D>      STRUCTURAL                              data shape
Ingredient       STRUCTURAL                              data shape (2-field record)
List<T>          STRUCTURAL in parameter, NAME in ctor   parametric type
Recipe           NAME                                    identity (pancakes ≠ crepes)
Step             — (not user-visible in v1; defaults to structural)
Pinch            PRIMITIVE                               separate carve-out
```

### 1.6 Unit conversion factors (D1 §3, runtime_values.py UNIT_TABLE)

```
DIMENSION    BASE UNIT   OTHER UNITS
Mass         g           1 kg = 1000 g; 1 mg = 0.001 g
Volume       ml          1 l = 1000 ml; 1 tsp = 5 ml;
                         1 tbsp = 15 ml; 1 cup = 240 ml
Count        count       (no conversions)
Temperature  °C          (no conversions)
Duration     min         1 hr = 60 min
Pinch        —           (singleton, no conversion)
```

---

## SHEET 2 — Mechanics & Algorithms (walk-through ready)

### 2.1 `scale(r, by: k)` — full operational semantics

```
RULE (big-step):
  <r, S> → RtRecipe(name, n, ingredients, step_decls, captured_params, …)
  <k, S> → k : (int | float)
  k > 0                                              ← else RuntimeRecipixError
  n' = int(round(n * k))                             ← banker's rounding
  ingredients' = scale_each(ingredients, k)
  S_scaled = globals.child()
    for (p, v) in captured_params:
      S_scaled[p] = n' if v was original servings, else v
    for (id, ing') in ingredients':
      S_scaled[id] = ing'
  steps' = [exec_step(sd, S_scaled.child()) for sd in step_decls]
  ───────────────────────────────────────────────
  <scale(r, by: k), S> → fresh RtRecipe(name, n', ingredients', steps', …)

scale_each(ing, k):
  if ing.q.dim in {Mass, Volume, Count}:
    RtIngredient(ing.name, RtQuantity(ing.q.value * k, ing.q.dim))
  if ing.q.dim in {Temperature, Duration} or ing.q is RtPinch:
    ing                                              ← unchanged
```

### 2.2 `substitute(r, x, with: y, ratio: k)` — full

```
RULE:
  <r, S> → RtRecipe(name, n, ingredients, …)
  k > 0
  x, y must be IDENT (decision #35); look up in recipe.ingredient_types
  orig = ingredients[x]; repl = ingredients[y]
  orig.q.dim == repl.q.dim                           ← else error #1
  not (orig.q is Pinch XOR repl.q is Pinch)         ← else error #16
  new_q = RtQuantity(orig.q.value * k, orig.q.dim)
  new_ings = ingredients with x → RtIngredient(y, new_q)
  if y != x: new_ings.pop(y)                        ← consume replacement
  ───────────────────────────────────────────────
  <substitute(r, x, with: y, ratio: k), S> → fresh RtRecipe(…, new_ings, …)
```

### 2.3 `foreach x in <list> { body }` — big-step

```
RULE:
  <list_expr, S> → RtList(elems, T)
  S_0 = S
  ∀ i ∈ [0, |elems|):
    S_i' = S_i[x ↦ elems[i]]               ← bind in fresh scope
    <body, S_i'> → S_{i+1}''
    S_{i+1} = S_{i+1}'' \ {x}              ← x out of scope
  ───────────────────────────────────────────
  <foreach x in list_expr { body }, S> → S_{|elems|}

NOTES:
  • list evaluated ONCE before iteration (decision #18)
  • x typed as T inferred at list construction
  • x cannot shadow (checker enforces #12 at compile time)
  • empty list → zero iterations, no error
```

### 2.4 Implicit Ingredient → Quantity projection (#31)

```
HELPER:
  _dimension_of(t):
    if t in {Mass, Volume, Count, Temperature, Duration}: return t
    if t.startswith("Ingredient:") and not endswith(":Pinch"):
      return t[len("Ingredient:"):]
    return None

APPLIES IN:
  • BinaryOp (arithmetic):    flour + 100 g
  • CompareOp:                flour > 100 g
  • SubstituteCall (impl):    inside ratio handling
  • action-verb dispatch (homogeneous class)

EQUIVALENT EXPLICIT:
  flour + 100 g  ≡  quantity_of(flour) + 100 g
```

### 2.5 AmbiguousCall resolution (plan §2.1 + §3)

```
PARSER:
  flip()      → AmbiguousCall(name="flip")
  half(4)     → FunctionCall(name="half", args=[IntLit(4)])
  pancakes(servings: 4) → RecipeCall(name="pancakes", kwargs=[…])

TYPECHECKER._rewrite_ambiguous walks AST:
  if name in functions: → FunctionCall(name, args=[], line=…)
  if name in recipes:   → RecipeCall(name, kwargs=[], line=…)
  else: leave           → later raises error #4 (unknown identifier)

INTERPRETER._eval_AmbiguousCall:
  raise RuntimeRecipixError("internal error: AmbiguousCall reached
        interpreter; type checker did not run")
  ← LOUD FAIL: prevents silent failures when typechecker is skipped
```

### 2.6 Sample 1 — full trace

```
SRC:  evaluate scale(pancakes(servings: 4), by: 1.5)

STEP A: pancakes(servings: 4) — recipe instantiation
  env = {servings: 4}
  ingredients evaluated:
    flour: 50 g * 4 = 200 g
    milk : 60 ml * 4 = 240 ml
    eggs : half(4) * 1 count = 2 count
    salt : 1 pinch
  step bodies eager-evaluated:
    step 1 "Mix dry"  → actions = [combine(flour, salt)]
    step 2 "Add wet"  → actions = [combine(milk, eggs)]
    step 3 "Cook batches" at 180°C for 3 min
      repeat 4 times { pour(milk); flip() }
      → actions = [pour, flip, pour, flip, pour, flip, pour, flip]  (4 cycles)
  RtRecipe(name="pancakes", servings=4, ingredients={…},
           steps=[…], step_decls=[…], captured_params={servings:4})

STEP B: scale(prev, by: 1.5) — re-execution
  n' = int(round(4 * 1.5)) = 6
  scaled ingredients:
    flour: 200*1.5 = 300 g
    milk : 240*1.5 = 360 ml
    eggs : 2*1.5 = 3 count
    salt : 1 pinch  (UNCHANGED — Pinch)
  S_scaled = {servings: 6, flour:300g, milk:360ml, eggs:3, salt:pinch}
  step bodies RE-EXECUTED:
    step 1 → combine(flour, salt)
    step 2 → combine(milk, eggs)
    step 3 → repeat 6 times { pour(milk); flip() }
         → 6 pour/flip cycles = 12 action lines
  Fresh RtRecipe — old one never mutated

STEP C: evaluate → render_recipe → cookbook output
```

### 2.7 Sample 2 — substitute mechanics

```
SRC:  evaluate substitute(smoothie(servings: 2), milk, with: oat_milk, ratio: 1.0)
       evaluate smoothie(servings: 2)

EVAL 1 (vegan): substitute
  smoothie(servings: 2) instantiates with:
    milk : 300 ml, banana: 2, sweetener: 20 g, oat_milk: 300 ml
  substitute looks up x="milk", y="oat_milk" in ingredient_types
  new_quantity = 300 ml * 1.0 = 300 ml
  new_ingredients = {milk: oat_milk@300ml,            ← slot relabeled
                     banana: 2,
                     sweetener: 20 g}
                     # oat_milk standalone POPPED (#consumed)
  Output: oat_milk 300 ml, banana 2, sweetener 20 g

EVAL 2 (non-vegan): no substitute
  Plain smoothie instantiation
  Output: milk 300 ml, banana 2, sweetener 20 g, oat_milk 300 ml
                                                  ↑ stays because pre-declared
                                                  ↑ for substitute call site
                                                  ↑ (#28 no-this design)
```

### 2.7b Sample 3 — type-error trace (the headline DSL demo)

```
SRC:  recipe broken() serves 1 {
        ingredient flour : 200 g
        ingredient water : 100 ml
        step "Combine wet and dry" {
          let total : Mass = flour + water    ← LINE 13, COL 0 of +
        }
      }
      evaluate broken()

LEX:    no error (200 g, 100 ml are well-formed quantity literals)
PARSE:  no error (let stmt is syntactically valid)
TYPECHECK in enclosing recipe scope:
  flour → "Ingredient:Mass"
  water → "Ingredient:Volume"
  _check_LetStmt(node):
    annotation = "Mass"
    expr = BinaryOp(+, Identifier(flour), Identifier(water))
    _check_BinaryOp:
      lt = "Ingredient:Mass"  → _dimension_of() → "Mass"
      rt = "Ingredient:Volume"→ _dimension_of() → "Volume"
      both non-None → _check_quantity_binop(+, "Mass", "Volume")
      "Mass" != "Volume" → raise TypeCheckError(error_code=1)
  ───────────────────────────────────────────────────────────────
OUTPUT:  exit 1
  type error at line 13, col 0: dimension mismatch: cannot + Mass and Volume

→ Caught at COMPILE time. Interpreter NEVER runs sample 3.
→ This is the headline-claim demonstration for spec §1's
  "dimensional type discipline."
→ Implicit Ingredient → Quantity projection (#31) is what turns
  flour from Ingredient<Mass> into a Mass value before the + runs.
```

### 2.8 The 19 spec §10 compile-time errors

```
#1   dim mismatch in arith/cmp/substitute
#2   Pinch in arith/cmp/scaling
#3   heterogeneous list literal
#4   unknown identifier
#5   single-assignment violation (re-declare in same scope)
#6   shadowing (re-declare visible from any ancestor)
#7   non-bool in if condition
#8   non-int in repeat count
#9   non-list in foreach source
#10  non-Temperature in step at modifier
#11  non-Duration in step for modifier
#12  wrong arity in recipe/function call
#13  wrong arg types (incl. action verbs)
#14  substitute of unknown ingredient
#15  float → int coercion attempt
#16  substitute swaps Pinch ↔ Quantity
#17  non-IDENT in substitute slot (parser catches)
#18  quantity_of on non-Ingredient
#19  return not as last stmt of function body (plan §2.6, added by us)

RUNTIME ERRORS (5):
  negative repeat count
  negative or zero scale.by
  substitute of unknown ingredient (rare; usually caught by #14)
  division by zero in scalar arithmetic
  Pinch in arithmetic context at runtime (rare; usually caught by #2)
```

### 2.9 Phase boundaries — which errors fire where

```
PHASE         ERROR CLASS                      EXAMPLES
Lexer         bad char / bad number-unit form  "200g" (no space, #7);
                                               '@' (unknown char);
                                               unterminated "...
Parser        grammar violations               "a < b < c" (#17 non-assoc);
                                               "if x return" no brace (#20);
                                               "substitute(r, f+s, ...)" (#35);
                                               "for ... at ..." reversed (#23);
                                               "200 + g" expr between (#7)
Type checker  §10 errors #1–#19                #1 dim mismatch (sample 3);
                                               #2 Pinch in arith;
                                               #4 unknown identifier;
                                               #6 shadowing;
                                               #12/#13 wrong arity/types;
                                               #15 float→int coercion;
                                               #18 quantity_of non-Ingr;
                                               #19 return not last
Interpreter   runtime errors                   division by 0;
                                               negative repeat count;
                                               scale.by ≤ 0;
                                               substitute unknown ingr (rare);
                                               AmbiguousCall reaches interp
                                               (loud internal-error guard)

ERROR MESSAGE FORMAT (consistent across phases):
  parse error at line L, col C: <message>
  type error at line L, col C: <message>
  runtime error at line L: <message>           (no col — runtime is stmt-level)
```

### 2.10 Action-verb three-class table (plan §2.3)

```
CLASS          VERBS                              RULE
Heterogeneous  combine, mix, add, sprinkle        ≥1 arg; Ingredient/Quantity
                                                   any dim including Pinch;
                                                   mixed dims OK (#29 carve-out)
Homogeneous    pour, drizzle, whisk, blend,       ≥1 arg; all args share ONE dim;
               knead, melt                         Pinch FORBIDDEN; projection #31
Nullary        bake, flip                          0 args (params via step modifiers)
```

---

## SHEET 3 — Defenses, Vocabulary & Quick-Recall

### 3.1 §4.8 rationale defenses (compressed for the exam)

```
NON-ASSOC COMPARISON (#17, §7.2):
  Left-assoc: 1kg < flour < 2kg → (1kg<flour)<2kg → bool<2kg → RUNTIME error
  Non-assoc:  PARSE ERROR (earliest phase, clearest message)
  Trade-off: users write (1kg < flour) && (flour < 2kg) — small writability cost
  Reliability > writability, consistent with §1.3 priorities

SHORT-CIRCUIT (#19, §7.5):
  Standard programmer expectation; matches operand order (#18)
  One mental model for both; eager would force nested if for null-checks
  Safety bonus: x != 0 && y/x > 1  ← y/x skipped when x=0

OPERAND ORDER L-TO-R (#18, §7.6):
  C/C++ "unspecified" → compiler reorders → cross-platform different errors
  Recipix: locked L-to-R; reliability > optimization (#1 already deprioritizes)
  Unobservable on VALUES (no side effects: #27 + #16)
  Observable in ERROR REPORTING: predictable line numbers

ASSIGNMENT AS STATEMENT (#27, §7.6):
  Only binding: let <name>:<type> = <expr>
  Every expression referentially transparent
  Decision #18 L-to-R unobservable (no operand can mutate)
  Operational semantics §4.4 simplified
  v2 mutation → revisit #27 FIRST

PINCH PRIMITIVE (#4, §6.2):
  Quantity<Pinch> would need carve-outs in every operator
  Separate primitive: carve-out in checker per-op entries only
  §6.2: primitives defined by operations supported, not storage
  Pinch supports ceremonial operations only — keeps language honest

EQUIVALENCE SPLIT (#10, §6.14):
  Data shape → STRUCTURAL (Ingredient/List/Quantity)
  Identity   → NAME      (Recipe — pancakes ≠ crepes)
  v1's closed type-name set forecloses hypothetical collision concerns

QUANTITY_OF AT UNARY (#34, §7.2):
  Return type DEPENDS on operand type: Ingredient<D> → D
  No FunctionType signature can express this dependency
  Unary production: cannot be shadowed, assigned, or passed as value

SCALE / SUBSTITUTE FUNCTIONAL (#25):
  Fresh RtRecipe value; original never mutated
  Referential transparency preserved
  No `this`: alternatives pre-declared inside recipe (#28 binding identity)

THREE-CLASS VERB COLLAPSE (plan §2.3):
  12 per-verb signatures → 12 checker branches + 24 tests + memorization tax
  Three classes honor decision #29 carve-out + projection #31
  Trade-off: pour(flour:Mass) type-checks (English-language verb semantics lost)
  v2 can add per-verb dimensions to homogeneous class — backwards-compatible

NO `while` LOOP (design choice):
  repeat and foreach are INTRINSICALLY BOUNDED (header gives the bound)
  while needs side effects (counter increment / accumulator update)
       → contradicts #16 (no mutation) and #27 (assignment-as-statement)
  Termination provable from the loop header alone — no infinite-loop bugs
  v2 mutation → while becomes meaningful again

EVALUATE-ONLY CONSTRAINT on scale/substitute (spec §9):
  Can only appear inside expressions rooted at an `evaluate` statement
  Reason 1: no `this` (#25 corollary) — a recipe can't reference itself
            during construction; scale/substitute only operate on
            already-instantiated recipe values
  Reason 2: ref-transparency boundary — recipe definitions stay pure;
            evaluate is where pure value construction meets rendering

ERROR #19 SINGLE-RETURN (plan §2.6 — added by us, not in original spec):
  Spec §7: "Single return at end of body. No early return in v1."
  Parser ALLOWS `return` anywhere (it's a semantic, not grammatical, rule)
  Without a checker rule: `if x { return 1 } return 2` silently accepted
  Our error #19: checker scans `body[-1]` is ReturnStmt, recursively
                 walks IfStmt/RepeatStmt/ForeachStmt for stray Returns
  Code: _check_single_return + _no_return_in (typechecker.py)

BANKER'S ROUNDING (plan §2.6 — for scale servings):
  scale(recipe-of-3, by: 0.5):
    truncation int(1.5)         = 1  → 33% serving loss
    ceiling    ceil(1.5)        = 2  → over-orders ingredients
    banker's   int(round(1.5))  = 2  → unbiased on halves
  Statistically unbiased (round-half-to-even);
  pinned by tests; documented in plan §2.6 and D1 §4.4
```

### 3.2 Sebesta vocabulary cheat sheet

```
TERM (§)                   ONE-LINE DEFINITION                  RECIPIX INSTANCE
Strong typing (§6.12)      Type errors always detected          Yes (2 named gaps)
Coercion (§7.4)            Implicit type conversion             Within-dim + int→float only
Widening coercion (§7.4)   Info-preserving direction            int → float
Narrowing coercion (§7.4)  Info-losing direction (dangerous)    float→int explicitly forbidden
Structural equiv. (§6.14)  Same field shape = same type         Quantity / Ingredient / List
Name equivalence (§6.14)   Same declaration name = same type    Recipe
Static scoping (§5.5)      Lookup by lexical structure          Yes, decision #11
Dynamic scoping (§5.5)     Lookup through call stack            NOT used
Stack-dynamic (§5.4)       Lifetime = activation lifetime       Most local bindings
Heap-dynamic (§5.4)        Lifetime = explicit allocation       NONE in v1
Referential transparency   Same expr = same value, always       Recipix v1 YES
Side-effect free           No mutation observable               #16+#25+#27 together
Short-circuit (§7.5)       Skip 2nd operand if 1st decides      && and || L-to-R
Pass-by-value (§9.5)       Caller copy unmodifiable             All params (no mutation)
Pass-by-reference (§9.5)   Callee can modify caller's value     Used internally as opt only
                                                                (unobservable in v1)
Operational sem (§3.5)     Abstract-machine transition rules    Big-step for scale, foreach
Denotational sem (§3.5)    Map to mathematical functions        NOT used
Axiomatic sem (§3.5)       Pre/postconditions (Hoare logic)     NOT used (handout forbids)
Type checking (§6.13)      Verify ops on compatible operands    Compile-time
Single-assignment          Names bound once, immutable          Decision #13
Lexical scope              Same as static                       Decision #11
Symbol table               Name → (type, scope) map             Environment class
Activation record          Stack frame for function call        Implicit in tree-walking
```

### 3.2b Sebesta-flavored definitions (for cold "explain term X" Qs)

```
STRONG TYPING (§6.12):
  "A language is strongly typed if type errors are always detected.
  Requires the types of all operands to be determined, either at
  compile time or at run time."
  → Recipix is strongly typed at compile time, except 2 named v1
    exceptions (negative quantities, empty-list type inference).

COERCION (§7.4):
  "An implicit type conversion. A NARROWING coercion converts a
  value to a type that cannot include all of the values of the
  original type (e.g. double to float, float to int). A WIDENING
  coercion converts to a type that can include at least
  approximations of all original values (e.g. int to float)."
  → Recipix: int → float widening allowed; float → int narrowing
    NEVER implicit (silent fractional loss is the danger Sebesta names).

REFERENTIAL TRANSPARENCY:
  "A program has the property of referential transparency if any
  two expressions in the program that have the same value can be
  substituted for one another anywhere in the program, without
  affecting the action of the program."
  → Recipix v1: yes, guaranteed by #16 (no mutation) + #25 (functional
    domain ops) + #27 (assignment is a statement).

STATIC (LEXICAL) SCOPING (§5.5):
  "The scope of a variable is determined by the textual structure of
  the program. References can be resolved at compile time."
  → Recipix: yes, decision #11. Lookup walks parent-pointer chain
    in Environment class. Each block opens a fresh scope.

DYNAMIC SCOPING (§5.5):
  "The scope of a variable depends on the calling sequence; resolution
  walks the run-time call stack, not the lexical text."
  → NOT used in Recipix. Would break decision #28 (substitute
    binding lookup) and the type rule for quantity_of.

SHORT-CIRCUIT EVALUATION (§7.5):
  "An evaluation of an expression in which the result is determined
  without evaluating all of the operands and/or operators."
  → Recipix: && and || short-circuit left-to-right.

OPERATIONAL SEMANTICS (§3.5):
  "Describes the meaning of a program by specifying how it executes
  on a real or hypothetical machine."
  → BIG-STEP (a.k.a. natural semantics): rules of the form
    <expr, S> → value or <stmt, S> → S'.
  → Recipix D1 §4.4 uses big-step for scale and foreach.

DENOTATIONAL SEMANTICS (§3.5):
  "Maps each language construct to a mathematical object (typically
  a function) that denotes its meaning."
  → NOT used in Recipix.

AXIOMATIC SEMANTICS (§3.5):
  "Uses preconditions and postconditions (Hoare logic) to describe
  meaning in terms of what's true before and after each statement."
  → NOT used in Recipix; handout explicitly forbids this style for
    the project.

NAME EQUIVALENCE (§6.14):
  "Two variables have equivalent types if their type definitions
  appear in the same declaration or in declarations that use the
  same type name."
  → Recipix: Recipe only.

STRUCTURAL EQUIVALENCE (§6.14):
  "Two variables have equivalent types if their types have identical
  structures."
  → Recipix: Quantity<D>, Ingredient, List<T>.

STACK-DYNAMIC LIFETIME (§5.4):
  "Variables whose storage bindings are created when their
  declaration statements are elaborated, but whose types are
  statically bound."
  → Recipix: most local bindings (params, let, ingredients, foreach
    loop vars). Recipe/function declarations are STATIC lifetime.

PASS-BY-VALUE (§9.5):
  "The value of the actual parameter is used to initialize the
  corresponding formal parameter. Acts as a local variable in the
  subprogram; modifications do not affect the actual parameter."
  → Recipix v1: collapses to this mode because no mutation exists.
    By-value/by-reference/by-result/by-value-result are observationally
    indistinguishable.
```

### 3.3 Binding-times table (§5.3)

```
BINDING                                    COMPILE TIME   RUN TIME
Recipe declarations (name, signature)      ✓              —
Function declarations (name, signature)    ✓              —
Ingredient TYPES (the dimension)           ✓              —
Ingredient quantity VALUES                 —              ✓ (at instantiation)
Recipe parameters                          —              ✓ (at instantiation)
Function parameters                        —              ✓ (at call)
foreach loop variable TYPE                 ✓              —
foreach loop variable VALUE                —              ✓ (per iteration)
let-bound TYPE (required annotation)       ✓              —
let-bound VALUE                            —              ✓
```

### 3.4 Token-category reference (§4.2 of D1)

```
CATEGORY               EXAMPLES                                            CONST
Identifier             flour, oat_milk                                     IDENT
Integer literal        200, 0, 42                                          INT_LIT
Float literal          1.5, 0.5                                            FLOAT_LIT
String literal         "Mix dry"                                           STRING_LIT
Boolean literal        true, false                                         BOOL_LIT
Reserved keyword       recipe, function, let, if, else, repeat, foreach,
                       evaluate, scale, substitute, ...                    (type = keyword text)
Type-name keyword      int, float, bool, Mass, Volume, ...                 TYPE_KW
Action-verb keyword    combine, mix, pour, ...                             ACTION_KW
Unit keyword           g, kg, ml, °C, min, pinch, ...                      UNIT_KW
Operator               + - * / == != < <= > >= && || ! =                   PLUS, EQ, ...
Separator              ( ) { } [ ] , : ->                                  LPAREN, ...
```

### 3.5 List design decisions (§6.5)

```
QUESTION                          RECIPIX ANSWER
Element type                      Homogeneous (decision #6)
Index range                       Not user-facing
Subscript check                   N/A (no indexing)
Static vs dynamic                 Type STATIC (inferred), length DYNAMIC
User-writable List<T> annotation  Forbidden in v1 (decision #32)
Empty list behavior               foreach → 0 iterations, no error
Element-type inference            At literal construction and foreach entry
```

### 3.6 The DSL one-liner (write this on EVERY answer that asks "why is Recipix a DSL")

```
"Dimensional type discipline. A general-purpose language treats 200
and 500 as raw numbers. Recipix lifts the dimensional structure into
the type system — adding grams to milliliters is a compile-time error.
The three domain-specific operations (evaluate, scale, substitute) and
the structured types (Recipe, Ingredient) all exist to preserve this
invariant."
```

### 3.7 Common-question quick-recall table

```
Q ASKED                                                ONE-LINE ANSWER
Why does sample 1 show 6 cycles instead of 4?         scale re-executes step
                                                       bodies under S_scaled
                                                       where servings=6 (D1 §4.4)
Why does sample 2 show 2 oat_milk lines (non-veg)?    no-this; oat_milk pre-
                                                       declared so substitute
                                                       can reference it (#28)
Why is pour(flour) accepted?                           three-class collapse:
                                                       single-arg trivially
                                                       homogeneous; v2 candidate
Why no negative-quantity check?                        v1 scope-out; sign
                                                       discipline doubles lattice;
                                                       v2 fix
Why use banker's rounding?                             unbiased on halves;
                                                       truncation halves cook,
                                                       ceiling over-orders
Why static scoping over dynamic?                       quantity_of and substitute
                                                       bare-IDENT both break under
                                                       dynamic
Why Pinch separate primitive?                          avoids per-op carve-outs
                                                       in Quantity<D>; §6.2 ops
                                                       framing
Why split equivalence rule?                            shape vs identity records
                                                       want different rules
Why assignment-as-statement?                           referential transparency;
                                                       no mutation in v1
What guarantees ref-transparency?                      #16 + #25 + #27 together
```

### 3.8 Exam-time process checklist

```
1. Read all questions FIRST. Note which want chapter cites, which want
   project-specific defenses, which want trace-throughs.
2. Budget ~9 min per question. Project-specific Qs are usually faster
   if you have the §2.x mechanics memorised.
3. ALWAYS name the Sebesta section AND the decision number in your
   answer. (E.g. "Per Sebesta §7.2 and Recipix decision #17, …")
4. For trace-through Qs (sample 1, 2, 3): walk the EXAM grader
   through your steps, don't just state the answer.
5. For defense Qs: state the choice, state the alternative, state the
   trade-off ACCEPTED. Three sentences minimum.
6. If you don't know: cite the closest decision number you DO know
   and reason from it. Partial credit > blank.
```

### 3.9 Fallback templates — for when you're stuck

```
UNKNOWN DECISION NUMBER:
  Scan §3.7 quick-recall table; cite the closest decision you know;
  reason from it. Better than blank.

UNKNOWN SEBESTA SECTION:
  Scan §1.1 chapter quick-map; cite the chapter even if not the §;
  partial credit > blank.

UNKNOWN PROGRAM TRACE:
  Cite the algorithm from sheet 2.x for the relevant operator;
  walk through with placeholder values; show your reasoning.

UNKNOWN DEFENSE — universal template:
  "Recipix locked [X]. The alternative would be [Y]. The trade-off
  accepted is [cost of X] in exchange for [benefit of X]. Sebesta
  §[N] frames this as [framework concept]."

ANSWER STRUCTURE for any 5-sentence project question:
  1. State the decision number + one-sentence claim.
  2. Cite the Sebesta § that frames it.
  3. State what the spec/code actually does (mechanics).
  4. State the alternative that was NOT chosen.
  5. State the trade-off accepted (cost in X for benefit in Y).

ANSWER STRUCTURE for any 5-sentence cold Sebesta question:
  1. State the Sebesta definition verbatim (§3.2b on Sheet 3).
  2. State which Recipix decision applies.
  3. Give the concrete Recipix instance from your code/spec.
  4. State one example program that illustrates it.
  5. State what would break in a v2 if the rule changed.
```

### 3.10 The four most likely "gotcha" questions (have answers ready)

```
GOTCHA 1: "Trace through sample 3's type-error message verbatim."
  → Use Sheet 2.7b — every line; cite error #1; end with the
    exact verbatim message:
    "type error at line 13, col 0: dimension mismatch: cannot + Mass and Volume"

GOTCHA 2: "Why does pour(flour : Mass) type-check?"
  → Three-class collapse (plan §2.3); single-arg homogeneous
    trivially satisfies the rule; English-language verb semantics
    deliberately sacrificed for type-system parsimony; v2 candidate
    for per-verb dimensions.

GOTCHA 3: "Your spec admits negative quantities — defend this."
  → v1 scope-out (D1 §4.5 exception (a)); adding sign discipline
    to dimensional type system would double the type lattice
    (Quantity<D, +> vs Quantity<D, ?>); judged too much work for
    v1; v2 fix candidate; named honestly in D5.

GOTCHA 4: "Why does sample 1 show 6 cycles instead of 4?"
  → scale's step-body re-execution rule (D1 §4.4, Sheet 2.1, 2.6);
    fresh env S_scaled with servings rebound to 6; step bodies
    re-evaluated; user-intuitive ("doubling the recipe doubles
    the work, not just the header"); ref-transparency preserved
    because fresh RtRecipe value is built.
```

---
---

# PART 3 — Practice Q&A (25 questions)

## Q1. Operand evaluation order — Sebesta §7.6

**Question.** Your decision #18 locks operand evaluation order to
"left-to-right, fully defined." Give a Recipix program where the
*choice* of order would change the observable result, and explain why
this is different from the canonical C example `i++ + i++`.

**Answer.** Recipix has no side-effecting expressions (no mutation
per #16, no assignment-as-expression per #27), so order is
**unobservable on values**. The one place it shows is **error
reporting**: `let x : int = f(a/0) + g(b/0)` raises division-by-zero
from `a/0` under L-to-R. The error message cites a specific line; if
order were "unspecified," different platforms could report different
lines, breaking reliability. C's `i++ + i++` doesn't exist in Recipix
because (a) there is no `++`, (b) `=` is not an expression — no
operand can mutate state another operand reads.

## Q2. Non-associative comparison — Sebesta §7.2, decision #17

**Question.** Your precedence table marks `<`, `<=`, `>`, `>=` and
`==`, `!=` as non-associative. Show what happens when a user writes
`1 kg < flour < 2 kg`. What error do they see, and when? Why did you
choose this over C-style left-associative?

**Answer.** The parser refuses `Additive ( CompOp Additive )?` — at
most one comparison per production. User sees a **parse error** at
the second `<`. Under C-style left-associativity, it would parse as
`(1 kg < flour) < 2 kg`, evaluate `1 kg < flour` to a `bool`, then
hit a **run-time type error** about comparing `bool` to `Mass`. The
non-associative choice catches the bug at the earliest possible
phase with the clearest error message. Trade-off accepted: users
chain explicitly with `(1 kg < flour) && (flour < 2 kg)`.

## Q3. `quantity_of` placement — Sebesta §7.2, decision #34

**Question.** Why is `quantity_of(x)` at the unary level rather than
treated as a function call at the primary level?

**Answer.** Its return type depends on the operand's type:
`quantity_of : Ingredient<D> → D`. A function-type signature can't
express the dependency on the operand's dimension field. A dedicated
unary production lets the type rule live in the operator dispatch,
not in a special-cased identifier. Side benefit: `quantity_of` lives
outside the value namespace — can't be shadowed by a `let`, can't be
passed as an argument, can't be assigned to a variable.

## Q4. Type equivalence split — Sebesta §6.14, decision #10

**Question.** Sebesta §6.14 typically frames equivalence as one rule
per language. Recipix uses a split — structural for
`Quantity<D>`/`Ingredient`/`List<T>`, name for `Recipe`. Defend the
split. What breaks if `Recipe` uses structural equivalence?

**Answer.** Records modeling **data shape** (Ingredient is a
transparent two-tuple, List is parametric, Quantity is dim-tagged)
want structural so two same-shaped values from different scopes
interoperate. Records modeling **identity** (Recipe) want name so
accidental shape collisions can't substitute one for another. Under
structural for Recipe, `pancakes` and `crepes` happening to share
`{flour, milk, eggs}` would both type-check as the same Recipe — and
`scale(pancakes_value, by: 2)` would silently substitute where
`crepes` was expected. Recipe identity carries program meaning; field
shape is a coincidence.

## Q5. Implicit Ingredient → Quantity projection — decision #31

**Question.** Inside a step body, `flour + 100 g` type-checks even
though `flour : Ingredient<Mass>` and `100 g : Mass`. Walk through
what the type checker does. Name one consequence (good or bad) of
the design choice.

**Answer.** `_check_BinaryOp` sees `+` between `Ingredient<Mass>` and
`Mass`. Helper `_dimension_of(t)` returns the dimension if `t` is
`Quantity<D>` or `Ingredient<D>` (excluding Pinch). Both return
`Mass`, dimensions match, result is `Mass`, BinaryOp node gets
`.inferred_type = "Mass"`. **Good consequence**: ergonomic step
bodies (`flour + 100 g` vs. `quantity_of(flour) + 100 g`). **Bad
consequence**: small loss of type-system uniformity — the checker
special-cases `Ingredient` in every arithmetic and comparison path.

## Q6. Pinch as separate primitive — Sebesta §6.2, decision #4

**Question.** Defend `Pinch` as its own primitive rather than
`Quantity<Pinch>`.

**Answer.** Pinch admits no arithmetic, no comparison, no scaling, no
substitution-by-ratio. As `Quantity<Pinch>`, every operation on
`Quantity<D>` (every `+`, every `<`, every `scale`, every
`substitute`) would need a Pinch branch. As a separate primitive,
the carve-out lives in the checker's per-operation entry points
(`_check_BinaryOp` calls `_reject_pinch` early) and the rest of the
code never sees Pinch outside two syntactic positions (ingredient
declarations and step-action argument lists). Sebesta §6.2:
primitives are defined by *the operations they support*, not what
they store.

## Q7. Coercion asymmetry — Sebesta §7.4

**Question.** Recipix allows `int → float` and within-dimension unit
coercion. It forbids `float → int` even when representable as an int.
Why the asymmetry?

**Answer.** `int → float` is **information-preserving** — every
64-bit int ≤ 2^53 is exactly representable as IEEE 754 double.
Within-dimension unit coercion is **representation-only** — no
information lost. `float → int` is **narrowing** — silent fractional
truncation. Sebesta §7.4 flags narrowing coercions as the dangerous
kind. Implicit narrowing in `scale` arithmetic
(`int(servings * 1.5)` vs. `int(round(...))`) would be exactly the
silent-bug case. Explicit `to_int(x)` (v2) makes the loss visible.

## Q8. Scale-and-loop trace (project-specific)

**Question.** Open `interpreter.py`'s `_eval_ScaleCall` and
`_eval_RecipeCall`. Sample 1 outputs "pancakes — serves 6" with
**six** pour/flip cycles after `scale(pancakes(servings: 4), by: 1.5)`.
Walk through how six cycles are produced.

**Answer.** Recipe instantiation evaluates step bodies eagerly with
`servings = 4` in env (4 pour/flip cycles produced). `RtRecipe`
captures original `step_decls` and `captured_params`.
`_eval_ScaleCall`: (1) compute `n' = int(round(4 * 1.5)) = 6`,
(2) scale Mass/Volume/Count ingredients, (3) build fresh env
`S_scaled` with `servings = 6` and scaled ingredients, (4) walk every
`step_decl` again via `_exec_step_body(...)`. Step 3's
`repeat servings times` now reads `servings = 6` from `S_scaled`, so
six iterations. Referential transparency (#25) preserved because
`scale` builds a fresh `RtRecipe` — re-execution happens inside the
new value's construction.

## Q9. Parameter passing collapse — Sebesta §9.5

**Question.** Decision #16 says parameter passing in Recipix v1 is
"semantically by-value." Why does Sebesta §9.5's distinction between
by-value, by-reference, by-result, and by-value-result *collapse to
one mode* in Recipix? What single language change would make the
distinctions observable again?

**Answer.** Sebesta §9.5 distinguishes the four modes by their
**observable effects** — the difference between by-value and
by-reference is whether the callee can mutate something the caller
sees. Recipix has no mutation operators (no rebinding of `let` names
per #27, no compound assignment, no `++`). The interpreter shares
large values (`RtRecipe`, `RtList`) by reference for efficiency, but
no callee can modify them. By-value and by-reference are
indistinguishable at the language level. **Adding mutation** — a
mutable accumulator inside `repeat`, or a field-write operator —
would make the difference observable. Decision #16 names this
explicitly as the v2 revisit candidate.

## Q10. What's in your evaluator that isn't in your spec?

**Question.** Name one design decision visible in the interpreter's
behavior but not explicitly locked in spec §12's 35-decision table.
Defend it as an unstated choice.

**Answer.** **Step-body re-execution under scaled servings.** Spec §9
says `scale` "multiplies the servings field by the scalar" — silent
on whether step bodies referring to `servings` should reflect the
scaled value. The interpreter re-executes step bodies in a fresh env
where `servings` is rebound, producing sample 1's six (not four)
pour/flip cycles. Defense: the user-intuitive reading of `scale` is
"double the recipe, double the work, not just the header."
Re-execution preserves referential transparency (#25) — the
original `RtRecipe` is never mutated; re-execution happens inside the
new value's construction. v2 candidate for an explicit row in §12.

## Q11. Static vs. dynamic scoping — Sebesta §5.5

**Question.** Recipix uses static (lexical) scoping. Explain what
"static" means in this context. What two specific Recipix decisions
would break if you switched to dynamic scoping?

**Answer.** **Static (lexical) scoping** means a name's binding is
determined by the program text where it appears — the lookup walks
the *lexical* parent chain at compile time. **Dynamic scoping** would
look up names through the call stack at run time. Two breakages:
(1) **`quantity_of(flour)`** — under dynamic scoping, `flour` would
resolve through whichever scope happened to be active when the
expression evaluates, destroying the type rule that
`quantity_of`'s return type depends on the operand's quantity field.
(2) **`substitute(r, milk, with: oat_milk, ratio: 1.0)`** —
decision #35's bare-IDENT slots resolve through the recipe's
ingredient table at compile time; dynamic scoping would resolve
through the caller's scope, contradicting decision #28 (ingredient
identity is the symbol-table binding).

## Q12. Strong typing claim — Sebesta §6.12

**Question.** Your spec claims Recipix is "strongly typed." What does
Sebesta's §6.12 definition require, and what two specific exceptions
does your D1 §4.5 name where Recipix admits it falls short?

**Answer.** Sebesta §6.12: a language is **strongly typed** if every
operator is defined only on matching operand types, and every type
error is detected (either at compile time or at run time, but
detected). Recipix's claim: yes, with two named exceptions: (a) the
unary `-` operator syntactically applies to quantities, and the
interpreter accepts negative quantities, but the type checker does
not flag them — would matter when `scale` runs against a negative
factor; (b) empty list literals `[]` have inferred element type
`List<?>` which the checker handles defensively but doesn't fully
integrate with `foreach` loop type inference. Both are deliberately
scoped out of v1, named in D5 as v2 polish.

## Q13. Bindings — compile time vs. run time, Sebesta §5.3

**Question.** Identify three things in Recipix bound at compile time
and three things bound at run time.

**Answer.** **Compile time**: recipe and function declarations (name
+ signature); ingredient *types* (the dimension); `let`-bound types
(annotation is required, decision under §7 of spec). **Run time**:
ingredient *quantity values* (evaluated at recipe instantiation);
recipe and function *parameters* (bound at call/instantiation);
`foreach` loop variables (rebound per iteration). The split is what
lets the type checker prove dimensional correctness statically while
keeping quantity arithmetic dynamic.

## Q14. Sample 2's "extra" oat_milk line — project-specific

**Question.** Sample 2 has two `evaluate` statements. The second
(non-substituted) variant shows **both** `milk` and `oat_milk` in
its ingredients block. Why does `oat_milk` appear in a recipe that
isn't substituting anything?

**Answer.** Because of the **no-`this` design** (decision #25): a
recipe cannot reference itself during construction, so alternative
ingredients have to be in scope at the call site, which means they
have to be **pre-declared inside the recipe body**. The recipe
declares `oat_milk : 150 ml * servings` so that the call-site
`substitute(smoothie(...), milk, with: oat_milk, ratio: 1.0)` can
reference it as a binding (decision #28: identity is the binding).
In the non-substituted variant, the pre-declared `oat_milk` simply
sits unused alongside the canonical `milk`. Trade-off: small visual
oddity in exchange for fully functional, referentially transparent
`substitute` semantics.

## Q15. EBNF construct identification — Sebesta §3.1

**Question.** Look at this production from D1 §4.3:
```
<step_decl> ::= "step" STRING_LIT [ "at" <expr> ] [ "for" <expr> ]
                "{" { <step_action> } "}"
```
Identify each EBNF metasymbol used and what it means.

**Answer.** Three metasymbols. `[ ... ]` marks an **optional group**
— the `at <expr>` and `for <expr>` modifiers may appear zero or one
times. `{ ... }` marks **repetition** — zero or more `<step_action>`s
between the braces. Quoted strings (`"step"`, `"at"`, `"{"`) are
**terminals** — literal tokens the parser must consume. `STRING_LIT`
in UPPERCASE is a **token category** from the lexer (a string literal
of any content). The angle-bracket names (`<expr>`, `<step_action>`)
are **nonterminals**, each defined by its own production. The
production encodes decision #23: `at` strictly before `for`, each at
most once.

## Q16. Big-step operational semantics for `foreach` — Sebesta §3.5

**Question.** Write big-step operational semantics for
`foreach x in <list_expr> { <body> }`. State the side conditions.

**Answer.**
```
   <list_expr, S> -> RtList(elems, T)
   S_0 = S
   forall i in [0, |elems|):
       S_i' = S_i[x -> elems[i]]      // bind loop var in fresh scope
       <body, S_i'> -> S_{i+1}'
       S_{i+1} = S_{i+1}' \ {x}        // loop var goes out of scope
   ─────────────────────────────────────────────────────────
   <foreach x in list_expr { body }, S> -> S_{|elems|}
```
**Side conditions**: (a) `|elems| ≥ 0` — empty list produces zero
iterations, no error; (b) `x` is bound to type `T` in each iteration's
body scope; (c) `x` may not shadow a name visible in `S` (the type
checker enforces decision #12 at compile time, so by the time the
interpreter runs this rule, `x` is known not to collide); (d) the
list expression is evaluated **once**, before any iteration —
consistent with decision #18.

## Q17. Why no `while` loop? — design rationale

**Question.** Recipix has `repeat N times` and `foreach x in list`
but no `while <condition>` loop. Defend this choice.

**Answer.** `repeat` and `foreach` are both **intrinsically bounded**
— `repeat` by a non-negative int evaluated once before the loop;
`foreach` by the list's length. Termination is provable from the
loop header alone. A `while` loop whose condition can change between
iterations only makes sense in a language with **side effects** —
without mutation, the condition either holds forever (infinite loop)
or never (zero iterations) and degenerates into `if`. Adding `while`
would force adding mutation (counter increment, accumulator update),
which contradicts decision #16 (no mutation) and decision #27
(assignment-as-statement). v2 candidate if mutation is introduced.

## Q18. Short-circuit observability — Sebesta §7.5

**Question.** You said `&&` and `||` short-circuit left-to-right.
Construct a Recipix program where short-circuit produces a different
observable result than eager evaluation would. If you can't, explain
why not.

**Answer.** You can't construct one in v1. Short-circuit is
**observable** only when the skipped operand has side effects
(throws, prints, mutates). Recipix has no mutation, no I/O, no
exceptions in expression position — so the right operand of `&&`
produces nothing observable when skipped. The one place short-circuit
matters is **runtime safety**: under eager evaluation,
`x != 0 && y / x > 1` would still evaluate `y / x` when `x == 0`,
raising division-by-zero. Under short-circuit, `x != 0` is `false`
and `y / x` is skipped — no error. So short-circuit is a *safety
feature* in Recipix, not an observable-difference feature.

## Q19. The `evaluate`-only constraint — design rationale

**Question.** Spec §9 says `scale` and `substitute` are "call-site
only" — they can appear inside an `evaluate` expression but not
inside a `recipe` or `function` body. Why this restriction?

**Answer.** Two reasons. (1) **No `this`** (decision #25 corollary): a
recipe can't reference itself during construction. If `scale` could
appear inside a recipe body, the recipe being constructed would have
to reason about its own already-built form — circular. By forcing
`scale` / `substitute` to the call site, you can only operate on
recipes that have *already* been instantiated. (2) **Referential
transparency boundary**: `evaluate` is where the program transitions
from "pure value construction" to "produce a result." Restricting
the domain operators to the `evaluate` rooted expression keeps the
recipe definitions themselves pure.

## Q20. Why does spec §10 have error #19? — plan §2.6

**Question.** Spec §10 enumerates 18 compile-time errors; your
`part2_plan.md` §2.6 adds error #19 (single-return enforcement). Why
add a 19th? Where is it implemented?

**Answer.** Spec §7 says `function` bodies have a "Single `return`
statement at the end of the body. No early return in v1." But the
parser doesn't enforce this — `return` is a valid statement form
anywhere in a block. Without a checker rule, a user could write
`function f() -> int { if x { return 1 } return 2 }` and get a
silent acceptance. **Error #19** closes the gap: the checker scans
function bodies at entry, asserts `body[-1]` is a `ReturnStmt`, and
recursively scans nested blocks (`IfStmt`, `RepeatStmt`,
`ForeachStmt`) for any stray `ReturnStmt`. Implemented in
`typechecker.py::_check_single_return` and `_no_return_in`.

## Q21. The three-class action-verb table — design rationale

**Question.** Plan §2.3 collapses the 12 action verbs into three
classes (Heterogeneous: `combine, mix, add, sprinkle`; Homogeneous:
`pour, drizzle, whisk, blend, knead, melt`; Nullary: `bake, flip`).
Defend this collapse over per-verb signatures.

**Answer.** Twelve bespoke signatures means ~12 checker branches,
~24 tests, a memorization tax for the exam, and zero
language-design credit. The spec only commits to "action verbs are
an exception to the homogeneous-list rule" (decision #29) and the
closed verb set — it does **not** mandate per-verb types. The
three-class collapse honors decision #29 (combine/mix/add/sprinkle
mix dimensions including Pinch) and the implicit projection (#31)
for the homogeneous class, with nullary verbs taking their
parameters via step modifiers (`at` / `for`). The cost is small loss
of cooking-faithful semantics — `pour(flour : Mass)` type-checks
under §2.3 even though "pour" linguistically implies liquid. v2 can
add per-verb dimension constraints to the homogeneous class as a
backwards-compatible refinement.

## Q22. Why is there no negative-quantity check? — D1 §4.5 exception (a)

**Question.** Your D1 §4.5 admits an exception to "strong typing":
the interpreter accepts negative quantities but the type checker
doesn't flag them. When would this matter, and why is it scoped out
of v1?

**Answer.** It would matter when `scale(r, by: -0.5)` runs — the
checker catches `by ≤ 0` at run time (decision #25 / runtime error),
but a value like `let bad : Mass = -200 g` slips through. Adding a
**sign discipline** to the dimensional type system (e.g.
`Quantity<D, +>` vs. `Quantity<D, ?>`) would mean either: (a) every
quantity expression gets a sign attribute the checker tracks, which
doubles the dimensional lattice and complicates substitute/scale
rules; or (b) a separate `NonNegative` predicate type that interacts
with every quantity operator. Both were judged too much work for the
v1 schedule. v2 fix is documented in D5 §1. Defense at exam: "scoped
to v1 honestly; named in §4.5 and D5 §1; v2 refinement candidate."

## Q23. Banker's rounding — design rationale

**Question.** Your `scale` rounds `servings` via `int(round(s * by))`
— banker's rounding. Why not truncation (`int(s * by)`) or ceiling
(`math.ceil(s * by)`)?

**Answer.** Three rules; one example: `scale(recipe-of-3, by: 0.5)`.

| Rule | servings = | Result |
|---|---|---|
| Truncation | `int(1.5)` = `1` | 33% serving loss — silently halves the cook |
| Ceiling | `math.ceil(1.5)` = `2` | over-orders ingredients vs. shown servings |
| Banker's | `int(round(1.5))` = `2` | unbiased on half-way cases |

Banker's rounding ($\text{round-half-to-even}$ on 1.5 → 2; on 2.5
→ 2) is the **statistically unbiased** choice. The trade-off is
that 0.5 and 1.5 both round to even, which can surprise users —
but pinned by a test that exercises the boundary, and documented in
plan §2.6.

## Q24. What does "referentially transparent" actually mean? — Ch. 1 / Ch. 7

**Question.** Your D1 and D4 entries repeatedly claim Recipix v1 is
"referentially transparent." Define the term precisely and identify
the three Recipix decisions that *together* guarantee it.

**Answer.** **Referential transparency**: an expression can be
replaced by its value without changing the meaning of the program.
Equivalently, evaluating the same expression in the same scope always
produces the same result — no hidden state, no side effects. Three
decisions together guarantee it:
(1) **#16 by-value semantics** — no callee can mutate caller-visible
    state.
(2) **#25 functional `scale`/`substitute`** — domain operators produce
    fresh `RtRecipe` values, never mutate the original.
(3) **#27 assignment as statement** — no expression has a value-side
    effect; `let` binds once and is immutable.
Together these make every expression a pure mathematical function
from its inputs to its result. The benefit is **simpler reasoning**:
any expression can be substituted with an equivalent one without
breaking the program, and operand evaluation order (#18) becomes
unobservable on values.

## Q25. Cross-cutting question — combining 3 chapters

**Question.** Your sample 3 program triggers a compile-time type
error: `let total : Mass = flour + water` where `flour : Ingredient<Mass>`
and `water : Ingredient<Volume>`. Trace through (a) what Ch. 4 (lexer
+ parser) produces, (b) what Ch. 5 (binding) and Ch. 6 (types) decide,
and (c) why the error message points at the `+` operator's line, not
the `let` keyword's line.

**Answer.**
**(a) Ch. 4 (lex + parse)**: lexer produces tokens `let`, `IDENT(total)`,
`:`, `TYPE_KW(Mass)`, `=`, `IDENT(flour)`, `+`, `IDENT(water)`. Parser
builds `LetStmt(name="total", type_name="Mass", expr=BinaryOp(op="+",
left=Identifier("flour"), right=Identifier("water"), line=13))`. No
error at parse time — the syntax is valid.
**(b) Ch. 5 (binding) + Ch. 6 (types)**: at the enclosing recipe
scope, the checker resolves `flour` to `"Ingredient:Mass"` and `water`
to `"Ingredient:Volume"` via `Environment.lookup`. In `_check_BinaryOp`,
`_dimension_of(lt)` returns `"Mass"` (implicit projection #31) and
`_dimension_of(rt)` returns `"Volume"`. Both are non-None; both go
into `_check_quantity_binop` with `op = "+"`. The rule "dimensions
must match" fires `raise TypeCheckError(line=node.line, col=0, msg=
"dimension mismatch: cannot + Mass and Volume", error_code=1)`.
**(c) Why the `+` line, not the `let` line**: `node.line` on the
`BinaryOp` was set by the parser when it consumed the `+` operator
— which is the same line as `let` in this fixture, but if `flour +`
were on line 13 and `water` were on line 14 (multi-line expression),
the error would cite line 13 (the operator's line). Spec convention:
errors cite the **offending operator**, not the enclosing construct.

---
---

# Self-test checklist

Before walking into the exam, you should be able to:

1. **Recite the 7-level precedence ladder** from memory, with
   associativity for each level (left / non-assoc / right).
2. **Walk through sample 1's output** explaining each ingredient line
   and the six pour/flip cycles cold, in under 90 seconds.
3. **Name 3 Sebesta sections** for each major decision (#10, #17,
   #18, #20, #25, #27, #31, #34).
4. **Cite at least 2 documented AI-was-wrong cases** from your D4
   journal — the rubric weighs "critical evaluation" and the exam
   may probe how you noticed.
5. **Explain why your spec admits negative quantities** (it does —
   §3 line on unary minus, named as exception in D1 §4.5). This is
   exam-bait; pre-load the v1-scoped-out / v2-fixable defense.
6. **Defend the `pour(flour : Mass)` accept** under the three-class
   collapse — the "cooking semantics vs. type-system parsimony"
   framing from E3.
7. **Walk through the dimension-mismatch type-error trace** end to
   end (Q25 in §3) — connecting Ch. 4, 5, 6 in one answer.
8. **Define referential transparency** precisely and name the three
   decisions (#16, #25, #27) that together guarantee it (Q24).
9. **Distinguish strong typing vs. type safety** — Sebesta §6.12 vs.
   the broader concept (Recipix is strong; type safety is broader
   and includes runtime checks).
10. **State the difference between operational, denotational, and
    axiomatic semantics** (Sebesta §3.5) and identify which you
    used in D1 §4.4.

Good luck on the 28th. The work is done; the exam is just walking
the grader through what you already built.
