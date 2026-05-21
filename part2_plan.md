# Recipix Part 2 — Plan & Runtime Contract

**Status:** Rev 2 — incorporates feedback pass, awaiting İsmail's sign-off
**Submission:** Friday, 22 May 2026, 23:59 (~60 hours from now)
**Exam:** Thursday, 28 May 2026, 08:30, in-class, 90 min

This document is the Part 2 equivalent of the `tokens.py` agreement that
made Part 1 work. **It must be reviewed, argued over, and signed off in a
single joint session before either partner writes a line of Part 2 code.**
The Part 1 win was that we front-loaded the contract; the same move
applies here.

### Rev 2 change log

Sharpening pass over Rev 1 in response to a review. Substantive changes:

- §1 — Removed the implicit "Berk skips Ch. 6 / İsmail skips Ch. 7"
  reading. Both partners read both chapters; the table only marks
  who is the first-line owner of each chapter's terminology.
- §2.3 — Action-verb table collapsed from 12 per-verb rows to three
  signature classes (Heterogeneous / Homogeneous / Nullary). Cuts
  ~12 checker branches, ~24 tests, and a chunk of exam memorisation.
- §2.5 — Added the parameter-list-scope-equals-body-scope convention
  so the shadowing check has one less corner case.
- §2.6 — New section: three small contract items that the first
  draft missed (`serves` evaluation timing, single-return location,
  `scale` servings rounding rule). Each is one paragraph.
- §5 — `evaluate`-only and single-return constraints now have
  locked wording; single-return becomes spec §10 error #19.
- §6 — Added working rules: parser tests stay green, push-to-main
  with no feature branches, coordinate before co-editing.
- §8 — D1 §4.7 now single-owner (Berk); D5 now joint, 1 page total
  (D4 stays per-student, D6 stays joint). D3 PDF assembly named.
- §9 — Both partners do E2 *and* E3 independently, with fragment
  splits named. E2 entry-style language tightened (depth is graded).
- §10 — Six new explicit Phase 0 decisions covering the above.

---

## 1. Job split — Option A (horizontal, by module)

| Partner | Module | Primary Sebesta focus (own work) |
|---------|--------|----------------------------------|
| **Berk Hakan Öge** (210104004132) | Interpreter | Ch. 7 (expression evaluation, operand order, short-circuit), Ch. 5 leftovers (scope at runtime, parameter passing) |
| **İsmail Kabak** (1901042652) | Type checker | Ch. 6 (types, equivalence, coercion, structured types) |

> **No exam chapter split.** Each of us gets a personalised Exam 2 paper, but
> the handout is explicit that both papers draw from **Ch. 6 and Ch. 7**, with
> reference back to Part 1 material. Ch. 7 talks about operand evaluation
> order *and* coercion — one lives in the interpreter, one in the type
> checker. Ch. 6 talks about type equivalence *and* the runtime tagging
> our values carry. Both partners read both chapters end-to-end. The table
> above only marks who is the first-line owner of each chapter's terminology,
> not who can skip the other.

### Why this split

- **AST ownership continuity.** Berk owns the AST shapes from Part 1
  (`QuantityOf`, `SubstituteCall`, `AmbiguousCall`); the interpreter consumes
  them directly.
- **Design-spec ownership continuity.** İsmail authored the v4.1 spec; every
  type rule he implements is one he wrote into the spec. The §10 error list
  (18 compile-time errors) is his to enforce.
- **Defensibility for the exam.** Each partner gets a separately gradable
  artifact and a non-overlapping chapter zone on the May 28 paper. No
  shared-blame failure modes.
- **D5 alignment.** İsmail's Part-1 D5 explicitly anticipates owning the
  type checker as the hardest deliverable; Berk's Part-1 D5 flagged the
  three Part-1/Part-2 boundary items (AmbiguousCall resolution,
  evaluate-only constraint, single-return rule) that the type checker
  will resolve.

---

## 2. Integration contracts

These six items must be agreed before code starts. Everything else can
be local to its module.

### 2.1 TypedAST contract — in-place annotation

The type checker mutates AST nodes by adding two optional fields:

```python
# On every Expr node:
node.inferred_type: str           # "int" | "float" | "bool" | "Mass" |
                                  # "Volume" | "Count" | "Temperature" |
                                  # "Duration" | "Pinch" | "Ingredient" |
                                  # "Recipe" | "List<T>"

# On every AmbiguousCall node only:
node.resolved_kind: str           # "recipe" | "function"
```

