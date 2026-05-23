# CSE 341 — Practice Exam (Part 1)
### Recipix · Berk Hakan Öge · 90 minutes

**Format note:** This is sized to match the real exam — 10 questions, mix of
short-answer and draw/annotate, roughly 9 min/question. **Attempt every
question on paper first**, then check the Answer Key below. Self-grading
guide at the very end.

> Three sheets of A4 handwritten notes allowed in the real exam (one side each,
> your name on each). Practice **without notes first**, then with, to see how
> much your cheat sheet would actually save you.

---

## PART A — Project-Specific (60 minutes, 6 questions)

### Q1. [10 min] Defense of Decision #34

> In your final D1 spec, `quantity_of` is classified as a **unary operator**,
> not a function. (Decision #34 in your design table.)
>
> (a) Explain in 4–6 sentences *why* a function declaration could not express
> the same semantics. Reference Sebesta Ch. 6 terminology.
>
> (b) Name one specific trade-off you accepted by making this choice.
>
> (c) On the syntactic side, point to the exact production in your EBNF
> grammar where this decision is visible.

---

### Q2. [10 min] Parser trace + AST

Consider the Recipix expression:

```
quantity_of(flour) + 100 g * 2
```

(a) **Trace** your parser's function-call sequence from `_parse_expr` down to
all leaf productions. List every function entered and what it produces,
in order.

(b) **Draw** the resulting AST. Label every node type and edge.

(c) On the AST, **annotate** the node where Decision #34 was enforced and
the node where Decision #7 was enforced.

---

### Q3. [10 min] Scope and binding resolution

Consider this Recipix program:

```
function double(n: int) -> int {
    return n * 2
}

recipe cake(servings: int) serves servings {
    ingredient flour : 100 g * servings
    ingredient sugar : double(servings) * 1 g

    step "Mix" {
        let total : Mass = flour + sugar
        if servings > 4 {
            let large : bool = true
        }
    }
}

evaluate cake(servings: 6)
```

Answer the following:

(a) For each of the four occurrences of `servings` in the code, identify
**which declaration** the name resolves to under static scoping. State
the enclosing scope for each.

(b) At what **binding time** is the *type* of `flour` known? At what binding
time is its *value* known? Justify each.

(c) What is the **lifetime** of the variable `large` according to Sebesta's
categories (§5.4.3)? Justify.

(d) Why is the program valid — i.e., why doesn't the declaration of `large`
inside the `if` block constitute illegal shadowing? Reference Decision #12.

---

### Q4. [10 min] Decision #17 — honest analysis

Your retrospective (D5) describes Decision #17 (non-associative comparisons)
with this nuance: "the *same* comparison cannot chain — `a < b == c` should
parse as `(a < b) == c`."

(a) Examine the following code excerpt from your `_parse_rel`:

```python
if self._check(LT, LTE, GT, GTE):
    op_tok = self._advance()
    right = self._parse_add()
    if self._check(LT, LTE, GT, GTE, EQ, NEQ):
        raise ParseError(..., "comparison operators are non-associative; "
                              "use parentheses to group comparisons (Decision #17)")
```

What does this parser **actually do** when it encounters `a < b == c`?
Trace it step by step.

(b) Is the parser's behavior consistent with the spec's intent? Explain
honestly.

(c) Suppose the examiner asks: "Is your spec strongly consistent with your
implementation? Justify." Give a careful, honest answer (a B-grade
"yes" loses points; a confident wrong answer loses more).

---

### Q5. [10 min] Decision #35 and grammar visibility

In your spec, `substitute`'s ingredient-name slots are restricted to **bare
identifiers**, not general expressions.

(a) Write the EBNF production for `<substitute_call>` exactly as it appears
in your spec §13.

(b) In your parser, **two checks** enforce that the slot is a bare
identifier. Identify both. (One is the token-type check; the other is a
lookahead guard. Be specific.)

(c) Why does this design choice make Decision #28 ("ingredient identity is
the binding, not the `name` field") visible at the grammar level rather
than in the type checker? Argue in 3–4 sentences.

(d) The `SubstituteCall` AST node has `original_name: str` and
`replacement_name: str` — typed as `str`, not `Expr`. Why is this the
right AST shape given Decision #35?

---

### Q6. [10 min] Sebesta evaluation criteria for Recipix

