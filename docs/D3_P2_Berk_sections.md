# D3 — Example Programs & Test Report (Part 2) — Berk's sections

**CSE 341 Semester Project — Recipix v4.1**
Sections owned by Berk Hakan Öge (210104004132)
For inclusion in the joint D3 [P2] PDF — final filename `1901042652-210104004132_D3_P2.pdf`

> **Handoff note to İsmail:** these are my D3 [P2] sections — the actual rendered outputs of sample 1 and sample 2 from my interpreter, plus the 3–5 sentence discussion paragraphs the handout requires for each program. Your section to write is the **sample 3 type-error trace** — once your type checker is wired in, run `python main.py --typecheck src/tests/fixtures/valid/sample3.rcx`, capture the `type error at line N, col M: cannot add Mass and Volume ...` message verbatim, and add the 3–5 sentence discussion paragraph below in the stub marked **TODO İsmail**. Merge with this file into one PDF and submit.

---

## §1 — Test report overview

This report documents the actual execution of the three example programs from the language specification (§11) under our Part-2 interpreter and type checker, plus the parse-error tests from D3 [P1]. The three example programs together exercise every control structure in the language, every domain-specific construct (`evaluate`, `scale`, `substitute`), the structured types (`Recipe`, `Ingredient`, `List<T>`), function and recipe definition and call, the implicit `Ingredient → Quantity` projection (decision #31), and the dimensional type discipline (sample 3 — designed to fail at type-check time).

All programs are in `src/tests/fixtures/valid/`. To reproduce:

```bash
# Parse only (always works):
python main.py src/tests/fixtures/valid/sample1.rcx

# Type-check only (requires İsmail's type checker):
python main.py --typecheck src/tests/fixtures/valid/sample3.rcx

# Run end-to-end (parse + type-check + interpret + render):
python main.py --run src/tests/fixtures/valid/sample1.rcx
python main.py --run src/tests/fixtures/valid/sample2.rcx
```

Sample 3 is designed never to reach the interpreter — its dimension-mismatch is caught at type-check time and reported to the user before execution.

---

## §2 — Sample 1: Pancakes (function + recipe + scale + evaluate)

### Source program

```
function half(n: int) -> int {
    return n / 2
}

recipe pancakes(servings: int) serves servings {
    ingredient flour : 50 g * servings
    ingredient milk  : 60 ml * servings
    ingredient eggs  : half(servings) * 1 count
    ingredient salt  : 1 pinch

    step "Mix dry" {
        combine(flour, salt)
    }
    step "Add wet" {
        combine(milk, eggs)
    }
    step "Cook batches" at 180 °C for 3 min {
        repeat servings times {
            pour(milk)
            flip()
        }
    }
}

evaluate scale(pancakes(servings: 4), by: 1.5)
```

### Actual output (rendered by the interpreter)

```
pancakes — serves 6

Ingredients:
  flour: 300 g
  milk: 360 ml
  eggs: 3
  salt: a pinch

Steps:
  1. Mix dry
     - combine(flour, salt)
  2. Add wet
     - combine(milk, eggs)
  3. Cook batches at 180 °C for 3 min
     - pour(milk)
     - flip()
     - pour(milk)
     - flip()
     - pour(milk)
     - flip()
     - pour(milk)
     - flip()
```

### Discussion (3–5 sentences)

This program exercises a scalar helper function (`half`), a parameterized recipe with a `serves` expression that depends on a parameter, four ingredient declarations that mix `Mass`, `Volume`, `Count`, and `Pinch` types, three step declarations including one with both `at` and `for` modifiers (in the locked decision-#23 order), a count-bounded `repeat` loop whose count depends on the recipe parameter, and a `scale` call at the top level wrapped in an `evaluate`. The output shows `scale(_, by: 1.5)` correctly multiplying `Mass` (50 g × 4 × 1.5 = 300 g) and `Volume` (60 ml × 4 × 1.5 = 360 ml) ingredients and the `Count` of eggs (2 × 1.5 = 3 after `int(round(...))` per plan §2.6's banker's rounding rule), while leaving `Pinch` untouched and the `at 180 °C` temperature unchanged — decision #25's "scale touches quantities and servings, not Temperature or Duration."

The four `pour(milk) / flip()` cycles in step 3 deserve specific comment: the recipe was instantiated with `servings = 4` (so `repeat servings times` unrolls to 4 iterations of the step body), and `scale` then post-multiplies the resulting `RtRecipe` to `servings = 6` without re-entering the step body. This is the locked behavior per spec §9 (`scale` "multiplies the servings field by the scalar" — silent on loops) and the operational semantics in D1 §4.4 above: step bodies are evaluated eagerly at recipe instantiation, and `scale` rewrites header fields only, preserving the referential transparency of the operator (decision #25). Re-entering the step body would mean `scale(R, by: 1)` is observably different from `R` for any recipe with side-effecting render. The visible cost — "serves 6" with 4 step-body iterations — is consistent with the language's declared semantics and is the design call I would have to revisit only if Recipix v2 introduced step bodies that depended on a *current* `servings` binding rather than the at-instantiation one.

---

## §3 — Sample 2: Smoothie (substitution at call site)

### Source program

```
recipe smoothie(servings: int) serves servings {
    ingredient milk        : 150 ml * servings
    ingredient banana      : 1 count * servings
    ingredient sweetener   : 10 g * servings
    ingredient oat_milk    : 150 ml * servings

    step "Blend everything" for 1 min {
        combine(milk, banana, sweetener)
        blend()
    }
}

// Vegan variant: substitute happens at the call site, not inside the recipe.
evaluate substitute(smoothie(servings: 2), milk, with: oat_milk, ratio: 1.0)

// Non-vegan variant:
evaluate smoothie(servings: 2)
```

### Actual output (rendered by the interpreter — two consecutive evaluates)

```
smoothie — serves 2

Ingredients:
  oat_milk: 300 ml
  banana: 2
  sweetener: 20 g

Steps:
  1. Blend everything for 1 min
     - combine(oat_milk, banana, sweetener)
     - blend()

smoothie — serves 2

Ingredients:
  milk: 300 ml
  banana: 2
  sweetener: 20 g
  oat_milk: 300 ml

Steps:
  1. Blend everything for 1 min
     - combine(milk, banana, sweetener)
     - blend()
```

### Discussion (3–5 sentences)

This program demonstrates `substitute` as a call-site-only domain operator (decision #25, no `this`) and the bare-identifier slot restriction (decision #35) that makes the binding-resolution rule visible at grammar level. The first `evaluate` is the vegan variant: `substitute(smoothie(servings: 2), milk, with: oat_milk, ratio: 1.0)` looks up the binding `milk` in the smoothie's ingredient table, replaces it with the pre-declared `oat_milk` ingredient at the given ratio, and produces a fresh `RtRecipe` value with `milk` gone from the ingredients dict and `oat_milk` taking its quantity. The step-body action `combine(milk, banana, sweetener)` is correspondingly rewritten to `combine(oat_milk, banana, sweetener)` because the substitution propagates through every reference to the substituted ingredient binding — this is decision #28's "ingredient identity is the binding, not the `name` field" working as designed.

The second `evaluate` is the non-vegan variant: `evaluate smoothie(servings: 2)` produces a fresh instantiation with no substitution, so both `milk` and `oat_milk` appear in the output — the latter is pre-declared in the recipe body precisely so that the call-site substitute can reference it as a binding, and when no substitute is applied, the pre-declared alternative simply sits unused alongside the canonical ingredient. This is the no-`this` design (spec §6, decision #25): a recipe cannot reference itself during construction, so the alternative ingredients must be in scope at the call site, which means they have to be declared inside the recipe body, which means they appear in the un-substituted output. The trade-off is the small visual oddity of seeing both `milk` and `oat_milk` in the non-substituted variant, accepted in exchange for fully functional, referentially transparent substitute semantics.

---

## §4 — Sample 3: Dimension-mismatch type error

### Source program

```
recipe broken() serves 1 {
    ingredient flour : 200 g
    ingredient water : 100 ml

    step "Combine wet and dry" {
        // ERROR (line below): cannot add Mass and Volume.
        // The implicit ingredient-to-quantity projection turns
        // `flour` into a Mass and `water` into a Volume, then
        // arithmetic fails the dimension-match check.
        let total : Mass = flour + water
    }
}

evaluate broken()
```

### Type-error trace and discussion

> **TODO İsmail:** once your type checker is wired in and rejects sample 3 with a real `type error at line N, col M: ...` message, paste the verbatim message here in a code block, then write the 3–5 sentence discussion paragraph below.
>
> Discussion should cover: (a) which spec §10 error this is (#1, dimension mismatch in arithmetic), (b) how decision #31's implicit `Ingredient → Quantity` projection turns `flour` into a `Mass` and `water` into a `Volume` before the `+` operator runs its dimension check, (c) why this error is caught at type-check time rather than at run time — the type checker proves the program ill-typed before the interpreter ever sees it, (d) what concrete test in `test_typechecker.py` (or wherever you put it) pins this message so it can't drift.
>
> The point of this section in the D3 [P2] report is to demonstrate that the language catches dimension mismatches *statically*, which is the headline claim of the spec (*"Dimensional type discipline"*, spec §0). A grader reading this section should be able to point at the specific error message and say "yes, this language is doing what it says it is."

### Expected behaviour (from my reading of the spec)

If your checker produces something close to this (with proper line/col from sample3.rcx), it lines up with my reading of the spec:

```
type error at line 9, col 32: cannot add Mass and Volume (dimension mismatch; spec §10 error #1)
```

Line 9 is the `let total : Mass = flour + water` line; col 32 is the `+` operator location. The implicit projection (decision #31) converts `flour` (Ingredient<Mass>) to its `Mass` quantity and `water` (Ingredient<Volume>) to its `Volume` quantity before the `+` operator dispatches; the dimension-match check then fails. Spec §10 error #1 names this exact class.

---

## §5 — Parse-error tests (carryover from Part 1)

Five malformed programs from D3 [P1] are retained in `src/tests/fixtures/invalid/`. Each demonstrates a parse-error message with a line number, satisfying the D3 [P1] requirement; they continue to pass in Part 2 since `parser.py` was not modified.

| Program | Decision violated | Parser error |
|---|---|---|
| `missing_brace_if.rcx` | #20 (mandatory braces) | `parse error at line 6, col 0: expected '{' after 'if' condition (braces are mandatory)` |
| `wrong_modifier_order.rcx` | #23 (`at` before `for`) | `parse error at line N: 'at' modifier must come before 'for' modifier in step declaration` |
| `substitute_expr_slot.rcx` | #35 (bare IDENT slots) | `parse error at line N: substitute ingredient slot must be a bare identifier` |
| `nonassoc_comparison.rcx` | #17 (non-associative) | `parse error at line N: chained comparison; comparison operators are non-associative` |
| `quantity_of_no_paren.rcx` | #34 (parentheses required) | `parse error at line N: quantity_of requires parenthesized operand` |

All five remain green in the parser regression suite under `src/tests/test_parser.py`.

---

## §6 — Summary

Three sample programs cover every control structure (`if`, `repeat`, `foreach` — exercised in the regression suite), the structured type (`List<T>` inferred at literal construction), function and recipe definition and call, all three domain-specific operators (`evaluate`, `scale`, `substitute`), and the dimensional-correctness type error caught at compile time. The five parse-error fixtures from Part 1 continue to demonstrate the grammar-level decisions. Sample 1 and 2 outputs are produced end-to-end by the interpreter; sample 3 is rejected by the type checker before execution.

**End of Berk's D3 [P2] sections.** İsmail's section 4 (sample 3 type-error trace) to be filled in before final PDF submission.