Statement nodes get no annotations. Type strings use the spec's user-facing
names. List element types are encoded as `"List<Mass>"`, `"List<int>"`, etc.

**Rationale:** in-place annotation is the cheapest contract — no parallel
data structure to keep in sync, smaller diffs, and the interpreter can
ignore the annotations entirely except for `AmbiguousCall.resolved_kind`,
which it must consult.

**Critical consequence:** the interpreter can be written and unit-tested
against the un-annotated AST. Berk does not block on İsmail.

### 2.2 Runtime value representations

Defined together in `src/recipix/runtime_values.py`. Both modules import
from this file.

```python
@dataclass
class RtQuantity:
    value: float          # always in the dimension's base unit
    dimension: str        # "Mass" | "Volume" | "Count" | "Temperature" | "Duration"

class RtPinch:            # singleton sentinel — no fields, ceremonial
    pass
PINCH = RtPinch()

@dataclass
class RtIngredient:
    name: str
    quantity: RtQuantity | RtPinch

@dataclass
class RtRecipe:
    name: str
    servings: int
    ingredients: dict[str, RtIngredient]   # keyed by binding identifier
    steps: list                             # AST StepDecl nodes, evaluated lazily at render time

@dataclass
class RtList:
    elements: list
    element_type: str
```

Primitives `int`, `float`, `bool` use Python natives directly.

**Base-unit convention (locked):**

| Dimension | Base unit |
|-----------|-----------|
| Mass | `g` |
| Volume | `ml` |
| Count | `count` |
| Temperature | `°C` |
| Duration | `min` |

All arithmetic is done on base-unit numerics. Rendering converts back
to a reader-friendly unit (heuristic in `rendering.py`).

### 2.3 Action verb signature table