Sebesta §1.3 lists four broad evaluation criteria: **readability,
writability, reliability, and cost.**

(a) Which two does Recipix **prioritize**? Give one concrete language design
choice that supports each.

(b) Which one does Recipix **knowingly sacrifice**? Give one concrete
example of a design choice where it was traded away.

(c) Pick a single design choice (any from your 35-decision table) and show
how it pulls in **opposite directions** on at least two evaluation
criteria. Name the trade-off explicitly.

---

## PART B — General PL on Sebesta Ch. 1, 3, 4, 5 (30 minutes, 4 questions)

### Q7. [8 min] EBNF → BNF + left recursion

(a) Convert the following EBNF rule to **pure BNF**:

```
<add_expr> ::= <mul_expr> { ("+" | "-") <mul_expr> }
```

(b) Your BNF version will be **left-recursive**. Why is that a problem for
a top-down (LL) predictive parser?

(c) How does your hand-written recursive-descent parser **avoid this
problem** while still implementing left-associative `+` and `-`?
Reference the actual control structure used in `_parse_add`.

---

### Q8. [8 min] Grammar ambiguity — dangling else

Consider the following classic ambiguous grammar fragment:

```
<stmt> ::= "if" <expr> <stmt>
        |  "if" <expr> <stmt> "else" <stmt>
        |  <other>
```

(a) Construct an input string with this grammar that has **two distinct
parse trees**. Sketch both trees.

(b) Sebesta §3.2 names three common strategies for resolving the
dangling-else ambiguity in real languages. Name them.

(c) Which strategy does Recipix use? Show, by reference to the EBNF
production for your `<if_stmt>`, why your grammar is **unambiguous by
construction**.

---

### Q9. [8 min] Operational semantics

Give an **operational** semantics in inference-rule form (Sebesta §3.5) for
the Recipix construct:

```
if <C> { B1 } else { B2 }
```

You may use:
- `<E, S> -> v` to mean "expression E in state S evaluates to v"
- `<B, S> -> S'` to mean "block B in state S transitions to state S'"

Cover both branches of the conditional.

Then: state **one specific design decision** that this semantics encodes —
i.e., something an alternative semantics could have done differently.

---

### Q10. [6 min] LL(1) analysis

(a) Define what it means for a grammar to be **LL(1)** in Sebesta's
terminology.

(b) Is the Recipix grammar LL(1)? Be specific — give a yes/no answer and
identify any places where it is not.

(c) For each non-LL(1) place you identify, explain why the parser still
works deterministically.

---

# 🛑 STOP HERE FIRST 🛑

**Don't read below until you've attempted every question on paper.**
The answers are designed to be the kind of response that earns A-rubric
points. Quick scan ≠ practice.

---
---
---

# ANSWER KEY

> Grading note: a strong answer in this course ties a design choice to
> **(a) Sebesta terminology**, **(b) a named trade-off accepted**, and
> **(c) an alternative not taken**. Most answers below follow this shape.

---

## Q1 Answer — Decision #34 defense

**(a) Why a function can't express it.** A Recipix function declaration has
the form `function <name>(<params>) -> <return_type> { ... return <expr> }`
where `<return_type>` is a single, fixed type-name keyword. The semantics of
`quantity_of` is *type-level*: its return type depends on which `Quantity<D>`
dimension lives inside the `Ingredient` operand. So the type rule is
`Ingredient → <dimension of its quantity field>`, where the dimension is
extracted from the argument's record structure. This is precisely the kind
of dependency a fixed return-type annotation cannot express. In Sebesta §6.7
terms, this is structural type information being propagated outward from the
operand's record type — and our function-type system has no provision for
that. Making `quantity_of` a unary operator avoids needing such a type
representation at all.

**(b) Trade-off accepted.** A small departure from syntactic uniformity:
`quantity_of(flour)` *looks like* a function call but isn't one. The user
cannot redefine it, store it in a variable, or pass it as an argument. In
exchange we get a cleaner type system that doesn't require dependent return
types.

**(c) Grammar visibility.** Decision #34 appears in the `<unary>` production:

```
<unary> ::= "-" <unary>
         |  "!" <unary>
         |  "quantity_of" "(" <expr> ")"
         |  <primary>
```

The third alternative is a *dedicated alternative at the unary level*. It
is never reached through `<primary>` (which is where function calls live),
so the parser literally cannot parse `quantity_of` as a function call.

