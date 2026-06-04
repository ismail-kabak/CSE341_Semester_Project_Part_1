# Exam 2 — Berk-specific study material

Per handout §3.1 and D6 contribution report, your exam questions
target the components you personally built. This document covers
those components specifically.

**Your owned components:**
- `src/recipix/parser.py` (Part 1 carryover)
- `src/recipix/interpreter.py` (Part 2)
- `src/recipix/rendering.py` (Part 2)
- D1 §4.3 EBNF revisions
- D1 §4.4 Semantics (`scale` + `foreach` operational)
- D1 §4.7 Expressions & Assignment
- D1 §4.8 — four paragraphs (precedence/non-assoc cmp, short-circuit,
  operand order, assignment-as-statement)
- D3 §2 (Sample 1 — pancakes) and §3 (Sample 2 — smoothie)
- Joint with İsmail: `environment.py`, `runtime_values.py`, `errors.py`

---

## PART A — Reading material (your code paths)

### A.1 Interpreter dispatcher pattern

Your interpreter is a **tree-walking evaluator**. The core dispatch
pattern:

```python
def _eval(self, node, env: Environment):
    handler = getattr(self, f"_eval_{type(node).__name__}", None)
    if handler is None:
        raise NotImplementedError(f"No interpreter for {type(node).__name__}")
    return handler(node, env)
```

One method per AST node type. The env chain handles scoping (you don't
re-implement scope rules — `Environment.child()` and `lookup()` do it).

**Key invariant you maintain:** the type checker has already proven
every expression's `.inferred_type`. The interpreter trusts those
annotations. If you see an `AmbiguousCall` at runtime, the type
checker was bypassed — you raise loudly.

### A.2 `_eval_BinaryOp` — what runs for `flour + 100 g`

```
1. Recursively eval left:  flour (Identifier) → env.lookup("flour")
                            → RtIngredient("flour", RtQuantity(200, "Mass"))
2. Recursively eval right: 100 g (QuantityLit)
                            → normalize_to_base(100, "g") = (100, "Mass")
                            → RtQuantity(100, "Mass")
3. Implicit projection (decision #31):
   if left is RtIngredient: left = left.quantity
   (same for right)
   → now both are RtQuantity values
4. Pinch check: if either is RtPinch, raise (#2 territory but at runtime
   the checker already covered this)
5. Op dispatch on "+":
   same dimension → return RtQuantity(left.value + right.value, dim)
   → RtQuantity(300, "Mass")
```

The implicit projection step is *the* Decision #31 mechanic. Memorize
this trace; it's almost certainly an exam question.

### A.3 `_eval_RecipeCall` — recipe instantiation

```
1. Look up the recipe declaration in self.globals
2. Create a child env: recipe_env = self.globals.child()
3. Bind kwargs into recipe_env (servings: 4 → recipe_env["servings"] = 4)
4. Evaluate the `serves <expr>` to a Python int
5. Evaluate each ingredient declaration:
   a. Eval the expression (e.g. 50 g * servings = 50*4 = 200 g)
   b. Build RtIngredient(name, quantity)
   c. recipe_env.define(name, RtIngredient) so step bodies can see it
6. Eager-evaluate step bodies into action lists:
   for each step_decl:
     evaluate at/for modifiers
     accumulate actions = []
     run _exec_step_body(step_decl.body, recipe_env, actions)
     append {description, at, for, actions} to steps
7. Snapshot captured_params = {p.name: recipe_env.lookup(p.name)
                                 for p in decl.params}
   → keeps the original parameter values for scale's re-execution
8. Return RtRecipe(name, servings_value, ingredients_dict, steps,
                    step_decls=decl.steps, captured_params)
```

Steps 7 and 8 are the **captured_params + step_decls** mechanism that
makes scale's re-execution rule work. Without these fields, scale
couldn't rebind `servings` and re-execute the body.

### A.4 `_eval_ScaleCall` — the 7-step algorithm

