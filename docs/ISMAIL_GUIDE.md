# İsmail's Build Guide — Recipix Part 2 Type Checker

**Companion to** `part2_plan.md` (the signed-off joint contract).
**Owner:** İsmail Kabak (1901042652).
**Module:** `src/recipix/typechecker.py`.
**Submission:** Friday, 22 May 2026, 23:59.

This guide is your runway for sitting down and writing the type checker.
It does not replace `part2_plan.md` — that's the contract with Berk and
the spec. This document is **your view of the contract**: what's already
been built, what your dispatch surface looks like, and the order to fill
in the stubs so the integration tests light up green one by one.

Read `part2_plan.md` §1–§2.8, §5, §10 first if you haven't. Then come
back here.

---

## 1. Where everything stands right now

As of HEAD (`d5c539c`), Berk's interpreter and rendering layer are
**done and tested.** The current test count is 152 with two expected
failures (`pl03_scale_in_ingredient`, `pl06_scale_in_step_expr` — those
are the type-checker-deferred regression fixtures that *you* will turn
green). Run this to confirm:

```bash
python -m unittest discover src/tests
# Expect: Ran 152 tests in <1s — FAILED (failures=2)
```

Sample 1 and Sample 2 already render cookbook-style output through the
interpreter — but only via a test helper that simulates the
`AmbiguousCall → FunctionCall/RecipeCall` resolution your checker will
do for real. The CLI `--run` flag currently raises
`NotImplementedError` because `recipix.typechecker.check` is still a
stub. **The moment your `check()` returns a program, `--run` will
start working end-to-end** with no changes needed in Berk's interpreter
or `__main__.py`. That is the goal post.

What's already implemented for you to build on:

| Module | Status | What it gives you |
|---|---|---|
| `src/recipix/runtime_values.py` | ✅ done | `RtQuantity`, `RtIngredient`, `RtRecipe`, `RtList`, `BASE_UNIT`, `normalize_to_base()` — you don't need any of these in the checker, but knowing they exist is useful for the exam |
| `src/recipix/environment.py` | ✅ done | `Environment` class with `define`, `lookup`, `declare_check`, `has_local`, `has_visible`, `child` — **use it**, don't reinvent |
| `src/recipix/errors.py` | ✅ done | `TypeCheckError(line, col, message, error_code=None)`, `RedeclarationError`, `ShadowingError` — the wrap-and-re-raise pattern is laid out below |
| `src/recipix/interpreter.py` | ✅ done | 619 lines, 36 tests passing, runs samples 1+2 end-to-end. Assumes you'll resolve `AmbiguousCall` before handing the program to it. |
| `src/recipix/typechecker.py` | ◯ stubs | 221 lines, 33 `NotImplementedError`. **Your starting point.** Dispatch table fully laid out — one `_check_NodeType` method per AST node type. |

What you must NOT touch:

- `lexer.py`, `parser.py`, `ast_nodes.py`, `tokens.py`, `pretty.py` — locked Part 1 contracts.
- `interpreter.py`, `rendering.py` — Berk's modules. If a bug there blocks you, file an issue in chat; don't edit.
- `part2_plan.md` — signed-off contract. If you need to deviate, talk to Berk first.

---

## 2. Your dispatch surface — what's already laid out

`src/recipix/typechecker.py` already contains the full `TypeChecker`
class with one `_check_<NodeType>` method per AST node, each currently
`raise NotImplementedError`. Your job is to fill them in. Methods grouped
by phase:

**Top-level structure (visit first — most other methods depend on
symbol tables built here):**

```
_check_Program          # build top-level symbol table (recipes + functions)
_check_RecipeDecl       # open scope, bind params, walk ingredients + steps
_check_FunctionDecl     # open scope, bind params, walk body, enforce single-return
_check_Param            # type-string validation
```

**Declarations inside recipe / function bodies:**

```
_check_IngredientDecl   # bind ingredient name + dimension
_check_StepDecl         # validate at/for modifiers, walk action statements
_check_LetStmt          # declare_check → define; check expr type matches annotation
_check_ActionStmt       # action-verb signature check (§2.3 three-class table)
```

**Control flow:**

```
_check_IfStmt           # condition must be bool
_check_RepeatStmt       # count must be int
_check_ForeachStmt      # iterable must be List<T>; bind loop var as T
_check_ReturnStmt       # only inside function bodies (parser already restricts this)
_check_EvalStmt         # set in_evaluate=True, walk expr
```

**Expressions (annotate `.inferred_type` on each):**

