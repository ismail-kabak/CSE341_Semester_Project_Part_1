# CSE 341 — Exam 2 Study Notes
### Recipix · Berk Hakan Öge (210104004132) · 28 May 2026, 90 min

> Scope per handout §3.3: Sebesta **Ch. 6 (types)** and **Ch. 7
> (expressions / assignment)**, with possible reference back to
> Ch. 1, 3, 4, 5. Personalised paper — Berk gets questions about his
> own components (parser P1, interpreter, rendering, D1 §4.3 / §4.4 /
> §4.7, and his four §4.8 rationale paragraphs). You may bring three
> sheets of A4 handwritten notes, one side each.

---

## 1. Quick-reference card (memorise cold)

### 1.1 Type-system decisions (Sebesta Ch. 6)

| Sebesta concept | Recipix locked answer |
|---|---|
| Primitive types (§6.2) | `int`, `float`, `bool`, five `Quantity<D>` (`Mass/Volume/Count/Temperature/Duration`), `Pinch` (separate primitive, decision #4) |
| Strong typing (§6.12) | **Yes** — every operator only on matching operand types, every implicit coercion listed |
| Coercion rules (§7.4) | (a) within-dimension unit coercion (`200 g + 1 kg = 1200 g`); (b) `int → float` widening in mixed-mode. Never `float → int`; never cross-dimension. |
| Type equivalence (§6.14) | **Split** (decision #10): structural for `Quantity<D>` / `Ingredient` / `List<T>`; **name** for `Recipe` |
| Structured types (§6.5–6.7) | One: `List<T>`, homogeneous, type inferred at literal construction, no user-facing indexing, `foreach`-only iteration |
| Type checking time | Compile time. Type checker walks AST, annotates `.inferred_type` per Expr node, rewrites `AmbiguousCall` to `FunctionCall` / `RecipeCall` |

### 1.2 Expression decisions (Sebesta Ch. 7)

| Sebesta concept | Recipix locked answer |
|---|---|
| Precedence (§7.2) | 7 levels: (1) unary `-` / `!` / `quantity_of(...)`, (2) `*` `/`, (3) `+` `-`, (4) `<` `<=` `>` `>=` non-assoc, (5) `==` `!=` non-assoc, (6) `&&`, (7) `\|\|` |
| Associativity (§7.2) | Left for binary arithmetic & logical; **non-associative for comparison (decision #17)**; right for unary prefix |
| Short-circuit (§7.5) | Yes, `&&` and `\|\|` short-circuit left-to-right |
| Operand evaluation order (§7.6) | **Left-to-right, fully defined** (decision #18). Stronger than C's "unspecified". |
| Assignment (§7.6) | **Statement, not expression** (decision #27). `let` is the only binding form. No compound assignment, no `++`. |

### 1.3 Scope & binding (Sebesta Ch. 5)

| Concept | Recipix |
|---|---|
| Scoping | Static (lexical) — decision #11 |
| Shadowing | Forbidden — decision #12 |
| Single-assignment | All names immutable in their scope — decision #13 |
| Parameter passing | Semantically by-value (no mutation exists in v1) — decision #16 |
| Lifetime | Recipes/functions static; everything else stack-dynamic |

### 1.4 Decision quick-cite table (your top 10 from the spec's 35)

```
#4   Pinch is a separate primitive, not Quantity<Pinch>
#7   Quantity literals are TWO tokens (number + unit)
#10  Equivalence: structural for Q/I/L, name for Recipe
#17  Comparison non-associative (no chaining)
#18  Operand evaluation L→R, fully defined
#20  Mandatory braces on if/else (no dangling-else)
#25  scale/substitute are functional — fresh recipe value, no mutation
#27  Assignment is a statement, not an expression
#31  Implicit Ingredient → Quantity projection in arithmetic
#34  quantity_of is a unary operator, not a function
#35  substitute slots are bare IDENT terminals
```

---

## 2. Your interpreter, line by line (questions WILL drill into this)

### 2.1 `scale(r, by: k)` — what actually runs

Big-step operational, locked in your D1 §4.4. Read these out loud
until you can recite them:

```
1. Evaluate r → RtRecipe(name, n, ingredients, step_decls, captured_params, …)
2. Evaluate k → scalar (int or float). If k ≤ 0 → RuntimeRecipixError.
3. n' = int(round(n * k))                    ← banker's rounding (plan §2.6)
4. For each (id, ing) in ingredients:
     if dim ∈ {Mass, Volume, Count}: scale by k
     if dim ∈ {Temperature, Duration}: unchanged (intensive quantities)
     if ing.quantity is RtPinch: unchanged
5. Build fresh env S_scaled with servings rebound to n' and new ingredients
6. Re-execute every step_decl against S_scaled  ← the key step!
7. Return fresh RtRecipe — old recipe value never mutated (decision #25)
```

**Why banker's rounding** (`int(round(x))`)?
- Truncation toward zero: `scale(r-of-3, by: 0.5) → 1 serving` (33% serving loss)
- Ceiling: over-orders ingredients vs. shown servings
- Banker's: unbiased on half-way cases

**Why re-execute step bodies?** User expectation: doubling a recipe
doubles the work. Without re-execution, sample 1 would show `serves 6`
with only 4 pour/flip cycles (the `repeat servings times` was bound
to 4 at instantiation). Re-execution preserves referential transparency
(the new `RtRecipe` is fresh, no mutation) while letting `servings`
mean what users think it means.

### 2.2 `substitute(r, x, with: y, ratio: k)` — what actually runs

```
1. Evaluate r → RtRecipe
2. Look up x and y in the recipe's ingredient binding table — bare IDENT
   slots (decision #35). The grammar guarantees these are not arbitrary
   expressions, so the lookup is a static symbol-table operation
3. new_quantity = original_quantity * k
4. Build new ingredients dict: replace original slot with replacement
5. POP the standalone replacement binding (consumed) → only the
   substituted slot appears in output
6. Return fresh RtRecipe (functional, no mutation)
```

**Why does sample 2's non-vegan variant show both `milk` and `oat_milk`?**
The `oat_milk` ingredient is *pre-declared* in the recipe body so the
call-site `substitute` can reference it as a binding (decision #28:
identity is the binding, not the field). When no substitute is applied,
the pre-declared alternative sits unused next to the canonical one.
This is the no-`this` design (decision #25): a recipe can't reference
itself during construction, so alternatives go inside.

### 2.3 Implicit `Ingredient → Quantity` projection (decision #31)

When an `Ingredient` value appears in arithmetic, comparison, or
substitution context that expects a `Quantity<D>`, it auto-projects
to its quantity field. Equivalent explicit form: `quantity_of(ing)`.

Inside a step body: `flour + 100 g` is shorthand for
`quantity_of(flour) + 100 g`. Without this, every arithmetic
expression in a recipe would need explicit `quantity_of()` calls.

**Trade-off accepted**: small loss of type-system uniformity for
substantial readability gain.

### 2.4 `AmbiguousCall` resolution

The parser produces `AmbiguousCall(name)` for zero-arg calls like
`flip()` because it can't tell whether it's a function or a recipe.
The type checker walks the AST, builds a symbol table of
`{recipes: dict, functions: dict}`, and rewrites every `AmbiguousCall`
to `RecipeCall(kwargs=[])` or `FunctionCall(args=[])` by name lookup.

If your interpreter ever sees an `AmbiguousCall` at run time, it
raises a loud `RuntimeRecipixError("internal error: AmbiguousCall
reached the interpreter")` — this prevents silent failures when the
type checker is skipped.

---

## 3. Your §4.8 rationale paragraphs (defend cold)

### 3.1 Why non-associative comparison (#17)

Left-associative `a < b < c` parses as `(a < b) < c`. Type checker
catches it, but the user gets a *bool vs. quantity* type error at run
time, not the obviously-intended "is b between a and c?" intent.
Non-associative catches the bug at **parse time** with a clean
"chained comparison not allowed" message. Trade-off: users write
`a < b && b < c` explicitly. Reliability over writability — consistent
with §1.3.

### 3.2 Why short-circuit `&&` / `||` left-to-right (Sebesta §7.5)

Short-circuit matches what programmers expect; eager `&&` would force
`if x != null && x.field > 0` to nest as two `if`s. Direction left-to-right
matches decision #18's operand evaluation order, so users have *one*
mental model for both. Right-to-left would have been internally
consistent if operand order were also right-to-left, but Sebesta §7.6
notes left-to-right is the strongly dominant convention.

### 3.3 Why operand evaluation order is fully defined (#18, Sebesta §7.6)

Most language specs leave operand order "unspecified" so compilers
can reorder for optimization (C, C++). For a DSL this is hostile:
the same program running twice can hit two different
division-by-zero candidates and report two different line numbers on
two different platforms. Recipix locks left-to-right because
**reliability and predictable error reporting matter more than
performance in v1.** Performance was already deprioritized in §1.

### 3.4 Why assignment is a statement, not an expression (#27)

`let` is the only binding form. The whole language becomes
**referentially transparent**: same expression in same scope = same
value every time. This lets decision #18's L-to-R order be entirely
unobservable (no expression can mutate). Trade-off: no
`if ((x = compute()) > 0)` form — but v1 has no mutation or I/O
loop anyway, so the missing pattern doesn't arise. If v2 introduces
mutation, this is the **first** decision to revisit.

---

## 4. Sebesta vocabulary you must deploy correctly

| Term | One-line definition | Recipix instance |
|---|---|---|
| Strong typing (§6.12) | Type errors always detected | Yes, except negative-quantity gap (admitted in D1 §4.5) |
| Coercion (§7.4) | Implicit type conversion | Within-dim unit + int→float widening |
| Narrowing coercion (§7.4) | Information-losing direction | float→int — **explicitly forbidden** |
| Structural equivalence (§6.14) | Type identity = field shape | `Ingredient`, `List<T>`, `Quantity<D>` |
| Name equivalence (§6.14) | Type identity = declaration site | `Recipe` |
| Static scoping (§5.5) | Resolution by lexical structure | Yes, decision #11 |
| Stack-dynamic lifetime (§5.4) | Created/destroyed with activation | Recipe parameters, ingredients, `let`-bound names |
| Referential transparency | Same expr → same value, always | True in Recipix v1 (no mutation) |
| Side-effect-free | No mutation observable | Decision #25: scale/substitute are functional |
| Short-circuit (§7.5) | Skip 2nd operand if 1st determines result | `&&` and `\|\|` L-to-R |
| Pass-by-value (§9.5) | Caller's copy unmodifiable | All params; observable equivalent of by-value because no mutation exists |

---

## 5. Practice questions with answers

### Q1. Operand evaluation order — Sebesta §7.6

**Question.** Your spec locks operand evaluation order to "left-to-right,
fully defined" (decision #18). Give a Recipix program where the
*choice* of order changes the observable result, and explain why
this is different from the canonical C example `i++ + i++`.

**Answer.** Because Recipix has no side-effecting expressions (no
mutation per decision #16, no assignment-as-expression per
decision #27), order is *unobservable* on values — the same expression
in the same scope evaluates to the same result regardless of order.
The one observable place is **error reporting**:
`let x : int = f(a/0) + g(b/0)` raises division-by-zero from `a/0`
under L-to-R, not from `b/0`. The error message cites a specific
line; if order were "unspecified", different platforms could report
different lines. C's `i++ + i++` doesn't exist in Recipix because
(a) there is no `++` and (b) `=` is not an expression — so no
operand can mutate state another operand reads.

### Q2. Non-associative comparison — Sebesta §7.2, decision #17

**Question.** Your precedence table marks `<`, `<=`, `>`, `>=` and
`==`, `!=` as non-associative. Show what happens when a user writes
`1 kg < flour < 2 kg`. What error do they see, and when (parse time
or type-check time)? Why did you choose this design over the C-style
left-associative alternative?

**Answer.** Under non-associativity, the parser refuses
`Additive ( CompOp Additive )?` — at most one comparison operator
per production. The user sees a **parse error** at the second `<`:
*"chained comparison not allowed; comparison operators are
non-associative."* This is the earliest possible phase. Under C-style
left-associativity, `1 kg < flour < 2 kg` parses as `(1 kg < flour) < 2 kg`,
which evaluates `1 kg < flour` to a `bool`, then tries to compare
`bool < 2 kg` and hits a **type error at run time** with a confusing
message about comparing `bool` to `Mass`. Trade-off accepted: users
who want transitive chaining write `(1 kg < flour) && (flour < 2 kg)`
explicitly. Reliability and clear error messages over writability.

### Q3. `quantity_of` placement — Sebesta §7.2, decision #34

**Question.** Why is `quantity_of(x)` at the unary level (level 1)
in your precedence ladder, rather than being treated as a function
call at the primary level like `f(x)`?

**Answer.** Its **return type depends on the argument's type-level
structure**: `quantity_of : Ingredient<D> → D`. A function type
signature like `(Ingredient) -> ?` cannot express the dependency on
the operand's dimension field. Placing it at the unary level (a
dedicated grammar production) lets the type rule live in the operator
dispatch, not in a special-cased identifier. It also keeps `quantity_of`
out of the value namespace: it cannot be shadowed by a `let` binding,
cannot be passed as an argument, cannot be assigned. Trade-off: small
loss of syntactic uniformity (looks like a call but isn't one) in
exchange for a cleaner type system.

### Q4. Type equivalence split — Sebesta §6.14, decision #10

**Question.** Sebesta §6.14 typically frames type equivalence as a
one-rule-per-language choice. Recipix uses a split: structural for
`Quantity<D>`, `Ingredient`, and `List<T>`, but **name** equivalence
for `Recipe`. Defend the split. What would break if `Recipe` used
structural equivalence?

**Answer.** Records modeling *data shape* (Ingredient is a transparent
two-tuple; List is parametric; Quantity is a base-unit numeric +
dimension tag) want structural equivalence so two values with the
same shape are the same type — independent of where they were
constructed. Records modeling *identity* (Recipe) want name
equivalence so two recipes sharing a field shape don't accidentally
become interchangeable. If `Recipe` used structural equivalence,
`pancakes` and `crepes` happening to share `{flour, milk, eggs}` would
both type-check as the same `Recipe` type, and `scale(pancakes_value,
by: 2)` would silently substitute under `crepes` if a function
expected a `crepes`-typed argument. Recipe identity carries program
meaning; field shape is a coincidence we don't want the type system
to commit on.

### Q5. Implicit `Ingredient → Quantity` projection — decision #31

**Question.** Inside a step body, `flour + 100 g` type-checks even
though `flour` has type `Ingredient<Mass>` and `100 g` has type
`Mass`. Walk through what the type checker does to make this work,
and name one consequence (good or bad) of the design choice.

**Answer.** When `_check_BinaryOp` sees a `+` between `Ingredient<Mass>`
and `Mass`, it uses a `_dimension_of(t)` helper that returns the
dimension if `t` is either `Quantity<D>` or `Ingredient<D>` (excluding
`Pinch`). Both operands return `Mass`, dimensions match, the result is
typed `Mass`, the BinaryOp node gets `inferred_type = "Mass"`. The
projection happens implicitly — the user never wrote `quantity_of(flour)`.
**Good consequence**: ergonomic — step bodies stay readable
(`flour + 100 g` instead of `quantity_of(flour) + 100 g`).
**Bad consequence**: small loss of type-system uniformity — the
type checker has to special-case `Ingredient` in every arithmetic
and comparison path. **Equivalent explicit form** always exists:
`quantity_of(flour) + 100 g` is identical to `flour + 100 g` per spec §2.

### Q6. Sebesta §6.2 — Pinch as a separate primitive (decision #4)

**Question.** Defend `Pinch` as its own primitive type rather than
making it `Quantity<Pinch>` (i.e. parameterizing the `Quantity<D>`
machinery over `D = Pinch`).

**Answer.** `Pinch` admits **no arithmetic, no comparison, no scaling,
no substitution-by-ratio**. As `Quantity<Pinch>`, every `+`, `-`, `*`,
`/`, `<`, `==`, `scale`, `substitute` operation on `Quantity<D>` would
need a `Pinch` branch in its type rule — a carve-out per operation.
As a separate primitive, the carve-out lives in the type checker's
per-operation entry points (`_check_BinaryOp` rejects Pinch early via
`_reject_pinch`), and the rest of the code never sees `Pinch` outside
two syntactic positions (ingredient declarations and step-action
argument lists). Sebesta §6.2: a primitive type is defined by *the
operations it supports*, not by what it stores. Pinch supports
*ceremonial* operations only — it stays a primitive.

### Q7. Sebesta §7.4 — coercion asymmetry

**Question.** Recipix allows `int → float` widening and within-dimension
unit coercion (g↔kg). It forbids `float → int` even when the value is
representable as an int. Why the asymmetry?

**Answer.** `int → float` is **information-preserving** in the
direction of widening: every 64-bit int up to 2^53 is exactly
representable as IEEE 754 double. Within-dimension unit coercion is
**representation-only** (no information lost — `200 g` and `0.2 kg`
denote the same physical quantity). `float → int` is **narrowing**
and silently lossy — Sebesta §7.4 explicitly flags narrowing coercions
as the dangerous kind. Silent truncation inside `scale` arithmetic
(e.g. `int(servings * 1.5)` vs. `int(round(...))`) would be exactly
the bug a user has the hardest time debugging. Forbidding implicit
narrowing forces an explicit `to_int(x)` (reserved for v2) so the
information loss is visible at the call site.

### Q8. Project-specific: scale-and-loop interaction (sample 1)

**Question.** Open `interpreter.py`'s `_eval_ScaleCall` and `_eval_RecipeCall`.
Sample 1's output shows "pancakes — serves 6" with **six** pour/flip
cycles after `scale(pancakes(servings: 4), by: 1.5)`. Walk through
how the interpreter produces six cycles instead of four.

**Answer.** Recipe instantiation evaluates step bodies eagerly into
an action list, with the original `servings` parameter (4) bound in
the env. The `RtRecipe` value captures the original `step_decls` and
`captured_params` on extra fields specifically so `scale` can re-execute
later. When `_eval_ScaleCall` runs: (1) compute `n' = int(round(4 * 1.5)) = 6`,
(2) scale Mass/Volume/Count ingredients, (3) build a **fresh
evaluation environment** `S_scaled` with `servings` rebound to 6 and
ingredients rebound to scaled values, (4) walk every `step_decl`
again, calling `_exec_step_body` against `S_scaled`. The
`repeat servings times` loop in step 3 reads `servings` from
`S_scaled` (= 6), so the loop body runs six times. Referential
transparency (decision #25) is preserved because `scale` builds a
fresh `RtRecipe` — the original is never mutated; the re-execution
happens inside the new value's construction.

### Q9. Sebesta §9.5 — parameter passing

**Question.** Your decision #16 says parameter passing in Recipix v1
is "semantically by-value." Why does Sebesta §9.5's distinction
between by-value, by-reference, by-result, and by-value-result
*collapse to one mode* in Recipix? What single language change would
make the distinctions observable again?

**Answer.** Sebesta §9.5 distinguishes the four modes by their
**observable effects**: the difference between by-value and
by-reference is whether the callee can mutate something the caller
can see. Recipix has **no mutation operators** — no assignment
statement on existing names (decision #27: `let` only binds, never
re-binds), no compound assignment, no `++`. So even though the
interpreter passes large values (`RtRecipe`, `RtList`) by reference
for efficiency, no callee can *modify* what the caller sees. By-value
and by-reference are indistinguishable at the language level.
**Adding mutation** — a mutable accumulator inside a `repeat`, or a
field-write operator — would make the difference observable, and
decision #16 would be the first rule to revisit (this is named
explicitly in the spec).

### Q10. Cross-chapter: what's in your evaluator that isn't in your spec?

**Question.** Name one design decision that's visible in the
interpreter's behavior but is *not* explicitly locked in spec §12's
35-decision table. How would you defend it if a grader probed it as
an unstated choice?

**Answer.** **Step-body re-execution under scaled servings** (per
D1 §4.4 [P2]). Spec §9 says `scale` "multiplies the servings field by
the scalar" — silent on whether step bodies referring to `servings`
should reflect the scaled value. The interpreter chose to **re-execute
step bodies in a fresh env where servings is rebound**, which makes
sample 1 produce six pour/flip cycles instead of four. Defense: the
user-intuitive reading of `scale` is that doubling a recipe doubles
the work, not just the header. Re-execution preserves referential
transparency (decision #25) — the original `RtRecipe` value is never
mutated; the re-execution happens entirely inside the new value's
construction. This is a v2 candidate for an explicit row in §12,
locking the rule formally.

---

## 6. What to put on your 3 handwritten sheets

**Sheet 1 — Quick reference (everything in §1 above):**
- 35-decision quick-cite list (only your top 10)
- Sebesta Ch. 6 mapping table
- Sebesta Ch. 7 mapping table
- Precedence ladder (7 levels with associativity column)

**Sheet 2 — Mechanics you'll be asked to walk through:**
- `scale` 7-step algorithm
- `substitute` 6-step algorithm
- AmbiguousCall resolution flow
- Implicit Ingredient → Quantity projection rule
- Sample 1's six-cycle output explanation

**Sheet 3 — Defenses (rationale paragraphs in shorthand):**
- Non-associative comparison (why parse-time over type-time)
- Short-circuit L-to-R (matches operand order)
- Operand order locked (reliability over reorder optimization)
- Assignment-as-statement (referential transparency)
- Pinch as primitive (carve-out localization)
- Type equivalence split (shape-vs-identity)
- `quantity_of` at unary (dependent return type)

---

## 7. Test yourself

Before walking into the exam, you should be able to:

1. **Recite the 7-level precedence ladder** from memory, with
   associativity for each level.
2. **Walk through sample 1's output** explaining each ingredient
   line and the six pour/flip cycles cold, in under 90 seconds.
3. **Name 3 Sebesta sections** for each major decision (#10, #17,
   #18, #20, #25, #27, #31, #34).
4. **Cite at least 2 documented AI-was-wrong cases** from your D4
   journal — because the rubric weighs "critical evaluation" and the
   exam may probe how you noticed.
5. **Explain why your spec admits negative quantities** (it does —
   §3 line on unary minus, named as an exception in D1 §4.5). This
   is exam-bait; pre-load the v1-scoped-out / v2-fixable defense.
6. **Defend the `pour(flour: Mass)` accept** under the three-class
   collapse — the "cooking semantics vs type-system parsimony"
   framing from E3.

Good luck. The work is done; the exam is just walking the grader
through what you already built.
