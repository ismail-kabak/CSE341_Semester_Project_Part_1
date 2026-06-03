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

The following is the dense reference content distilled from Part 1.
Pick which lines go on which sheet based on what you tend to forget.

## Sheet 1 — Quick reference

### Seven-level precedence ladder

```
  Level 1  unary - / ! / quantity_of(...)   right-assoc
  Level 2  * /                              left-assoc
  Level 3  + - (binary)                     left-assoc
  Level 4  < <= > >=                        non-associative
  Level 5  == !=                            non-associative
  Level 6  &&                               left-assoc
  Level 7  ||                               left-assoc
```

### Top 12 decisions (memorise the number + one-line summary)

```
#4   Pinch is its own primitive (not Quantity<Pinch>)
#7   Quantity literals are TWO tokens (number + unit)
#10  Equivalence: structural for Quantity/Ingredient/List,
                  name for Recipe
#11  Static (lexical) scoping
#12  No shadowing (compile-time error)
#13  Single-assignment (let names are immutable)
#17  Comparison non-associative (no chaining at parse time)
#18  Operand evaluation L-to-R, fully defined
#20  Mandatory braces on if/else (no dangling-else)
#25  scale/substitute are functional (fresh value, no mutation)
#27  Assignment is a statement, not an expression
#31  Implicit Ingredient → Quantity projection
#34  quantity_of is a unary operator, not a function
#35  substitute slots are bare IDENT terminals
```

### Sebesta quick map

```
§1.3   Eval criteria: readability, writability, reliability, cost.
       Recipix priorities: reliability > writability > readability > cost
§3.5   Operational semantics — Recipix uses big-step
§5.4   Lifetime: stack-dynamic for everything except recipe/fn decls
§5.5   Static scoping; lookup walks parent-pointer chain
§6.2   Primitives defined by operations they support, not storage
§6.5   Lists: homogeneous, type inferred, no indexing, foreach-only
§6.12  Strongly typed = type errors always detected (Recipix: yes)
§6.14  Type equivalence — Recipix splits structural and name
§7.2   Precedence + associativity table
§7.4   Coercion — Recipix allows widening + within-dimension only
§7.5   Short-circuit: &&, || left-to-right
§7.6   Operand order — Recipix locks L-to-R
§9.5   Parameter passing — collapses to by-value in absence of mutation
```

## Sheet 2 — Mechanics (walk-through ready)

### `scale(r, by: k)` — 7 steps

```
1. <r, S> -> RtRecipe(name, n, ingredients, step_decls,
                      captured_params, ...)
2. <k, S> -> k : (int | float); if k <= 0 -> RuntimeRecipixError
3. n' = int(round(n * k))                  # banker's rounding
4. for (id, ing) in ingredients:
     if dim in {Mass, Volume, Count}: scale by k
     if dim in {Temperature, Duration}: unchanged (intensive)
     if RtPinch: unchanged
5. Build S_scaled (fresh env): servings -> n', ingredients -> scaled
6. Re-execute step bodies under S_scaled
7. Return fresh RtRecipe(...) — original never mutated (decision #25)
```

### `substitute(r, x, with: y, ratio: k)` — 6 steps

```
1. <r, S> -> RtRecipe
2. Look up x, y in recipe.ingredient_types
   (bare IDENT terminals per #35 — symbol-table lookup, not runtime)
3. new_quantity = original.quantity * k
4. Build new ingredients: replace original slot with replacement
5. POP the standalone y binding (consumed) — only substituted slot
   appears in output
6. Return fresh RtRecipe — original untouched
```

### Sample 1 output explanation

```
evaluate scale(pancakes(servings: 4), by: 1.5)
  -> pancakes(servings: 4) instantiates with servings=4
     ingredients: 50*4=200g flour, 60*4=240ml milk, half(4)=2 eggs
     steps eager-evaluated in env where servings=4
       step 3 unrolls "repeat 4 times" -> 4 pour/flip cycles
     returns RtRecipe with step_decls + captured_params snapshot

  -> scale(..., by: 1.5)
     n' = int(round(4 * 1.5)) = 6
     ingredients scaled: 200*1.5=300g, 240*1.5=360ml, 2*1.5=3 eggs
     fresh env S_scaled: servings=6, scaled ingredients
     RE-EXECUTE step bodies under S_scaled
       step 3 "repeat 6 times" now unrolls -> 6 pour/flip cycles
     fresh RtRecipe(serves=6, scaled ingredients, 6-cycle steps)
```

### Implicit Ingredient → Quantity projection (#31)

```
flour + 100 g                # both project, lt = Mass, rt = Mass
  is equivalent to
quantity_of(flour) + 100 g

The type checker's _dimension_of(t):
  if t in {Mass, Volume, Count, Temperature, Duration}: return t
  if t.startswith("Ingredient:") and not endswith(":Pinch"):
      return t[len("Ingredient:"):]
  return None
```

### AmbiguousCall resolution

```
parser: f()  -> AmbiguousCall(name="f")
typechecker._rewrite_ambiguous walks AST:
  if name in functions: -> FunctionCall(name, args=[], line)
  if name in recipes:   -> RecipeCall(name, kwargs=[], line)
  else: leave intact -> later raises error #4 (unknown ident)

interpreter sees AmbiguousCall -> raises RuntimeRecipixError
  (loud-fail to prevent silent skip of type checker)
```

## Sheet 3 — Defenses (rationale paragraphs in shorthand)

### Non-associative comparison (#17)

```
Left-assoc: 1kg < flour < 2kg
  parses as (1kg < flour) < 2kg
  evaluates 1kg < flour -> bool
  then compares bool < 2kg
  RUNTIME type error
Non-assoc:
  parses as PARSE ERROR
  user must write (1kg < flour) && (flour < 2kg)
Trade-off: small writability cost, big reliability + error-msg win
```

### Short-circuit `&&` / `||` L-to-R

```
- Standard programmer expectation (Sebesta §7.5)
- Direction matches decision #18 operand order
- One mental model for both -> consistency
- Eager would force nesting in null-checks
```

### Operand evaluation order locked (#18)

```
- C/C++: "unspecified" -> compiler can reorder
- Cost in a DSL: same program, different runtime errors, different lines
- Recipix: L-to-R, fully defined
- Reliability > optimization (which §1 already deprioritized)
- Unobservable on values because no side effects (#27 + #16)
- Observable only in error reporting -> predictable line numbers
```

### Assignment as statement (#27)

```
- Only binding: let <name> : <type> = <expr>
- Every expression referentially transparent
- Decision #18 L-to-R becomes unobservable (no operand can mutate)
- Operational semantics in §4.4 simplified
- Trade-off: no while ((x = read()) != null) -- but v1 has no I/O loop
- v2 mutation -> revisit this rule FIRST
```

### Pinch as separate primitive (#4)

```
- Quantity<Pinch> would need per-op carve-outs
- Separate primitive: carve-out in checker's per-op entry points only
- Sebesta §6.2: primitives defined by operations supported
- Pinch supports ceremonial operations only
```

### Equivalence split (#10)

```
- Records modeling DATA SHAPE -> structural
  (Ingredient, List<T>, Quantity<D>)
- Records modeling IDENTITY -> name
  (Recipe -- pancakes != crepes even with same field set)
- v1's closed type-name set forecloses collision concerns
  that motivate name-equiv in open systems
```

### `quantity_of` at unary level (#34)

```
- Return type depends on operand type:
    quantity_of : Ingredient<D> -> D
- No FunctionType signature can express this dependency
- Unary-level production gives dedicated grammar slot
- Side benefit: can't be shadowed, can't be assigned,
  can't be passed as a value
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