```
1. Eval r → must produce RtRecipe (the type checker proved it)
2. Eval k → must be int/float; if k ≤ 0 → RuntimeRecipixError
3. n' = int(round(n * k))                ← banker's rounding (plan §2.6)
4. Scale ingredients:
   for (id, ing) in r.ingredients.items():
     if ing.quantity is RtPinch:           → unchanged
     elif ing.quantity.dimension in {Mass, Volume, Count}:
       new_q = RtQuantity(ing.quantity.value * k, ing.quantity.dimension)
       new_ings[id] = RtIngredient(ing.name, new_q)
     elif ing.quantity.dimension in {Temperature, Duration}:
       new_ings[id] = ing            ← intensive quantities unchanged
5. Build fresh scaled_env from self.globals.child():
   for (p, v) in r.captured_params.items():
     if v == r.servings (i.e. it was the original servings value):
       scaled_env.define(p, n')
     else:
       scaled_env.define(p, v)
   for (id, scaled_ing) in new_ings.items():
     scaled_env.define(id, scaled_ing)
6. Re-execute each step_decl against scaled_env:
   new_steps = []
   for step_decl in r.step_decls:
     actions = []
     evaluate at/for modifiers under scaled_env
     _exec_step_body(step_decl.body, scaled_env, actions)
     new_steps.append({description, at, for, actions})
7. Return fresh RtRecipe(name, n', new_ings, new_steps, step_decls,
                          captured_params)
```

**Why fresh RtRecipe?** Decision #25 (functional `scale`). The
original recipe value is never mutated. Referential transparency
preserved.

### A.5 `_eval_SubstituteCall` — pop-on-consume

```
1. Eval the recipe expression (the substitute target)
2. Look up x and y in the recipe's ingredient table via bare IDENT
   (decision #35 makes these grammar-level identifiers, not exprs)
3. orig = r.ingredients[x]
4. new_q = RtQuantity(orig.quantity.value * ratio, orig.quantity.dimension)
5. new_ings = dict(r.ingredients)
6. new_ings[x] = RtIngredient(name=y, quantity=new_q)   ← relabel slot
7. if y != x:
       new_ings.pop(y)                                 ← consume replacement
   (this is the line that makes sample 2's vegan variant show only
    one oat_milk line — the standalone oat_milk gets removed because
    it's "consumed" into the substituted slot)
8. Return fresh RtRecipe(r.name, r.servings, new_ings, r.steps, ...)
```

**Note:** step bodies are NOT re-executed for substitute (unlike scale).
Why? The step `combine(milk, banana, sweetener)` in sample 2 still
shows up as `combine(oat_milk, banana, sweetener)` in the substituted
output because **the actions stored in `steps` reference ingredient
*labels* via the recipe's ingredient binding table**. When the binding
table changes, the rendered output reflects the new labels — no
re-execution needed.

### A.6 Rendering heuristic (`rendering.py`)

Your `render_quantity` function decides how to display a normalized
base-unit value:

```
def render_quantity(q: RtQuantity) -> str:
    v, d = q.value, q.dimension
    if d == "Mass":
        if v >= 1000: return f"{v/1000:g} kg"
        else:         return f"{v:g} g"
    if d == "Volume":
        if v >= 1000: return f"{v/1000:g} l"
        else:         return f"{v:g} ml"
    if d == "Count":
        return f"{int(v) if v == int(v) else v:g}"
    if d == "Temperature":
        return f"{v:g} °C"
    if d == "Duration":
        if v >= 60: return f"{v/60:g} hr"
        else:       return f"{v:g} min"
```

**Why the thresholds?** Cookbook readability. `300 g` reads fine; once
you cross 1000 g a reader expects `1.5 kg`. Same for `360 ml` vs
`1.2 l` and `45 min` vs `1.5 hr`. The boundary is the smallest sensible
unit for that dimension. **Pinch** renders as `"a pinch"`.

**Why `:g` format?** It drops trailing zeros: `300.0 g` → `300 g`,
`1.5 kg` → `1.5 kg`. Avoids `300.000000 g` ugliness.

### A.7 Parser carryover — your Part-1 decisions

These are still your responsibility on the exam. The parser enforces:

- **#7 quantity literals as two tokens** (`_parse_primary`): after
  `INT_LIT`/`FLOAT_LIT`, peek for `UNIT_KW`. If present, consume
  both into a `QuantityLit` AST node. If not, just a numeric literal.
- **#17 non-associative comparison** (`_parse_eq` / `_parse_rel`):
  after consuming one comparison op and its right operand, check for
  a second comparison. If found, raise `ParseError`. This is what
  makes `a < b < c` a parse error.
- **#20 mandatory braces on if/else** (`_parse_if_stmt`): both branches
  call `_expect(LBRACE, ...)`. Eliminates dangling-else.
- **#23 fixed step-modifier order** (`_parse_step_decl`): consume
  optional `at`, then optional `for`. If `at` appears after `for`,
  explicit error.
- **#34 `quantity_of` at unary level** (`_parse_unary`): dedicated
  branch that consumes `quantity_of`, `(`, expression, `)`. Never
  reaches `_parse_primary` (which would treat it as a function call).