---

## Q2 Answer — Parser trace + AST

**(a) Trace.** Starting from `_parse_expr` for `quantity_of(flour) + 100 g * 2`:

| # | Function | Action |
|---|---|---|
| 1 | `_parse_expr` | calls `_parse_or` |
| 2 | `_parse_or` → `_parse_and` → `_parse_eq` → `_parse_rel` → `_parse_add` | drops to `_parse_mul` for the left operand |
| 3 | `_parse_mul` | drops to `_parse_unary` |
| 4 | `_parse_unary` | sees `quantity_of` — **enters Decision #34 branch.** Advances, expects `(`, calls `_parse_expr` for operand. |
| 5 | `_parse_expr` (recursive) | parses `flour` via the cascade → `_parse_primary` → `_parse_ident_or_call`. No `(` follows `flour`. Returns `Identifier('flour')`. |
| 6 | back in `_parse_unary` | consumes `)`. Returns `QuantityOf(Identifier('flour'))`. |
| 7 | back in `_parse_mul` | sees no `*`/`/` yet. Returns the QuantityOf. |
| 8 | back in `_parse_add` | sees `+`. Advances. Calls `_parse_mul` for right operand. |
| 9 | `_parse_mul` → `_parse_unary` → `_parse_primary` | sees `INT_LIT(100)`. Advances. Peeks: `UNIT_KW('g')`. **Decision #7 fires.** Returns `QuantityLit(100, 'g')`. |
| 10 | back in `_parse_mul` | sees `*`. Advances. Calls `_parse_unary` → `_parse_primary` → returns `IntLit(2)`. |
| 11 | `_parse_mul` | builds `BinaryOp(*, QuantityLit(100, 'g'), IntLit(2))`. No more `*`/`/`. Returns. |
| 12 | `_parse_add` | builds `BinaryOp(+, QuantityOf(...), BinaryOp(*, ...))`. No more `+`/`-`. Returns. |
| 13 | bubbles up through `_parse_rel`, `_parse_eq`, `_parse_and`, `_parse_or` | each returns unchanged. |

**(b) AST diagram.**

```
                          BinaryOp(+)
                         /           \
              QuantityOf              BinaryOp(*)
                  |                   /         \
            Identifier         QuantityLit       IntLit
              ('flour')         (100, 'g')         (2)
```

**(c) Annotations.**
- **Decision #34** is enforced at the `QuantityOf` node: it was produced
  by `_parse_unary`'s dedicated branch, NOT by `_parse_primary`'s
  ident-or-call routing.
- **Decision #7** is enforced at the `QuantityLit(100, 'g')` node:
  `_parse_primary` saw `INT_LIT` then peeked ahead for an adjacent
  `UNIT_KW`, combining the two tokens into one AST node.

---

## Q3 Answer — Scope and binding resolution

**(a) Four occurrences of `servings`:**

1. `recipe cake(servings: int)` — this is the **declaration**, the binding
   site. Scope: recipe-`cake` body.
2. `serves servings` — refers to the parameter declared in (1). Scope
   resolved by looking outward: the `serves` expression is in the recipe
   header's parameter-scope. Resolves to the recipe-`cake` parameter.
3. `ingredient flour : 100 g * servings` — the ingredient declaration's
   right-hand-side is in the recipe body's scope; `servings` is in scope
   from the recipe parameters. Resolves to the recipe-`cake` parameter.
4. `if servings > 4` — inside the step body, which is inside the recipe
   body. Static scoping walks outward: step body → recipe body. Found:
   resolves to the recipe-`cake` parameter.