The spec defers this to "Part 2 H6 / locked together." Earlier drafts of
this section enumerated all twelve verbs with bespoke arity/type rules; the
final form below collapses them into three signature classes. Rationale:
twelve special cases is ~12 branches in the checker, 12 in the interpreter,
24 tests, and a memorisation load for the exam that buys no language-design
credit. The spec only commits us to "action verbs are an exception to the
homogeneous-list rule" (#29) and the closed verb set. Three classes is
defensible, implementable in a day, and survives the exam question
*"why didn't you give each verb a unique signature?"* with a one-sentence
answer ("the linguistic distinction wasn't worth the type-system complexity
in v1").

| Class | Verbs | Rule |
|-------|-------|------|
| **Heterogeneous** | `combine`, `mix`, `add`, `sprinkle` | ≥1 arg; each arg is `Ingredient` (any dimension, including `Pinch`) or a bare `Quantity` of any dimension. Decision #29 carve-out applies — mixed dimensions allowed. |
| **Homogeneous** | `pour`, `drizzle`, `whisk`, `blend`, `knead`, `melt` | ≥1 arg; all args must share one dimension; `Pinch` not allowed. Implicit `Ingredient → Quantity` projection (#31) applies. |
| **Nullary** | `bake`, `flip` | 0 args. `at`/`for` step modifiers carry any parameters these verbs need. |

This table is the type checker's source of truth for §10 error #13
("Wrong argument types in recipe or function call") as applied to action
verbs. If a v2 of Recipix wants per-verb signatures, this is the first
place it can extend without changing the grammar.

### 2.4 Quantity normalization location

- **Type checker:** tracks dimension only. Does not look at the numeric
  value of a `QuantityLit`.
- **Interpreter:** normalizes to base unit at `QuantityLit` evaluation.
  Arithmetic always operates on base-unit numerics.
- **Rendering:** converts base-unit numerics back to a sensible unit
  (heuristic: `g` if value < 1000 else `kg`; `ml` if < 1000 else `l`;
  `min` if < 60 else `hr`; `count` and `°C` always shown as-is).

### 2.5 Environment chain

Shared module `src/recipix/environment.py`, authored once (Berk drafts;
İsmail reviews):

```python
class Environment:
    def __init__(self, parent: "Environment | None" = None): ...
    def define(self, name: str, value) -> None: ...   # raises on re-declare (single-assignment)
    def lookup(self, name: str): ...                  # walks parent chain
    def declare_check(self, name: str) -> None: ...   # raises on shadowing (any ancestor has it)
```

Both modules use the same shape. Type checker stores type strings as
values; interpreter stores runtime values. Same scoping logic; no
duplication.

**Single-assignment + no-shadowing enforcement lives in the
type checker**, via `declare_check()` before every `define()`.

**Scope convention for shadowing checks:** parameter lists live in the
same scope as the body they introduce — a function's parameters are
declared into the function body's scope, not a separate "parameter
scope." Concretely, `function f(x: int) -> int { let x : int = 1 }` is
a shadowing error, not a fresh binding in a nested scope. One test
case (`tests/test_checker.py::test_param_let_shadow`) pins this.

### 2.6 Three small contract items that bit us in review

These were missing from the first draft. They are short but graded.

- **`serves <expr>` evaluation timing.** The `serves` expression on a
  recipe is parsed greedily up to the body's `{` (spec §7). At
  type-check time, the checker verifies it has type `int` in a scope
  containing the recipe's parameters. At run time, the interpreter
  evaluates it *during recipe instantiation*, once `RecipeCall` has
  bound the kwargs into the new scope. It is **not** re-evaluated per
  ingredient. The resulting `int` is stored in `RtRecipe.servings`.
- **Single-`return` enforcement on functions.** Spec §7 forbids early
  return. The check runs at `FunctionDecl` entry in the type checker,
  *before* walking the body: assert `isinstance(decl.body[-1],
  ReturnStmt)` and `not any(isinstance(s, ReturnStmt) for s in
  decl.body[:-1])`. Nested blocks (`if`, `repeat`, etc.) are also
  scanned recursively for a stray `return`. One error: `error #19`
  ("return must appear only as the last statement of a function body")
  — added to spec §10 in the [P2] revision.
- **`scale` servings rounding rule.** Spec §9 says "rounded to int."
  We lock this to **`int(round(servings * by))`** — Python's banker's
  rounding, applied after multiplying. Justification (one-liner for
  the exam): banker's rounding is unbiased; truncation toward zero
  would silently halve the servings on `scale(r, by: 0.5)` even when
  the user expected ceiling. Test case:
  `scale(recipe-of-3, by: 0.5) → servings = 2`,
  `scale(recipe-of-3, by: 2/3) → servings = 2`.

### 2.7 File layout

```
src/recipix/
  __main__.py            # CLI — extended with --typecheck and --run flags
  parser.py              # unchanged from Part 1
  ast_nodes.py           # unchanged from Part 1
  tokens.py              # unchanged from Part 1
  errors.py              # EXTENDED — adds TypeCheckError, RuntimeRecipixError
  pretty.py              # unchanged from Part 1
  environment.py         # NEW — joint, Berk drafts
  runtime_values.py      # NEW — joint, Berk drafts
  typechecker.py         # NEW — İsmail owns
  interpreter.py         # NEW — Berk owns
  rendering.py           # NEW — Berk owns

src/lexer.py             # unchanged from Part 1
src/tokens.py            # unchanged from Part 1
```

---

## 3. Critical handoff dependency

Berk's interpreter cannot dispatch `AmbiguousCall` without
`resolved_kind`. **İsmail's first deliverable is therefore symbol-table
construction + `AmbiguousCall` resolution.** Target: Thursday 21 May,
12:00.

Everything else in the type checker (dimension checks, action-verb
signatures, single-assignment enforcement) can land later in the day
without blocking the interpreter.

---

## 4. Berk's task list (interpreter)

In recommended order:

1. `runtime_values.py` — dataclasses + base-unit convention. ~30 min.
2. `environment.py` — author the shared module. ~30 min, then hand off
   to İsmail.
3. Expression evaluator skeleton: `IntLit`, `FloatLit`, `BoolLit`,
   `StringLit`, `Identifier`, `BinaryOp` (numerics only), `UnaryOp`,
   `CompareOp`. Goal: `2 + 2` through the CLI before lunch Thursday.
4. `QuantityLit` evaluation + unit conversion table (Spec §3).
5. Quantity arithmetic: `Quantity + Quantity` (same dimension),
   `Quantity * scalar`, `scalar * Quantity`, `Quantity / scalar`,
   `Quantity / Quantity` (same dimension → unitless).
6. `QuantityOf` (trivial: returns `ingredient.quantity`) + implicit
   projection in `BinaryOp` / `CompareOp` (auto-unwrap `RtIngredient`
   in arithmetic context).
7. Statement execution: `LetStmt`, `IfStmt`, `RepeatStmt`,
   `ForeachStmt`. Runtime errors: negative repeat count, division by
   zero.
8. `FunctionCall` execution: new scope, bind args, run body, catch
   `ReturnException`.
9. `RecipeCall` execution: new scope, bind kwargs, evaluate ingredient
   decls, populate `RtRecipe`, store step AST nodes for lazy rendering.
10. `ScaleCall`: scales Mass/Volume/Count; **does not** scale
    Temperature/Duration; multiplies `servings` (rounded). Runtime
    error on negative or zero `by`.
11. `SubstituteCall`: symbol-table lookup of `original_name` and
    `replacement_name` in the recipe's ingredient table; new
    `RtRecipe` with replacement binding and quantity = `replacement
    quantity * ratio`.
12. `rendering.py`: walk an `RtRecipe`, output ingredients in
    sensible units, steps with `at`/`for` modifiers, step bodies
    with action verbs rendered in cookbook English.
13. `EvalStmt` execution: evaluate inner expr, then render.
14. CLI integration: `python -m recipix <file> --run` typechecks
    then interprets; `--typecheck` runs only the type checker.

Domain-specific runtime error (for D3 [P2]): negative repeat count
is the obvious one; substitute-of-unknown-ingredient is the
domain-flavored one (even though the type checker catches most of
these at compile time, a computed-at-runtime path is technically
possible per spec §10 runtime error #4).

---

## 5. İsmail's task list (type checker)

The type checker must satisfy the contracts in §2 of this document.
Implementation is İsmail's call — but the deliverables that
**Berk depends on** are:

1. **Symbol table construction + `AmbiguousCall` resolution.**
   Thursday 21 May, 12:00 deadline. This unblocks Berk's
   `FunctionCall` vs `RecipeCall` dispatch.
2. **All 18 compile-time errors from spec §10** raised with
   line + column + message in the established
   `parse error at line X, col Y: <message>` format (renamed
   `type error at line X, col Y: <message>`).
3. **In-place AST annotation** with `.inferred_type` on every Expr
   node (contract §2.1).
4. **`evaluate`-only constraint** on `scale` and `substitute`. Locked
   wording for the spec and the checker: *"`scale` and `substitute`
   may appear anywhere in an expression rooted at an `evaluate`
   statement; they may not appear inside a `recipe` body, a
   `function` body, or any `let` initializer outside an `evaluate`."*
   Implementation: the checker carries a boolean `in_evaluate` flag
   that is set true when entering `EvalStmt.expr` and false everywhere
   else. (Resolves the Part-1 ambiguity flagged in the README.)
5. **Single-return enforcement** on function bodies. Added as
   **error #19** in spec §10: *"return must appear only as the last
   statement of a function body."* Check fires at `FunctionDecl`
   entry; recursively scans nested blocks for stray `ReturnStmt`.
   (Resolves the second Part-1 README ambiguity.)
6. **Action-verb signature enforcement** per the three-class §2.3
   table.

The §10 error list, in priority order for Berk's interpreter to be
shippable:

- Errors that prevent the interpreter from being called on broken input
  (must be raised before Berk runs): #1 (dimension mismatch), #4
  (unknown identifier), #12 (wrong arity), #13 (wrong arg types),
  #14 (unknown ingredient in substitute), #17 (non-IDENT substitute
  slot — already caught by parser).
- Errors that improve Recipix's defensibility on the exam: #2
  (Pinch in arithmetic), #5–6 (single-assignment, shadowing), #18
  (`quantity_of` on non-Ingredient).
- Errors that polish the language: #3 (heterogeneous list literal),
  #7–11 (typed contexts: if condition, repeat count, foreach source,
  at modifier, for modifier), #15 (float→int coercion), #16
  (Pinch ↔ Quantity substitution).

---

## 6. Timeline

| When | Phase | Output |
|------|-------|--------|
| **Wed 20 May, evening** | Phase 0 — joint contract meeting | This doc + agreed Phase 0 amendments, both signed |
| **Thu 21 May, AM** | Parallel build, easy paths | Berk: literal eval + numeric arithmetic. İsmail: symbol table. |
| **Thu 21 May, 12:00** | Hard handoff | İsmail ships `AmbiguousCall.resolved_kind`. |
| **Thu 21 May, PM** | Parallel build, hard paths | Berk: Quantity arithmetic, RecipeCall, ScaleCall, SubstituteCall. İsmail: dimension checks, action-verb signatures, single-assignment. |
| **Thu 21 May, evening** | Integration round 1 | `evaluate scale(pancakes(servings: 4), by: 1.5)` runs end-to-end with rough output. |
| **Fri 22 May, AM** | Integration round 2 + polish | Samples 2 and 3 work. Sample 3 fails at type-check with expected message. |
| **Fri 22 May, PM** | Writing — D3 then D1 | D3 PDF (outputs + 1 type-error trace). D1 [P2] sections (§4.4, §4.5, §4.7, §4.8). |
| **Fri 22 May, evening** | D5 + D6 + D4 catch-up | Each writes own D5 (1 page); joint D6 (½ page, both sign); each finalizes own D4. |
| **Fri 22 May, 23:59** | Submission | All six deliverables uploaded. |

### Working rules for the 60-hour window

- **Parser tests stay green.** The existing 48 tests in
  `src/tests/test_parser.py` are the regression net for the
  AST contract. After every checker/interpreter change, run
  `python -m unittest discover src/tests` before pushing. A red
  parser test means the AST contract just drifted under the
  interpreter — fix immediately, do not "we'll get to it later" it.
- **Version control discipline.** Both partners push to `main`;
  pull before every coding session and after every other partner's
  push notification. No feature branches — the window is too short
  for review overhead. Commit messages name the module touched
  (`checker: dimension check on BinaryOp`, `interp: QuantityLit
  unit conversion`). If both partners need to touch the same file
  in the same hour, coordinate in chat first.
- **Daily journal entry before bed.** Both partners. Real dates.
  The handout treats backfilled D4 entries as zero credit.

---

## 7. Phase 0 meeting agenda (target: tonight, ~2 hours)

1. Read this doc end to end together.
2. Argue over the action verb signature table (§2.3). 30 min ceiling.
3. Argue over the base-unit convention and rendering heuristic (§2.2,
   §2.4). 15 min ceiling.
4. Argue over the `evaluate`-only constraint definition: is
   `evaluate scale(substitute(r, ...), by: 2)` legal? (Recommended yes
   — nesting under `evaluate` is the safe rule.) 10 min ceiling.
5. Agree on hand-written sample 1 and sample 2 expected outputs.
   Commit them to the repo as `tests/expected/sample1.txt` and
   `sample2.txt`. 20 min ceiling.
6. Agree on sample 3 expected type-error message text. 5 min ceiling.
7. Both sign off on this document by appending the final agreed
   version to the repo as `runtime_contract.md` (replacing this
   draft).

---

## 8. Written deliverables — section ownership

| Section | Owner | Notes |
|---------|-------|-------|
| D1 §4.1 Language Overview (revised) | İsmail | Already in spec |
| D1 §4.2 Lexical Structure (revised) | İsmail | Already in spec |
| D1 §4.3 Syntax / EBNF (revised) | Berk | Already in spec §13 |
| D1 §4.4 **Semantics [P2]** | Berk | Operational, big-step, two constructs: `foreach` and `scale` |
| D1 §4.5 **Type System [P2]** | İsmail | Five Sebesta-tied sub-questions; spec §2–§3 is the source |
| D1 §4.6 Names/Binding/Scope/Lifetime (revised) | İsmail | Spec §6 is the source |
| D1 §4.7 **Expressions & Assignment [P2]** | Berk | Half a page total — owned by one person to avoid split overhead. Coercion rules belong in §4.5 (İsmail) since they are a type-system concern; §4.7 stays focused on precedence, associativity, operand order, short-circuit, and assignment-as-statement. |
| D1 §4.8 **Design Rationale [P2]** | Each writes own | One paragraph per [P2] decision, in own voice. Handout warns this is where AI boilerplate fails most. |
| D3 [P2] outputs of samples 1, 2 | Berk | From interpreter. Also assembles the PDF. |
| D3 [P2] type-error trace of sample 3 | İsmail | From type checker. Drafts the discussion paragraph for the type-error program. |
| D3 [P2] PDF assembly | Berk | Combines outputs + İsmail's section + 3–5 sentence discussions per program. |
| D5 Retrospective + Self-Assessment | **Joint, 1 page total** | Handout asks for a 1-page artifact; it does *not* mandate per-student. Writing together is faster, keeps the self-assessment grades honest, and gives one consistent voice. (D4 stays per-student — that one *is* mandated individual.) |
| D6 Contribution Report | Joint | ½ page, both sign |

---

## 9. D4 AI Usage Journal — reminder for both partners

Read the handout warning carefully: **entries dated in the final 48
hours = zero credit.** Each partner needs **6 additional entries dated
9–22 May**, on top of the Part 1 minimum of 4.

Mandatory experiments for Part 2 — **each partner writes both E2 and
E3 in their own journal.** The handout phrasing is unambiguous; we
cannot share entries even though we share a project.

- **E2 — name vs structural equivalence.** Both partners run this
  independently. The honest test is *whether the AI gets Recipix's
  split right* (structural for `Quantity<D>`, `Ingredient`, `List<T>`;
  name for `Recipe`), not whether it can recite Sebesta §6.14
  generically. Concrete probe: give the AI our type-equivalence rule
  in one sentence, ask it to predict whether `{x: float, y: float}`
  passed where a `point` record is expected would type-check. A
  generic answer ("depends on the language") is the bug; a Recipix-
  specific answer ("name equivalence → no") is the correct one. Log
  whichever you get and why it matters. The entry does not "write
  itself" — depth of reflection is graded.

- **E3 — AI implements the type checker.** Different fragments per
  partner so the writeups are honest and distinct.
  - **İsmail:** the main dimension-check logic for `BinaryOp` on
    `Quantity` operands (§3 of the spec). Run on three inputs:
    `200 g + 1 kg` (allowed, normalizes to 1200 g), `200 g + 500 ml`
    (dimension mismatch), `200 g * 2` (allowed, scalar mult).
  - **Berk:** the action-verb signature checker (§2.3 of this doc,
    three-class table). Run on three inputs: `combine(flour, salt)`
    (heterogeneous, allowed), `pour(flour)` (Mass into Volume verb,
    rejected), `bake(x)` (arity error on nullary verb).
  Log the AI's first attempt, the bugs you found, and how you fixed
  them. The handout grades **three documented "AI was wrong" moments**
  per journal — E3 should give you at least one.

The other 4 entries per partner can be:
- Design rationale sessions for §4.4 or §4.5
- The semantics writeup for Berk
- The action verb signature table debate from Phase 0
- Pretty-printer or rendering heuristic work
- Bug-fixing sessions (the more honest the bug log, the higher the
  graded depth-of-reflection score)

---

## 10. Open decisions for the Phase 0 meeting

These are explicit yes/no questions to walk through in order. Items
marked **[NEW]** were added in this revision after the first feedback
pass on the plan.

1. **Confirm Option A split.** Berk = interpreter, İsmail = type
   checker. Y/N.
2. **Confirm in-place AST annotation** (§2.1) vs a parallel TypedAST
   structure. Recommended: in-place.
3. **[NEW] Confirm collapsed three-class action verb table** (§2.3).
   Heterogeneous / Homogeneous / Nullary. Default to this form;
   only re-expand to per-verb signatures if there is a concrete
   exam-defensible reason.
4. **Confirm base-unit convention** (§2.2). Lock.
5. **Confirm rendering unit heuristic** (§2.4). Lock or simplify.
6. **Confirm `evaluate`-only-but-nestable rule** (§5 task 4 wording).
   *Legal anywhere under an `evaluate`, illegal inside recipe or
   function bodies and outside-`evaluate` `let` initializers.*
7. **[NEW] Confirm `serves` expression evaluation timing** (§2.6):
   type-checked at recipe-decl time, evaluated once at recipe-call
   instantiation, stored in `RtRecipe.servings`.
8. **[NEW] Confirm single-return enforcement location** (§2.6):
   checked at `FunctionDecl` entry, scans nested blocks recursively.
   Added as error #19 to spec §10.
9. **[NEW] Confirm scale-servings rounding rule** (§2.6):
   `int(round(servings * by))` — banker's rounding after multiply.
10. **[NEW] Confirm D5 is joint, 1 page total** (§8). D4 stays
    per-student. D6 stays joint.
11. **[NEW] Confirm both partners do E2 *and* E3 independently**
    (§9), with the fragment split listed there.
12. **Confirm critical handoff deadline:** İsmail ships
    `AmbiguousCall.resolved_kind` by Thursday 21 May, 12:00.
13. **Sample 1 and Sample 2 expected output strings** — write
    together, commit to `tests/expected/`.
14. **Sample 3 expected type-error message** — İsmail proposes,
    Berk reviews.
15. **D4 journal cadence** — both commit to writing the day's entry
    before bed each night, not at the deadline.
16. **[NEW] Confirm working rules** (§6 trailer): parser tests stay
    green; push to `main`; no feature branches; coordinate in chat
    before co-editing a file.

---

**End of proposal.** Please mark up this doc with your reactions
(track changes, inline comments, or a reply note) before tonight's
meeting. Anything not pushed back on by the start of the meeting is
treated as accepted.

— Berk Hakan Öge (210104004132)