- **#35 substitute slots as bare IDENT** (`_parse_substitute_call`):
  after the recipe expression, expect `IDENT` (not `_parse_expr`).
  Same for the `with: IDENT` slot. Anything else is a parse error
  at the unexpected token.

### A.8 D1 §4.4 — your operational semantics for `scale` and `foreach`

Already in the cheat sheet (Sheet 2). The key things to remember:
- Big-step style (Sebesta §3.5)
- State `S` = environment mapping names to values
- `<expr, S> → value` for expressions
- `<stmt, S> → S'` for statements
- Side conditions on premises (e.g. `k > 0` for scale)
- `scale` has the *fresh env + re-execution* rule on the step bodies
- `foreach` has the *bind/execute/unbind* per-iteration rule with
  side conditions about empty lists and shadowing

### A.9 D1 §4.7 — your four exam-likely paragraphs

Your §4.8 contributions cover four design decisions. Their compressed
defenses are on the cheat sheet (§3.1 in Part 2 of the main notes).
The four paragraphs:

1. **Precedence ladder + non-associative comparison (#17)** — why
   non-assoc beats left-assoc.
2. **Short-circuit `&&` / `||` (#19)** — why left-to-right, why
   short-circuit at all.
3. **Operand evaluation order locked (#18)** — why "fully defined"
   beats C's "unspecified".
4. **Assignment as statement (#27)** — why `let` only, no
   assignment-as-expression.

---

## PART B — Berk-specific exam questions (10 with worked answers)

These drill into *your* code, not just the general language design.

### BQ1. Walk through `_eval_BinaryOp` for `flour + 100 g` inside a step body.

**Answer.**
1. Recursively eval the left operand: `flour` is an `Identifier` node.
   `_eval_Identifier` calls `env.lookup("flour")` which walks the
   env-chain up to the recipe scope and returns
   `RtIngredient("flour", RtQuantity(200.0, "Mass"))`.
2. Recursively eval the right: `100 g` is a `QuantityLit`.
   `_eval_QuantityLit` calls `normalize_to_base(100, "g")` which
   returns `(100.0, "Mass")`. Wrap in `RtQuantity(100.0, "Mass")`.
3. **Implicit Ingredient → Quantity projection (decision #31)**:
   if either operand is an `RtIngredient`, replace it with its
   `.quantity` field. Left becomes `RtQuantity(200.0, "Mass")`.
4. Pinch guard: neither operand is `RtPinch`. Continue.
5. Both have dimension `"Mass"` and the operator is `"+"`.
   `200.0 + 100.0 = 300.0`. Return `RtQuantity(300.0, "Mass")`.

The implicit projection is what lets users write
`flour + 100 g` instead of `quantity_of(flour) + 100 g`. Without it,
the interpreter would refuse to add an `Ingredient` to a `Quantity`.

### BQ2. Why does your interpreter handle `return` using an exception?

**Answer.** Recipix functions have a single top-level `return` at the
end of the body (spec §7), but parser-level the `return` statement can
appear anywhere inside nested blocks. To unwind out of arbitrarily
nested `if` / `repeat` / `foreach` blocks back to the function call
site, the interpreter raises a `ReturnException` carrying the return
value when it executes `ReturnStmt`. `_eval_FunctionCall` catches it,
returns the carried value as the call's result, and the unwinding
discards all the intermediate stack frames. Without exceptions you'd
need every loop and conditional to thread a "did we return?" boolean
back up.

### BQ3. Walk through `_eval_ScaleCall` step by step on `scale(pancakes(servings:4), by: 1.5)`.

**Answer.**
1. Evaluate `pancakes(servings: 4)` first (operand-order #18). This
   returns an `RtRecipe(servings=4, ingredients={...}, steps=[4-cycle
   pour/flip], step_decls=[...], captured_params={"servings": 4})`.
2. Evaluate `1.5` → 1.5 (float). It's > 0, no runtime error.
3. Compute `n' = int(round(4 * 1.5)) = 6`. Banker's rounding.
4. Build new ingredients:
   - flour `200 g` → `300 g` (Mass scales)
   - milk `240 ml` → `360 ml` (Volume scales)
   - eggs `2 count` → `3 count` (Count scales; `int(round(2 * 1.5)) = 3`)
   - salt `Pinch` → unchanged
5. Build `scaled_env = self.globals.child()`. Rebind
   `servings → 6` (because the captured param's value was 4, the
   original servings). Define all scaled ingredients in `scaled_env`.
6. Re-execute each step body against `scaled_env`. Step 3's
   `repeat servings times { pour(milk); flip() }` now reads
   `servings = 6` and unrolls into **six** pour/flip cycles.
7. Return a fresh `RtRecipe(servings=6, scaled ingredients, 6-cycle
   step actions, original step_decls, original captured_params)`.

The original recipe value from step 1 is never mutated — referential
transparency preserved (decision #25).

### BQ4. Why does Sample 2's non-vegan variant show both `milk` AND `oat_milk` while the vegan variant only shows `oat_milk`?

**Answer.** The vegan variant runs `substitute(smoothie(servings: 2),
milk, with: oat_milk, ratio: 1.0)`. My `_eval_SubstituteCall`:
1. Looks up `milk` and `oat_milk` in the recipe's ingredient table.
2. Computes the new quantity (`150 ml * 2 * 1.0 = 300 ml`).
3. Relabels the `milk` slot to use the name `oat_milk`.
4. **Pops the standalone `oat_milk` binding** (`new_ings.pop("oat_milk")`)
   because the replacement was consumed into the substituted slot.

So the rendered output shows one `oat_milk: 300 ml` line.

The non-vegan variant just runs `smoothie(servings: 2)` with no
substitute. The recipe declares `oat_milk` as a pre-declared
alternative so that any call-site `substitute` can reference it by
bare IDENT (decision #28 + #35). When no substitution happens, the
pre-declared alternative just sits there. So both `milk: 300 ml` and
`oat_milk: 300 ml` appear. This is the **no-`this`** design
(decision #25): a recipe can't reference itself during construction,
so alternative ingredients must be in scope at the call site, which
means they have to live inside the recipe body.

### BQ5. Sample 1 renders six `pour(milk) / flip()` cycles even though the recipe is instantiated with `servings = 4`. Walk through how the interpreter produces six iterations.

**Answer.**
1. `pancakes(servings: 4)` instantiates with `servings = 4` bound in
   the recipe env. Step body 3 (`repeat servings times { pour; flip }`)
   evaluates eagerly into an action list of 4 `pour/flip` pairs at
   instantiation time.
2. The returned `RtRecipe` captures `step_decls` (the raw AST nodes)
   and `captured_params` (`{"servings": 4}`) — these survive into the
   scaled recipe.
3. `_eval_ScaleCall` then builds a fresh `scaled_env` where
   `servings → 6`, and **re-executes** each step body against
   `scaled_env`. The `repeat servings times` loop in step 3 reads
   `servings = 6` and produces six iterations.
4. The fresh `RtRecipe` returned from `scale` has the 6-cycle step
   body, not the original 4-cycle one. The original value is never
   mutated — referential transparency (decision #25) preserved
   because the re-execution happens entirely inside the new recipe
   value's construction.

### BQ6. Your `render_quantity` uses 1000 as the threshold for `g → kg` and `ml → l`, and 60 for `min → hr`. Why those thresholds?

**Answer.** Cookbook readability. The threshold is chosen so the
displayed unit reads naturally to a human user:
- `200 g` reads cleaner than `0.2 kg` — keep in grams.
- `1500 g` reads worse than `1.5 kg` — switch to kg at the boundary
  where the larger unit becomes more readable.
- 1000 is the natural SI prefix boundary for mass and volume; 60 is
  the natural boundary for duration (minutes → hours).
- `Count` and `Temperature` have no smaller unit, so no threshold —
  render as-is.

This is a rendering choice, not a semantic one — internally
quantities are always stored in the base unit (`g`, `ml`, `min`, etc.)
so all arithmetic is consistent. The rendering heuristic only affects
the *display*.

### BQ7. Show in your parser source where decision #17 (non-associative comparison) is enforced. What error message does the user see?

**Answer.** In `parser.py`, both `_parse_eq` and `_parse_rel` use a
"consume one, check for second" pattern:

```python
def _parse_rel(self):
    left = self._parse_add()
    if self._check(LT, LTE, GT, GTE):
        op_tok = self._advance()
        right = self._parse_add()
        # Check for chained comparison
        if self._check(LT, LTE, GT, GTE):
            raise ParseError(
                self._line(), 0,
                "chained comparison not allowed; "
                "comparison operators are non-associative"
            )
        return CompareOp(op_tok.value, left, right, op_tok.line)
    return left
```

The user sees something like:
`parse error at line N, col 0: chained comparison not allowed;
comparison operators are non-associative`

This catches `1 kg < flour < 2 kg` at parse time, before any type
checking. Under left-associative parsing, the bug would only surface
at runtime as a confusing "cannot compare bool to Mass" type error.

### BQ8. Defend decision #18 (operand evaluation order is fully defined left-to-right) over C's "unspecified" rule.

**Answer.** C/C++ leaves operand evaluation order **unspecified** so
compilers can reorder operands for optimization. This means the same
program can produce different runtime errors on different platforms.
For a DSL aimed at reliability (Recipix §1.3 prioritization), this is
hostile: a student running `let x : int = f(a/0) + g(b/0)` could see
the division-by-zero come from `a/0` on one compiler and `b/0` on
another, with the error message citing different line numbers each
time. **Reliability and predictable error reporting** matter more than
operand-reorder optimization for v1 — and "cost" was already
deprioritized in §1's evaluation-criteria framing.

Recipix locks left-to-right. Because Recipix has no side-effecting
expressions (#16 no mutation, #27 assignment-as-statement), the order
is **unobservable on values** — the same expression evaluates to the
same result regardless. The order is only observable in **which
runtime error fires first**. Locking left-to-right guarantees error
messages cite predictable line numbers.

### BQ9. Your `_exec_step_body` is structured differently from your `_exec_stmt`. Why does that function exist separately?

**Answer.** Step bodies need to **accumulate action records** into a
list that becomes part of the resulting `RtRecipe.steps`. Ordinary
statement execution (`_exec_stmt`) just runs statements for their
effect on the env and returns nothing. The two control paths diverge:

- `_exec_stmt` routes `ActionStmt` nodes to a no-op (or in the
  loud-fail version, raises — because action verbs shouldn't appear
  outside step bodies).
- `_exec_step_body` walks the body specifically looking for
  `ActionStmt` nodes and packaging them into action records like
  `{"verb": "pour", "args": [...]}` which then get appended to the
  step's actions list.

The two paths share `LetStmt`, `IfStmt`, `RepeatStmt`, `ForeachStmt`
execution — those just delegate to standard control-flow handlers —
but the leaf-level treatment of action verbs differs. `_exec_step_body`
is essentially a partial-evaluator that walks the body and produces a
render plan; `_exec_stmt` is a regular statement executor.

### BQ10. Defense paragraph (in your own voice) for assignment-as-statement (decision #27).

**Answer (paragraph form, exam-ready):**

> Decision #27 was a deliberate import from functional-language
> discipline: with `let` as the only binding form and assignment as a
> statement, every expression in Recipix is **referentially
> transparent**. Same expression in the same scope produces the same
> value, every time. The trade-off is that some patterns require
> slightly more code — there is no `while ((line = read()) != null)`
> form, because `=` is not an expression. I accepted this because
> (a) v1 has no mutation and no I/O loop, so the missing pattern
> doesn't arise in real Recipix programs, and (b) it lets decision
> #18's left-to-right evaluation order be entirely unobservable on
> values, which simplifies the operational semantics in D1 §4.4 —
> every rule for binary operators can ignore the question "what if
> the left operand modified something the right operand reads?"
> because no operand can modify anything. The cost is a v1-only
> restriction; if Recipix v2 introduces mutation (a mutable
> accumulator inside `repeat`, for example), assignment-as-statement
> is the first rule that should be revisited.

---

## PART C — Quick-reference for Berk-specific gotchas

```
INTERPRETER ARCHITECTURE
  • Tree-walking dispatcher: getattr(self, f"_eval_{NodeType}", None)
  • Env chain: type-agnostic Environment, define/lookup/child
  • Loud-raise on AmbiguousCall (no silent fallback per PM-review)

KEY DATACLASSES (runtime_values.py)
  RtQuantity(value:float, dimension:str)    # always base unit
  RtPinch (singleton: PINCH)
  RtIngredient(name:str, quantity)
  RtRecipe(name, servings, ingredients, steps,
           step_decls, captured_params)     # last 2 for scale re-exec
  RtList(elements, element_type)

YOUR §4.7 PARAGRAPHS — what's defended
  Precedence + non-assoc cmp: parse-time catch > runtime type err
  Short-circuit: standard expectation; matches operand order
  Operand order locked: predictable error reporting
  Assignment as statement: every expr ref-transparent in v1

SAMPLE 1 KEY NUMBER: 6 cycles (not 4)
  Because scale re-executes step bodies under S_scaled

SAMPLE 2 KEY DETAIL: vegan shows 1 oat_milk; non-vegan shows 2
  Because substitute POPS the standalone replacement binding

PARSER #-DECISIONS YOU OWN ENFORCEMENT OF
  #7  quantity literal lookahead in _parse_primary
  #17 non-assoc check in _parse_eq / _parse_rel
  #20 mandatory braces in _parse_if_stmt
  #23 at-before-for in _parse_step_decl
  #34 dedicated unary production for quantity_of
  #35 IDENT slot guard in _parse_substitute_call
```

Good luck. You built this — explain what you built and you'll do
fine.