```
_check_BinaryOp         # numeric / quantity arithmetic per spec §3
_check_CompareOp        # non-associative; same-dimension only
_check_UnaryOp          # '-' on int/float/Quantity; '!' on bool
_check_QuantityOf       # operand must be Ingredient; returns its dimension
_check_SubstituteCall   # ingredient lookup, dimension match, evaluate-only
_check_ScaleCall        # recipe expr, scalar by, evaluate-only
_check_FunctionCall     # arity + arg types
_check_AmbiguousCall    # ★ critical: resolve to FunctionCall or RecipeCall by name lookup
_check_RecipeCall       # kwargs match recipe params
_check_KwArg            # used by RecipeCall
_check_Identifier       # env.lookup → type
_check_IntLit, _check_FloatLit, _check_BoolLit, _check_StringLit
_check_QuantityLit      # number + unit → Quantity<dimension>
_check_ListLit          # homogeneous; share one dimension if Quantity
```

You annotate each Expr node's `.inferred_type` in place (plan §2.1) —
that's the contract with Berk's interpreter, even though the interpreter
currently doesn't read the annotation for anything except
`AmbiguousCall` resolution.

---

## 3. THE FIRST 90 MINUTES — critical handoff path

The single most important thing in your half of Part 2 is **resolving
`AmbiguousCall`**. Without it, the CLI `--run` flag cannot work, and
Berk's tests currently use a helper to simulate your work. Ship this
first, push it, tell Berk.

### Step 1 — Symbol table (30 min)

`_check_Program` walks `program.items` and builds two name-keyed
tables:

```python
self.recipes = {}   # name → RecipeDecl
self.functions = {} # name → FunctionDecl
```

