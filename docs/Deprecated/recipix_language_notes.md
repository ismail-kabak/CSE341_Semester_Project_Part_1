# Recipix — Language Study Notes (Part 1 Exam)

> Exam scope: **Sebesta Ch. 1, 3, 4, 5.** Type system (Ch. 6) and expression
> semantics (Ch. 7) are technically in your spec but are *Part 2* exam material.
> You may still be asked to *defend* any design decision; just don't burn
> memorization on §6/§7 internals.

---

## 1. Identity & "what makes this a DSL" (Ch. 1)

**Recipix** = DSL for describing, parameterizing, scaling, substituting recipes.
Every numeric quantity carries a dimension (`Mass`, `Volume`, `Count`,
`Temperature`, `Duration`); the type system catches dimension mismatches at
compile time.

### The one-liner you must be able to say cold

> "What makes Recipix a DSL and not a generic scripting language?"
> **Dimensional type discipline.** A general-purpose language treats `200` and
> `500` as raw numbers. Recipix lifts the dimensional structure into the type
> system — adding grams to milliliters is a compile-time error. The three
> domain-specific operations (`evaluate`, `scale`, `substitute`) and the
> structured types (`Recipe`, `Ingredient`) all exist to preserve this
> invariant.

### Sebesta §1.3 evaluation criteria — how Recipix maps