All four references resolve to the **same** declaration (#1) — that's the
point of static scoping: program structure determines name resolution.

**(b) Binding times for `flour`:**
- **Type** (`Mass`): bound at **compile time**. The right-hand side
  `100 g * servings` has type `Mass` because `100 g` is `Mass` (quantity
  literal) and `Mass * scalar` stays `Mass`. The type checker can determine
  this purely from program text.
- **Value**: bound at **run time** — specifically at recipe instantiation
  when `cake(servings: 6)` is evaluated. The right-hand side references
  `servings` which is a parameter, so the actual numeric value can only be
  computed once `servings` has been supplied at the call site
  (here, `6`, producing `600 g`).

This split — types static, values dynamic — is exactly Sebesta §5.4.

**(c) Lifetime of `large`:**
**Stack-dynamic, per iteration of the enclosing if-branch entry.** More
precisely: `large` is a `let`-bound name inside the `if`-then body, which
opens a fresh scope under Decision #11. Its lifetime begins when control
reaches the `let` and ends when control exits the `if`-then block. This is
Sebesta's **stack-dynamic** category (§5.4.3): allocated when the scope
is entered, deallocated when the scope is exited, lifetime bounded by
block execution.

**(d) Why no shadowing:**
`large` is **not visible** in any enclosing scope. It is introduced for
the first time inside the `if`-then body. Decision #12 prohibits
**redeclaring** an identifier visible in an enclosing scope, not declaring
new identifiers in inner scopes. `total` (declared in the step body, one
level up) is not the same name as `large`, so there's no conflict.
Shadowing would only occur if we wrote `let total : Mass = ...` again
inside the `if` block.

---

## Q4 Answer — Decision #17 honest analysis

**(a) What the parser actually does with `a < b == c`:**

1. `_parse_or → _and → _eq → _rel → _add → _mul → _unary → _primary → _ident_or_call`. Returns `Identifier('a')`.
2. Bubbles back up to `_parse_rel`. Sees `<`. Enters the `if` branch.
   Advances. Calls `_parse_add` for the right operand.
3. `_parse_add` parses `b` (via the cascade) and returns it. No `+`/`-`
   follows. So `right = Identifier('b')`.
4. Back in `_parse_rel`. The non-associativity check fires:
   `self._check(LT, LTE, GT, GTE, EQ, NEQ)`. The next token is `==` — which
   is in this set.
5. **Raises** `ParseError(..., "comparison operators are non-associative; "
   "use parentheses to group comparisons (Decision #17)")`.

So the parser **rejects** `a < b == c` at the `==` token.

**(b) Consistent with spec intent?**
**No, not strictly.** My D5 retrospective explicitly says the *intent* of
Decision #17 is that the *same* comparison family shouldn't chain — i.e.
`a < b == c` *should* parse as `(a < b) == c` because `<` and `==` are
different operators. To match that intent, `_parse_rel` would need to check
only `(LT, LTE, GT, GTE)` after consuming a relational operator (not the
full `(LT, LTE, GT, GTE, EQ, NEQ)` set), and `_parse_eq` would need to check
only `(EQ, NEQ)` — keeping the families separate. The current code lumps
them together, which is the stricter rule and over-rejects mixed comparisons.

**(c) Honest answer to "are spec and impl strongly consistent?":**

> "Strongly consistent on the major decisions — every Part 1 spec decision
> from #7 through #35 is enforced at the right level of the recursive-descent
> stack, with `QuantityOf` and `SubstituteCall` having the AST shapes that
> §14 of the spec requires. There is **one consciously flagged inconsistency**
> on Decision #17: the spec intent (per my D5) is that only the *same*
> comparison family is non-associative, so `a < b == c` should parse as
> `(a < b) == c`. My parser's `_parse_rel` lumps relational and equality
> operators into one non-associativity check and rejects this case at parse
> time. This is on our Part 2 polish list. The behavior is stricter than the
> spec intended, not looser — programs that should parse don't, but no
> illegal programs slip through."

(This is the kind of answer the rubric rewards: it acknowledges the issue,
locates it precisely, characterizes its severity, and credits Part 2 work.
A "yes, perfectly consistent" answer would be marked down if the examiner
checks the code.)

---

## Q5 Answer — Decision #35 and grammar visibility

**(a) The EBNF production:**

```
<substitute_call> ::= "substitute" "(" <expr> ","
                          IDENT ","
                          "with" ":" IDENT ","
                          "ratio" ":" <expr>
                        ")"
```

The two ingredient slots are `IDENT` terminals — bare identifiers — not
`<expr>` non-terminals. The `ratio` slot remains `<expr>` because a numeric
ratio can legitimately be a computed expression.

**(b) Two checks in the parser:**

1. **Token-type check.** After `_expect_kw('substitute')` and the opening
   `(` and the recipe expression and the comma:
   ```python
   orig_tok = self._peek()
   if orig_tok.type != IDENT:
       raise ParseError(..., "substitute: original ingredient must be a
                              bare identifier, not '...'  (Decision #35)")
   ```
   This catches cases like `substitute(r, 100 g, ...)` where the user wrote
   a literal in the slot.

2. **Comma lookahead guard.** After consuming the IDENT:
   ```python
   if not self._check(COMMA):
       bad = self._peek()
       raise ParseError(..., "substitute: original ingredient must be a
                              bare identifier — expressions are not allowed
                              here (Decision #35); got '...'")
   ```
   This catches cases like `substitute(r, flour + sugar, ...)` where the
   user wrote an identifier *followed by* an operator (which would otherwise
   be parsed as an expression). The guard says: if the next token after the
   IDENT isn't a comma, the user wrote an expression — reject.

Both checks together ensure the slot is *exactly* a bare identifier and
nothing more.

**(c) Why grammar-level rather than type-checker-level visibility:**

Decision #28 says ingredient identity *is* the binding in the recipe's
symbol table — not a runtime value, not the `name` field's string contents.
By restricting the `substitute` slots to bare identifiers at the *grammar*
level, the parser only accepts inputs that *look like* symbol-table
references. The reader of the source code can see, just from the syntactic
shape, that `substitute(r, milk, with: oat_milk, ratio: 1.0)` is asking
"replace the binding `milk` with the binding `oat_milk`" — there's no
expression that could be a runtime value, so the binding-resolution
interpretation is the *only* possible interpretation. If we'd allowed
`<expr>` in the slot, the source code would suggest that `substitute(r,
some_function(), ...)` should work via runtime value matching, which is
not what Decision #28 wants.

**(d) AST shape — `str` not `Expr`:**

The grammar guarantees the slot is an identifier. An AST that types the
field as `Expr` would force every later phase (type checker, interpreter,
pretty printer) to handle "what if this Expr is somehow not an
Identifier?", even though the parser proves it always is. Typing the field
as `str` reflects the grammar's guarantee directly in the AST: there is no
runtime case for "what if it's an arbitrary expression." The AST faithfully
mirrors the grammar; consumers of the AST get the correct invariant for
free.

---

## Q6 Answer — Sebesta evaluation criteria for Recipix

**(a) Prioritized criteria:**

1. **Reliability.** Concrete choice: strong typing (#8) with dimensional
   discipline. The type system catches `flour + water` (Mass + Volume) at
   compile time, not at "the cake came out wrong" time. Non-associative
   comparisons (#17) and no shadowing (#12) also reflect this priority.

2. **Writability** for the domain user. Concrete choice: implicit
   Ingredient → Quantity projection (#31), which lets the user write
   `flour + 100 g` instead of `quantity_of(flour) + 100 g` everywhere.
   Action verbs that read like English (`combine`, `bake`, `flip`) are
   another writability investment.

**(b) Sacrificed criterion:**

**Cost.** Specifically, compile-time cost and language-feature cost. We pay
substantial compile-time work for dimensional type checking. We refuse
implicit narrowing (no float → int), so users must call `to_int(x)`
explicitly (Part 2). We added a separate AST node `QuantityOf` and dedicated
parser branches for `quantity_of` (#34) and `substitute` (#35) — extra
implementation complexity in exchange for a cleaner type system. None of
these are free; we accepted the cost for reliability.

**(c) A choice pulling in opposite directions:**

**Decision #7 — quantity literals as two tokens (`200 g`).**
- **Pulls toward reliability/simplicity of the lexer**: numbers and unit
  keywords stay orthogonal; the lexer's state machine doesn't need to
  recognize unit suffixes on numbers. Lexical ambiguity is eliminated.
- **Pulls *against* writability**: users must remember to leave a space
  (`200g` is rejected); construction from computed values requires the
  awkward idiom `<expr> * 1 g` (Decision #30).

**Trade-off accepted:** lexer simplicity and unambiguous parsing **at the
cost of** a small syntactic verbosity for users. We chose this side because
the alternative would either complicate the lexer or require a
context-sensitive tokenization rule — both worse for reliability.

---

## Q7 Answer — EBNF → BNF + left recursion

**(a) Conversion:**

```
<add_expr>      ::= <mul_expr>
                 |  <add_expr> "+" <mul_expr>
                 |  <add_expr> "-" <mul_expr>
```

(Unfolding the EBNF `{ ... }` repetition into a recursive alternative.
Each iteration of the `{ ... }` corresponds to one application of the
left-recursive rule.)

**(b) Why left recursion breaks top-down predictive parsing:**

A predictive parser for `<A> ::= <A> α | β` chooses an alternative based on
the first token it sees. But for the left-recursive alternative, before
matching anything, the parser must *first* call `<A>` recursively. This
recursion has no base case in the token stream — the parser hasn't consumed
anything, so the same situation reappears on each call. **Infinite descent,
no progress.** Sebesta §4.4.1 calls this out as the fundamental reason LL
grammars must be left-recursion-free.

**(c) How `_parse_add` avoids this:**

The hand-written parser uses an **iterative while-loop** to implement the
EBNF repetition directly, without ever recursing on `_parse_add` from
inside itself:

```python
def _parse_add(self):
    left = self._parse_mul()                     # parse first <mul_expr>
    while self._check(PLUS, MINUS):              # iterate over (+ | -)
        op_tok = self._advance()
        right = self._parse_mul()                # parse next <mul_expr>
        left = BinaryOp(op=op, left=left, right=right, ...)
    return left
```

Each iteration reassigns `left` to a new `BinaryOp` whose left child is the
*previous* `left`. This produces a left-leaning tree —
`BinaryOp(-, BinaryOp(+, a, b), c)` for input `a + b - c` — which is exactly
left-associative grouping. The loop progresses by consuming an operator
token each iteration, so termination is guaranteed (the token stream is
finite).

---

## Q8 Answer — Grammar ambiguity and dangling else

**(a) An ambiguous input:**

```
if A
    if B
        S1
    else
        S2
```

(I'm using indentation only for readability — the grammar has no whitespace
sensitivity.) Two parse trees:

**Tree 1 — `else` belongs to the inner `if`:**
```
   if A ──── if B ──── S1
                  └── else ── S2
```

**Tree 2 — `else` belongs to the outer `if`:**
```
   if A ──── (if B ── S1)
        └── else ── S2
```

Both are derivations of the same input under the given grammar — that's the
definition of ambiguity.

**(b) Three resolution strategies (Sebesta §3.2):**

1. **Disambiguating rule.** Add a semantic side rule: "`else` always matches
   the nearest unmatched `if`." The grammar stays ambiguous on paper, but
   the parser implements the rule. Used in C, C++, Java.

2. **Different grammar that's unambiguous.** Split `<stmt>` into
   `<matched_stmt>` (every nested `if` has its `else`) and `<unmatched_stmt>`
   (the outermost `if` is `else`-less). More verbose; eliminates ambiguity
   at the grammar level.

3. **Mandatory delimiters.** Require explicit closing keywords or braces on
   every conditional body. The ambiguity simply can't be expressed because
   the grammar can no longer produce a brace-less body. Used in Ada
   (`if ... end if`), Recipix (`{ ... }`).

**(c) Recipix's strategy:**

Recipix uses strategy 3 — **mandatory braces** (Decision #20). The EBNF:

```
<if_stmt> ::= "if" <expr> "{" { <stmt> } "}"
              [ "else" "{" { <stmt> } "}" ]
```

There's no production for a brace-less `if`-body. The closing `}` of the
inner `if` is unambiguous, and the `else` (if present) can only attach to
the syntactically preceding `if` — there's no place for it to "drift up"
to an outer `if` because the outer `if`'s body has already been closed by
its own `}`. **Unambiguous by construction.**

---

## Q9 Answer — Operational semantics for `if`

Using the conventions given:

```
<C, S> -> true       <B1, S> -> S'
──────────────────────────────────────
  <if C { B1 } else { B2 }, S> -> S'


<C, S> -> false      <B2, S> -> S'
──────────────────────────────────────
  <if C { B1 } else { B2 }, S> -> S'
```

**For the else-less form `if C { B1 }`:**

```
<C, S> -> true       <B1, S> -> S'
──────────────────────────────────
       <if C { B1 }, S> -> S'


            <C, S> -> false
       ─────────────────────────
        <if C { B1 }, S> -> S
```

(When the condition is false and there's no else, the state is unchanged.)

**Design decision this semantics encodes:**

Exactly **one** of the two branches executes — they are mutually exclusive
on the value of `C`. The condition `C` is evaluated **once**, not once per
branch. An alternative semantics could have evaluated both branches and
selected one (wasteful but well-defined), or could have evaluated `C` in
the context of *each* branch (which would matter if `C` had side effects,
but in Recipix v1 it cannot). The chosen semantics commits to the standard
short-evaluation conditional. This decision becomes observable the moment
the language admits side-effecting expressions; in v1 it's an aesthetic
choice but a meaningful one for forward compatibility.

---

## Q10 Answer — LL(1) analysis

**(a) Definition.** A grammar is **LL(1)** (Sebesta §4.4.1) if it can be
parsed top-down deterministically using **one** token of lookahead — i.e.,
for any non-terminal with multiple alternatives, the FIRST set of each
alternative is disjoint from the FIRST sets of the others, and (if the
non-terminal can derive ε) its FOLLOW set is disjoint from each
alternative's FIRST set. In practice: the next single token must uniquely
determine which production to apply.

**(b) Is Recipix LL(1)?**

**Almost everywhere, yes; one place uses two tokens of lookahead.**

The cleanly LL(1) parts:
- Top-level dispatch: `recipe`, `function`, `evaluate` are disjoint keywords.
- Statements: `let`, `if`, `repeat`, `foreach`, `return`, and the
  action-verb token class are all disjoint.
- Expressions: the precedence cascade is LL(1) at every level — each
  alternative is distinguished by its leading operator token.
- The optional-unit-keyword inside `_parse_primary` for quantity literals
  uses one-token lookahead (peek for `UNIT_KW`).

**The one non-LL(1) place: `_parse_ident_or_call`.**

After seeing `IDENT (`, the parser needs to distinguish:
- `pancakes(servings: 4)` — keyword-arg recipe call → `RecipeCall`
- `half(servings)` — positional-arg function call → `FunctionCall`

The decision requires looking *two* tokens past the `(`: is the first
argument shaped like `IDENT :` (keyword arg) or not (positional arg)? That's
LL(2).

**(c) Why the parser still works deterministically.**

Two reasons:
1. **No backtracking.** The parser commits to its choice after looking two
   tokens ahead and never reconsiders. The two-token lookahead is *bounded
   and finite* — we always look exactly that far, regardless of input. Time
   complexity stays linear.
2. **Zero-arg calls handled separately.** When the lookahead reveals `)`
   right after `(`, we can't tell which kind of call it is from any
   syntactic information, so we defer to the type checker by emitting an
   `AmbiguousCall` AST node. The parser is *deterministic* about its
   inability to decide — it doesn't guess; it records the ambiguity and
   moves on. This is a clean architectural separation: the parser does
   syntactic work; semantic identity resolution belongs to the type
   checker.

So strictly, the parser is LL(2). It's still linear-time, predictive, and
backtracking-free — the practical properties LL(1) buys you. The LL(2) move
is local to one production and doesn't propagate complexity elsewhere.

---

# Self-Grading Guide

For each question, score yourself **A / B / C / D** using the project rubric:

- **A — Excellent.** Used Sebesta terminology correctly, named a specific
  trade-off, referenced your spec/code by section or function name where
  appropriate, mentioned an alternative not taken.
- **B — Good.** Mostly correct, possibly missing one of: trade-off,
  alternative considered, or specific Sebesta reference.
- **C — Adequate.** Got the surface answer but couldn't tie it to Sebesta
  framework or your own code specifically.
- **D — Weak.** Couldn't answer or contradicted your own spec/implementation.

**Diagnostic patterns:**
- If you got Q1 / Q4 / Q5 with confidence, you can defend major design
  decisions — the most exam-critical skill.
- If Q2's trace was rough, **redo it on paper one more time** — it
  exercises the whole parser stack.
- If Q3 (scope/binding) felt slow, re-read the binding-time and lifetime
  tables in the language notes until they're automatic.
- If Q9 (operational semantics) was hard, copy the `repeat` and `if`
  inference rules onto your cheat sheet — these are formulaic once you've
  seen them.
- If Q10 (LL analysis) was hard, the *one* thing to remember:
  **LL(2) at `_parse_ident_or_call`, plus `AmbiguousCall` for zero-arg.**

**Time check:** Did you finish in 90 minutes? If not, where did you lose
time? Cheat-sheet blocks that save the most time:
- The 5 decision-to-code-location mappings (Block B of parser notes §12)
- The binding-time and lifetime tables (Block C of language notes §4)
- Operational semantics rules (Block D)