Single-pass; recipes and functions can refer to each other regardless
of declaration order. Raise `TypeCheckError(error_code=4)` ("unknown
identifier") if a call later references a name not in either table.

Tip: store the declarations themselves, not just their signatures —
you'll need the param list for `FunctionCall`/`RecipeCall` argument
type checking.

### Step 2 — Resolve `AmbiguousCall` in place (30 min)

Per plan §2.1, your checker **mutates the AST** to rewrite each
`AmbiguousCall` into either a `FunctionCall` (with `args=[]`) or a
`RecipeCall` (with `kwargs=[]`). The rule is name-table lookup:

```python
def _check_AmbiguousCall(self, node):
    if node.name in self.functions:
        return FunctionCall(name=node.name, args=[], line=node.line)
    if node.name in self.recipes:
        return RecipeCall(name=node.name, kwargs=[], line=node.line)
    raise TypeCheckError(
        node.line, 0,
        f"unknown identifier {node.name!r} (not a function or recipe)",
        error_code=4,
    )
```

But that's not quite enough — the *containing* node has a reference to
the old `AmbiguousCall`, and you have to update it. Either:

- Return the rewritten node from every `_check_*` method and have the
  parent reassign the field, or
- Walk the tree with a generic mutator that does the swap when it sees
  the wrapper field.

Look at how `tests/test_interpreter.py::_resolve_ambiguous_calls`
already does this for the integration tests — you can crib the
walking strategy. The semantics are exactly what your checker
produces; you're just replacing the helper.

### Step 3 — Make `check()` round-trip end-to-end (30 min)

Make `check(program)` walk the whole tree (even if most methods are
still stubs) and successfully return for sample 1 and sample 2. Don't
worry yet about getting the type rules right — just make the walker
work without crashing.

Once these three steps are done:

```bash
python main.py --typecheck src/tests/fixtures/valid/sample1.rcx
# expect: OK — type-checked

python main.py --run src/tests/fixtures/valid/sample1.rcx
# expect: the rendered cookbook output that the interpreter now produces
```

**That's your first commit.** Push it, ping Berk on chat. From that
point on you and Berk are no longer blocked on each other for
anything.

---

## 4. The 19 errors from spec §10 (+ #19 from plan §2.6)

Each of these must fire on at least one test in
`src/tests/test_typechecker.py` (which you create). The check exists,
the test pins it, and the D3 PDF gets one of these as its type-error
demonstration program.

| # | Error | Where to raise it |
|---|---|---|
| 1 | Dimension mismatch in arithmetic | `_check_BinaryOp`, `_check_CompareOp` |
| 2 | Pinch in arithmetic / comparison / scaling | `_check_BinaryOp`, `_check_CompareOp`, `_check_ScaleCall`, `_check_SubstituteCall` |
| 3 | Heterogeneous list literal | `_check_ListLit` |
| 4 | Unknown identifier | `_check_Identifier`, `_check_AmbiguousCall`, `_check_FunctionCall`, `_check_RecipeCall` |
| 5 | Single-assignment violation | wrap `Environment.define` → `RedeclarationError` → re-raise |
| 6 | Shadowing | wrap `Environment.declare_check` → `ShadowingError` → re-raise |
| 7 | `if` condition not bool | `_check_IfStmt` |
| 8 | `repeat` count not int | `_check_RepeatStmt` |
| 9 | `foreach` source not a list | `_check_ForeachStmt` |
| 10 | `at` modifier not Temperature | `_check_StepDecl` |
| 11 | `for` modifier not Duration | `_check_StepDecl` |
| 12 | Wrong arity in call | `_check_FunctionCall`, `_check_RecipeCall` |
| 13 | Wrong arg types in call | `_check_FunctionCall`, `_check_RecipeCall`, `_check_ActionStmt` |
| 14 | Unknown ingredient in `substitute` | `_check_SubstituteCall` |
| 15 | Implicit `float → int` coercion | `_check_BinaryOp`, `_check_LetStmt` |
| 16 | Substitute between Pinch and Quantity | `_check_SubstituteCall` |
| 17 | Non-IDENT in `substitute` slot | already caught by parser; double-check parser produces `SubstituteCall` only with str fields |
| 18 | `quantity_of` on non-Ingredient | `_check_QuantityOf` |
| **19** | **`return` not last statement of function body** | `_check_FunctionDecl` — pre-walk `body[:-1]` for any `ReturnStmt` (also descend into nested `if`/`repeat`/`foreach` blocks); error if found, or if `body[-1]` is not `ReturnStmt` |

**Priority order** (so Berk's integration tests stop being blocked first):

- Tier 1 (must work for sample programs to type-check): #1, #4, #12, #13, #17 (verify parser invariant), plus the `evaluate`-only constraint on `scale`/`substitute` per plan §5 task 4
- Tier 2 (exam-defensibility): #2, #5, #6, #18, #19
- Tier 3 (polish before submission): #3, #7–#11, #15, #16, #14

---

## 5. The wrap-and-re-raise pattern (read once, use everywhere)

`Environment.define()` and `declare_check()` raise their own specific
exceptions. Your checker should never let those reach the user as a
Python traceback. Wrap them every time:

```python
from .errors import (
    TypeCheckError, RedeclarationError, ShadowingError,
)

def _check_LetStmt(self, node):
    # ... validate type annotation matches expr type ...
    try:
        self.env.declare_check(node.name)
    except ShadowingError:
        raise TypeCheckError(
            node.line, 0,
            f"let binding {node.name!r} shadows an existing name",
            error_code=6,
        )
    try:
        self.env.define(node.name, node.type_name)
    except RedeclarationError:
        # shouldn't happen because declare_check already passed,
        # but kept defensively
        raise TypeCheckError(
            node.line, 0,
            f"let binding {node.name!r} is already declared",
            error_code=5,
        )
```

The exact same pattern applies to `IngredientDecl`, `Param`,
`ForeachStmt` (loop variable), and function/recipe parameter binding.
Consider writing a `self._declare(name, type_str, line)` helper on the
class so you don't repeat the try/except eight times.

**Special-case for parameter lists** (plan §2.5 scope convention):
recipe and function parameters live in the **same scope as the body**,
not a separate parameter scope. So when you `_check_FunctionDecl`:

```python
self.env = self.env.child()           # open new scope
for p in node.params:
    self._declare(p.name, p.type_name, p.line)   # into the body scope
# walk body in self.env
self.env = self.env.parent            # close scope
```

A `let x : int = 1` inside `function f(x: int)` then correctly fails
with `ShadowingError`.

---

## 6. Decision #31 — implicit Ingredient → Quantity projection

This is the highest-risk type rule because it crosscuts every
arithmetic and comparison operator. The spec says (paraphrasing): when
an `Ingredient` appears in a context that expects `Quantity<D>` —
inside `BinaryOp`, `CompareOp`, `_check_SubstituteCall`'s ratio — it
implicitly projects to its `quantity` field.

Implementation tip: rather than coding the projection at every
operator, write a `self._quantity_type_of(expr_node)` helper that
returns the dimension if `expr_node` is `Ingredient` or
`Quantity<D>`, and `None` otherwise. Then `_check_BinaryOp` for `+`
becomes:

```python
ld = self._quantity_type_of(node.left)
rd = self._quantity_type_of(node.right)
if ld and rd:
    if ld != rd:
        raise TypeCheckError(
            node.line, 0,
            f"cannot add {ld} and {rd} (dimension mismatch)",
            error_code=1,
        )
    node.inferred_type = ld
    return ld
# fall through to numeric rules
```

Pinch must be rejected explicitly. Berk's interpreter already
implements the projection at run-time, so the checker just needs to
prove it's safe. Three tests already exist in
`TestImplicitIngredientProjection` — your checker has to make them all
type-check too.

---

## 7. Action verb signature enforcement (plan §2.3)

The three-class table is the source of truth:

| Class | Verbs | Rule |
|---|---|---|
| **Heterogeneous** | `combine`, `mix`, `add`, `sprinkle` | ≥1 arg; each arg is `Ingredient` or `Quantity` of any dimension (including `Pinch`) |
| **Homogeneous** | `pour`, `drizzle`, `whisk`, `blend`, `knead`, `melt` | ≥1 arg; all args share one dimension; `Pinch` forbidden |
| **Nullary** | `bake`, `flip` | 0 args |

Code shape: one `ACTION_VERB_CLASS = {verb: "het"/"hom"/"nul"}` dict in
the module, one method that dispatches. Five lines of dispatch + the
per-class rule. Don't over-engineer it.

---

## 8. `evaluate`-only constraint on `scale` and `substitute`

Per plan §5 task 4: `scale` and `substitute` may appear **anywhere in
an expression rooted at an `EvalStmt`**, but not inside a `recipe`
body, a `function` body, or a `let` initializer outside an `EvalStmt`.

Implementation: carry a boolean `self.in_evaluate` flag on the
`TypeChecker` instance, default `False`. Set `True` when entering
`_check_EvalStmt(node.expr)`, restore `False` on the way out. In
`_check_ScaleCall` and `_check_SubstituteCall`, if `not
self.in_evaluate`, raise `TypeCheckError` (no specific error_code in
spec §10 — use `error_code=None` and a clear message; this rule lives
in §9 of the spec).

The two failing regression tests (`pl03`, `pl06`) are exactly this
rule. Once you implement it correctly, both turn green and your test
count goes 152 → 154.

---

## 9. Verifying you're done

The acceptance test is the four-command sequence below. When all four
behave as marked, your type checker is complete enough to ship D2.

```bash
# 1. Full test suite green (your tests + Berk's tests + regression).
python -m unittest discover src/tests
# Expect: Ran ~180+ tests, OK (0 failures, 0 errors).
# The pl03 / pl06 regression failures should now PASS.

# 2. Sample 1 type-checks and runs end-to-end through the CLI.
python main.py --run src/tests/fixtures/valid/sample1.rcx
# Expect: the cookbook output the interpreter already produces.

# 3. Sample 2 likewise (both variants).
python main.py --run src/tests/fixtures/valid/sample2.rcx
# Expect: vegan smoothie + non-vegan smoothie.

# 4. Sample 3 type-checks and FAILS with a clear dimension-mismatch
# error message at the let line (this is the D3 type-error trace).
python main.py --typecheck src/tests/fixtures/valid/sample3.rcx
# Expect: type error at line N, col M: cannot add Mass and Volume ...
```

---

## 10. Exam preparation — what you specifically own

The 28 May exam will personalize questions to your half of Part 2 (per
the handout). Be ready to defend:

- **Sebesta Ch. 6 (types):** strong typing decision (#8), structural
  vs name equivalence split (#10) — be able to explain *why*
  structural for `Quantity<D>`/`Ingredient`/`List<T>` and *why* name
  for `Recipe`; coercion rules (#9, within-dimension unit + int→float
  but never the other way); implicit `Ingredient → Quantity`
  projection (#31).
- **Sebesta Ch. 5 (scope, binding):** static lexical scoping (#11),
  no-shadowing (#12), single-assignment (#13), the parameter-scope
  convention from plan §2.5.
- **The 19 errors:** for any one I pick, you should be able to name
  the spec section, the AST node where it fires, and (ideally) what
  alternative design would have made it unnecessary.
- **Decision #4 (Pinch as its own primitive, not `Quantity<Pinch>`):**
  why this is better than overloading the Quantity machinery — exam
  loves "why didn't you do the obvious thing" questions.

The plan's §1 footer says explicitly: both partners get Ch. 6 + Ch. 7
questions, not split. Don't skip Ch. 7 prep (Berk's territory) — short-
circuit, operand order, assignment-as-statement. You'll get questions
on them.

---

## 11. Daily journal reminder

You also owe **6 more D4 entries dated 9–22 May**, on top of your
Part 1 journal. The mandatory experiments for Part 2 are E2 (name vs
structural equivalence) and E3 (AI implements your type checker).
Both are explicitly per-student — see plan §9 for the fragment split.

Log your day's session before you go to bed. Real dates. The handout
treats backfilled D4 entries as zero credit.

---

**Good luck. The interpreter is waiting for you.**