| Criterion | Recipix's stance |
|---|---|
| **Readability** | Good. Mandatory braces (#20), keywords like `serves`, `at`, `for`, action verbs that read like English (`combine`, `bake`). Sacrificed slightly: two-token quantity literals (`200 g` not `200g`) — a writability cost paid for unambiguous lexing. |
| **Writability** | High for domain users. Implicit `Ingredient → Quantity` projection (#31) means you write `flour + 100 g` not `quantity_of(flour) + 100 g`. Sacrificed: arbitrary expressions in `substitute` slots (#35). |
| **Reliability** | The headline. Strong typing (#8), no shadowing (#12), single-assignment (#13), dimensional checking, non-associative comparisons (#17 — `a < b < c` doesn't parse) all push errors to compile time. |
| **Cost** | Knowingly deprioritized. Performance is not a goal; static type-checking work at compile time is paid for at user-experience reliability. |

### Language category

Imperative + small functional flavor. Statements drive recipe declarations and
step bodies; expressions are referentially transparent (no mutation in v1),
which is why parameter passing collapses to "by-value" (#16).

---

## 2. Lexical structure (Ch. 4)

### Token categories
| Category | Examples |
|---|---|
| Identifier | `flour`, `pancakes`. RE: `[a-zA-Z_][a-zA-Z0-9_]*`. ASCII only, case-sensitive. |
| Integer literal | `200`, `0`, `42` |
| Float literal | `1.5`, `0.75` |
| String literal | `"Mix dry"` — UTF-8, any char except `"` and newline, no escapes in v1 |
| Reserved keyword | `recipe function ingredient step let if else repeat times foreach in at for evaluate scale substitute serves with by ratio return quantity_of` (plus `true`/`false` which produce `BOOL_LIT`, not keyword tokens) |
| Type-name keyword | `int float bool Mass Volume Count Temperature Duration Pinch` |
| Action-verb keyword | `combine mix pour melt whisk blend bake flip add sprinkle drizzle knead` |
| Unit keyword | `mg g kg ml l tsp tbsp cup °C min hr count pinch` |
| Operator | `+ - * / == != < <= > >= && \|\| ! =` |
| Separator | `( ) { } [ ] , : ->` |

### Why two tokens for a quantity (Decision #7)
`200 g` is **`INT_LIT(200)` then `UNIT_KW('g')`**. Only whitespace and `//`
comments may appear between them. The alternative — `200g` as one token —
would force the lexer to know unit keywords at the character level and would
break the clean orthogonal "number / keyword" split.
- Valid: `200 g`, `1.5 kg`, `200    g`, `200 /* heavy */ g`
- Invalid: `200g` (no separator → **lexical error**)

### `°C` is one token
`°C` is a single `UNIT_KW` with `.value == '°C'`. The degree symbol cannot
appear standalone. Defensive against Unicode classification issues.

### Why this matters for the exam
Lexical analysis is Ch. 4. Be ready to:
- Write the regex for an identifier
- Explain why keywords like `recipe` are **reserved words**, not predefined
  identifiers (cannot be redefined; this simplifies parsing)
- Distinguish *lexeme* (the literal substring) from *token* (lexeme + category
  tag)
- Explain why state diagrams / DFAs are typically used for scanners

---

## 3. Syntax — EBNF, ambiguity, precedence (Ch. 3, 4)

### Why EBNF, not raw BNF?
EBNF (Sebesta §3.1) adds `{ ... }` (zero-or-more), `[ ... ]` (optional), and
`( ... | ... )` (alternatives). Raw BNF has only alternation and recursion.
EBNF is **strictly equivalent in expressive power** to BNF (you can always
unfold `{X}` into a recursive rule) but it's far more compact for lists and
optional fragments. Recipix uses EBNF throughout for the param lists, step
modifiers, and list literals.

### Resolving ambiguity in Recipix's grammar

Two ambiguities every grammar must resolve. Sebesta §3.2.

| Ambiguity | Recipix's resolution |
|---|---|
| **Operator precedence** (`1 + 2 * 3` — does `+` or `*` bind tighter?) | Separate productions per precedence level (§5 / Decision #17). `*` and `/` bind tighter than `+` and `-` because `_parse_mul` is called inside `_parse_add`. |
| **Operator associativity** (`a - b - c` — left or right?) | Left for `+ - * /` (loops, accumulating left operand). Right for unary. **Non-associative** for `< <= > >= == !=` — explicitly rejected at parse time (#17). |
| **Dangling else** (`if A if B then C else D` — which `if` does the `else` belong to?) | Eliminated **by construction**: both `if` and `else` bodies require `{ ... }` braces (#20). No ambiguity to resolve because the grammar simply cannot produce a brace-less branch. |

### Sebesta-style ambiguity demonstration

The classic ambiguous grammar:
```
<stmt> ::= "if" <expr> <stmt>
        |  "if" <expr> <stmt> "else" <stmt>
        |  <other>
```
The string `if A if B C else D` has **two parse trees**: `else D` could belong
to the inner or outer `if`. Standard fixes:
1. Disambiguating rule ("else matches nearest unmatched if") — semantic patch
2. Different grammar that forces matched/unmatched distinction — verbose
3. **Mandatory braces** — Recipix's choice

### Operator precedence (locked, full table — §5 of spec)

| Level | Operators | Associativity |
|---|---|---|
| 1 (highest) | unary `-`, `!`, `quantity_of(...)` | right |
| 2 | `*`, `/` | left |
| 3 | `+`, `-` (binary) | left |
| 4 | `<`, `<=`, `>`, `>=` | **non-associative** |
| 5 | `==`, `!=` | **non-associative** |
| 6 | `&&` | left |
| 7 (lowest) | `\|\|` | left |

Operand evaluation order is **left-to-right and fully defined** (Sebesta §7.6).
This rules out an entire class of compiler-specific bugs that languages like
C accept.

### Grammar productions you may be asked to write

```
<program>        ::= { <recipe_decl> | <function_decl> | <eval_stmt> }
<recipe_decl>    ::= "recipe" IDENT "(" [ <params> ] ")" "serves" <expr> "{"
                       { <ingredient_decl> } { <step_decl> }
                     "}"
<function_decl>  ::= "function" IDENT "(" [ <params> ] ")" "->" <type_name>
                     "{" { <stmt> } "return" <expr> "}"
<params>         ::= <param> { "," <param> }
<param>          ::= IDENT ":" <type_name>
<ingredient_decl>::= "ingredient" IDENT ":" <expr>
<step_decl>      ::= "step" STRING_LIT [ "at" <expr> ] [ "for" <expr> ]
                     "{" { <stmt> } "}"
<if_stmt>        ::= "if" <expr> "{" { <stmt> } "}" [ "else" "{" { <stmt> } "}" ]
<repeat_stmt>    ::= "repeat" <expr> "times" "{" { <stmt> } "}"
<foreach_stmt>   ::= "foreach" IDENT "in" <expr> "{" { <stmt> } "}"

<expr>           ::= <or_expr>
<or_expr>        ::= <and_expr> { "||" <and_expr> }
<and_expr>       ::= <eq_expr>  { "&&" <eq_expr> }
<eq_expr>        ::= <rel_expr> [ ("==" | "!=") <rel_expr> ]      // non-assoc
<rel_expr>       ::= <add_expr> [ ("<"|"<="|">"|">=") <add_expr> ] // non-assoc
<add_expr>       ::= <mul_expr> { ("+" | "-") <mul_expr> }
<mul_expr>       ::= <unary>    { ("*" | "/") <unary> }
<unary>          ::= "-" <unary> | "!" <unary>
                  |  "quantity_of" "(" <expr> ")"      // Decision #34
                  |  <primary>
<primary>        ::= INT_LIT [ UNIT_KW ]               // Decision #7 quantity
                  |  FLOAT_LIT [ UNIT_KW ]
                  |  BOOL_LIT | STRING_LIT | IDENT
                  |  IDENT "(" [ <args> ] ")"
                  |  <list_lit>
                  |  <scale_call>
                  |  <substitute_call>
                  |  "(" <expr> ")"
<substitute_call>::= "substitute" "(" <expr> ","
                       IDENT ","                       // Decision #35: bare IDENT
                       "with" ":" IDENT ","            // Decision #35: bare IDENT
                       "ratio" ":" <expr> ")"
```

### Static vs. dynamic semantics — Sebesta §3.5

- **Static semantics** = rules that can be checked without running the program
  (type-rules, scoping). In Recipix: every dimension-mismatch error, every
  "unknown identifier", every "no shadowing" check.
- **Dynamic semantics** = the *meaning* of running constructs. Three styles:
  1. **Operational** — define meaning by describing state transitions of an
     abstract machine. *Recipix uses this style.*
  2. **Denotational** — map programs to mathematical functions over states.
  3. **Axiomatic** — use logical predicates (Hoare triples `{P} S {Q}`); used
     for verification. *The handout explicitly says this is NOT accepted here.*

### Operational semantics example — `repeat n times B`

The version from the handout's sample:
```
<n, S> -> n'   <B, S> -> S1   <B, S1> -> S2   ...   <B, S_{n'-1}> -> S_{n'}
─────────────────────────────────────────────────────────────────────────
                        <repeat n times B, S> -> S_{n'}
```
**What this reveals:** `n` is evaluated *once* at loop entry, not each
iteration. This is a real design decision — changing it would change observable
semantics if `n` could have side effects (in v1 it can't, but the rule still
matters).

### Sebesta-style mini Q&A (skim before bed)
- **Q:** Is your grammar LL(1)?
  **A:** Mostly. The expression cascade is LL(1) because each level either
  consumes a level-specific operator or falls through. One place we use
  **2-token lookahead** is in `_parse_ident_or_call`: after `IDENT (`, we peek
  ahead to see if the first arg is `IDENT :` (keyword arg → recipe call) or an
  expression (positional → function call). So the grammar is LL(2) at that
  point.
- **Q:** Convert `<expr> ::= <term> { ("+" | "-") <term> }` to pure BNF.
  **A:**
  ```
  <expr>     ::= <expr_tail>
  <expr_tail>::= <term>
              |  <expr_tail> "+" <term>
              |  <expr_tail> "-" <term>
  ```
  (Note: this is **left-recursive**, which is fine for a hand-written or
  bottom-up parser but bad for top-down predictive — which is why we use the
  EBNF "loop" form in our recursive-descent parser.)

---

## 4. Names, binding, scope, lifetime (Ch. 5)

### Identifier rules
`[a-zA-Z_][a-zA-Z0-9_]*`, case-sensitive, ASCII only. Cannot collide with
**any** reserved/type/action/unit keyword.

### Static (lexical) scoping — Decision #11
**Each of these opens a fresh scope:**
- `recipe` body (params + ingredients visible inside)
- `function` body (params visible inside)
- `step` body (enclosing recipe's ingredients visible)
- `if` block and `else` block (independently)
- `repeat` body
- `foreach` body (loop variable visible only inside)

**Inner scopes can read outer names. No shadowing** (Decision #12) — declaring
an identifier already visible anywhere up the chain is a compile-time error.

### Why static, not dynamic?
- **Static (lexical):** resolves names by program text — the *enclosing*
  declaration determines the binding. Predictable from reading the code.
- **Dynamic:** resolves names by call chain — whoever was the most recent
  caller's binding wins. Easier to implement (just walk the call stack) but
  notoriously hard to reason about; abandoned by mainstream languages after
  early Lisp/APL.

Recipix chooses static because **reliability** is the top criterion and the
program text should be the single source of truth for what a name refers to.
Dynamic scoping would let a caller silently change the meaning of a recipe's
ingredient lookup — catastrophic in a domain where "what does `flour` mean
here?" must be unambiguous.

### Binding times (Sebesta §5.4) — Recipix's table

| Thing | Bound at |
|---|---|
| Recipe & function names + signatures | **Compile time** |
| Ingredient *types* | **Compile time** |
| `let`-bound names — their *type* | **Compile time** (annotation required) |
| Ingredient *quantity values* | **Run time** (at recipe instantiation) |
| Recipe parameters | **Run time** (at instantiation) |
| Function parameters | **Run time** (at call) |
| Loop variables | **Run time** (at iteration entry) |
| `let`-bound names — their *value* | **Run time** (when control reaches declaration) |

The clean split: **types** are static, **values** are dynamic. This is exactly
the picture Sebesta paints in §5.4.3.

### Lifetime (Sebesta §5.4.3) — Recipix's table

| Entity | Lifetime category |
|---|---|
| Recipe declarations | **Static** (whole program) |
| Function declarations | **Static** |
| Recipe parameters | **Stack-dynamic** (per instantiation) |
| Function parameters | **Stack-dynamic** (per call) |
| Ingredients within a recipe | **Stack-dynamic** (per recipe instantiation) |
| `let`-bound names | **Stack-dynamic** (per enclosing scope) |
| Loop variables | **Stack-dynamic** (per iteration) |

**No `Pinch` here, no explicit-heap, no implicit-heap.** Recipix has no manual
allocation and no garbage-collected heap: everything that lives is either
program-lifetime (static) or scope-lifetime (stack-dynamic). This is a
deliberate simplification consistent with the no-mutation, no-aliasing design.

### Single-assignment discipline (Decision #13)
- Ingredient names: declared exactly once per recipe scope.
- `let`-bound names: declared exactly once per enclosing scope, immutable.
- Recipe and function parameters: bound once at call, immutable.
- `foreach` loop variables: rebound each iteration, immutable within.

### "Show on this code excerpt where x resolves" — practice trace

```
recipe pancakes(servings: int) serves servings {
    ingredient flour : 50 g * servings   // <-- 'servings' here
    step "Mix" {
        let total : Mass = flour + 100 g
        if servings > 4 {                // <-- 'servings' here
            let total : Mass = flour     // ERROR: shadowing 'total'!
        }
    }
}
```
- `servings` in the ingredient decl resolves to the **recipe parameter** (the
  enclosing scope is the recipe body, where `servings` is bound).
- `servings` inside the `if` body resolves to the *same* recipe parameter —
  static scoping walks outward through the enclosing block scopes (`if`
  body → step body → recipe body → here it is).
- The inner `let total : Mass = flour` is **a compile-time error** because
  `total` is already visible from the enclosing step body. Decision #12: no
  shadowing.

### Why no `this`? (Decision #25)
`scale` and `substitute` are **call-site only** — they cannot appear inside a
recipe body, and a recipe cannot reference itself. Every Recipix expression
is referentially transparent in v1. This is the strongest possible
simplification for the scope/lifetime story: there are no mutable bindings,
no aliasing, no self-reference cycles.

---

## 5. Type system, operations, errors (light overview — mostly Ch. 6/7)

> You don't need to memorize this for Exam 1. It's here because if the
> examiner asks "why did you make `Pinch` a separate primitive?" or "why name
> equivalence for recipes?", a one-paragraph defense matters more than
> rote recall.

### The five "signature" type-side decisions

| # | Decision | One-sentence defense |
|---|---|---|
| **#4** | `Pinch` is its own primitive, not a `Quantity<D>` | A pinch is a *gesture*, not a measurement; modeling it as `mg` would silently allow `1 pinch + 5 mg`, which is nonsense. |
| **#8** | Strong typing | Every operator is defined only on matching operand types; reliability over flexibility. |
| **#9** | Within-dimension unit coercion AND int→float widening; never float→int across dimensions | The principle: coerce only when no information is lost AND no dimensional commitment is violated. |
| **#10** | Structural for `Quantity<D>`, `Ingredient`, `List<T>`; **name** for `Recipe` | Two `Mass` values are the same type regardless of unit (units are convertible). But `pancakes` and `crepes` should not be interchangeable just because they happen to share an ingredient shape. |
| **#16** | Semantically by-value for all types | Recipix has no mutation, so by-value and by-reference collapse to a single observable mode. Implementation shares immutable references for recipes/lists as an optimization. |

### The three domain operations (Decision #25)
All **functional** (return new values, don't mutate), all **call-site only**
(cannot appear inside a recipe body).
- `evaluate <recipe_expr>` — top-level only; the entry point.
- `scale(<recipe>, by: <scalar>)` — multiplies Mass/Volume/Count quantities
  and `servings`; **does not** scale Temperature or Duration.
- `substitute(<recipe>, <ident>, with: <ident>, ratio: <scalar>)` — slots
  are bare identifiers (Decision #35).

---

## 6. Sample programs — what each one demonstrates

### Sample 1 — pancakes with helper function
Demonstrates: parameterized recipe, function declaration with return type,
`half(servings) * 1 count` quantity-from-expression idiom (consequence of #7
+ #30), action verbs with heterogeneous args (`combine(flour, salt)` mixing
Mass and Pinch — explicit carve-out per #29), `repeat n times`, step
modifiers `at 180 °C for 3 min`.

### Sample 2 — smoothie with substitution
Demonstrates: `substitute` at call site (#25 — no `this`), bare identifier
slots (#35), the no-`this` consequence — `oat_milk` is *pre-declared inside
the recipe* so it exists as a binding the call site can reference.

### Sample 3 — broken recipe (type error)
Demonstrates: implicit `Ingredient → Quantity` projection (#31) turning
`flour + water` into `Mass + Volume`, then the dimension mismatch is caught
at the `let total : Mass = flour + water` line. **Parse-time clean, type-check
fails.**

---

## 7. Likely Q&A — rehearse out loud

**Q: Why did you choose static scoping?**
A: Reliability is our top evaluation criterion. With static scoping the
meaning of every name is determined by where it appears in the program text,
not by who called the surrounding function. In a recipe DSL this is critical:
when a step references `flour`, that must mean the ingredient declared in
*this* recipe, full stop. Dynamic scoping would let a caller silently change
that meaning, which is exactly the class of error a domain-specific language
should rule out.

**Q: What would break if you switched to dynamic scoping?**
A: A function like `function half(n: int) -> int { return n / 2 }` could no
longer be safely reused across recipes, because `n` would resolve through the
call chain, not the lexical enclosing scope. We'd also need a different
implementation of `let`-bindings — currently they're stack-dynamic per scope;
under dynamic scoping they'd need shadow stacks per name.

**Q: Why mandatory braces?**
A: It eliminates the dangling-else ambiguity **by construction** rather than
by a disambiguating rule. The grammar simply cannot produce a brace-less
branch, so there's no ambiguity to resolve and the parser doesn't need a
special rule like "else matches nearest unmatched if."

**Q: Is your grammar ambiguous?**
A: No. Ambiguity is resolved structurally everywhere it could arise:
precedence and associativity by separate productions per level (cascade
`<or> → <and> → <eq> → <rel> → <add> → <mul> → <unary> → <primary>`),
dangling-else by mandatory braces (#20), comparison chaining forbidden by
non-associativity (#17).

**Q: Give me operational semantics for `if`.**
A:
```
<C, S> -> true    <B1, S> -> S'
─────────────────────────────────
   <if C { B1 } else { B2 }, S> -> S'

<C, S> -> false   <B2, S> -> S'
─────────────────────────────────
   <if C { B1 } else { B2 }, S> -> S'
```
(If there is no else, the second rule's body becomes a no-op.)

**Q: What's the difference between binding time of an ingredient's type vs. its value?**
A: An ingredient's **type** is bound at compile time — the dimension is known
from the right-hand side at declaration. Its **value** is bound at run time,
specifically at recipe instantiation, because the right-hand side may reference
recipe parameters: `ingredient flour : 50 g * servings` cannot be evaluated
until `servings` is supplied at the call site.

**Q: Why two tokens for `200 g`?**
A: To keep the lexer simple and orthogonal. If `200g` were a single token, the
lexer would need to recognize unit keywords as suffixes of numbers, mixing the
number-recognition state machine with the keyword-recognition one. Splitting
into two tokens lets the lexer treat numbers and keywords independently;
the parser then assembles them via a one-token lookahead in `_parse_primary`.

**Q: How does your language prioritize Sebesta's evaluation criteria?**
A: Reliability and writability for domain users come first. Cost is
knowingly sacrificed — we do extra compile-time work for dimension checking
and we allow no implicit narrowing. Readability is good but not pristine —
the two-token quantity rule (`200 g`) costs a tiny bit of visual density
in exchange for unambiguous lexing.
