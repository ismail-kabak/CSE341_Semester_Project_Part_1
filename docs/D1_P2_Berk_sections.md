# D1 — Design Specification (Part 2) — Berk's sections

**CSE 341 Semester Project — Recipix v4.1**
Sections owned by Berk Hakan Öge (210104004132)
For inclusion in the joint D1 [P2] PDF — final filename `1901042652-210104004132_D1_P2.pdf`

> **Handoff note to İsmail:** these are my sections of D1 [P2] per `part2_plan.md` §8 ownership table. Your sections to write are §4.1 (Language Overview, revised from spec §11), §4.2 (Lexical Structure, revised from spec §1), §4.5 (Type System, all five Sebesta-tied sub-questions, source = spec §2 + decision #10), §4.6 (Names/Binding/Scope/Lifetime, revised from spec §6), and your three §4.8 rationale paragraphs (coercion / equivalence / structured type). When you're done, merge with this file into one PDF and submit.

---

## §4.3 Syntax (revised from spec §13)

The complete EBNF grammar is locked in `recipix_v4_1_spec.md` §13 and reproduced below in summarized form. Decisions visible at the grammar level (and not deferred to the type checker) are annotated inline.

```ebnf
(* Top-level program *)
<program>         ::= { <top_decl> }
<top_decl>        ::= <recipe_decl> | <function_decl> | <eval_stmt>

(* Recipe declaration *)
<recipe_decl>     ::= "recipe" IDENT "(" [ <params> ] ")"
                      "serves" <expr> <block>
<params>          ::= IDENT ":" <type> { "," IDENT ":" <type> }
<block>           ::= "{" { <ingredient_decl> | <step_decl> | <stmt> } "}"

(* Function declaration *)
<function_decl>   ::= "function" IDENT "(" [ <params> ] ")"
                      "->" <type>
                      "{" { <stmt> } "return" <expr> "}"
                   (* Decision #19 [P2]: single return at end, no early
                      return; enforced by the type checker.            *)

(* Ingredient declaration — only inside a recipe body *)
<ingredient_decl> ::= "ingredient" IDENT ":" <expr>

(* Step declaration with optional modifiers in a fixed order *)
<step_decl>       ::= "step" STRING_LIT [ "at" <expr> ] [ "for" <expr> ]
                      "{" { <step_action> } "}"
                   (* Decision #23: `at` strictly before `for`; each at
                      most once.                                        *)

(* Statements *)
<stmt>            ::= <let_stmt> | <if_stmt> | <repeat_stmt>
                    | <foreach_stmt> | <action_stmt>
<let_stmt>        ::= "let" IDENT ":" <type> "=" <expr>
<if_stmt>         ::= "if" <expr> <block_stmt> [ "else" <block_stmt> ]
                   (* Decision #20: braces mandatory on both arms;
                      dangling-else eliminated by construction.        *)
<block_stmt>      ::= "{" { <stmt> } "}"
<repeat_stmt>     ::= "repeat" <expr> "times" <block_stmt>
<foreach_stmt>    ::= "foreach" IDENT "in" <expr> <block_stmt>

(* Domain-specific top-level operation *)
<eval_stmt>       ::= "evaluate" <expr>

(* Expression precedence ladder — lowest to highest *)
<expr>            ::= <or_expr>
<or_expr>         ::= <and_expr> { "||" <and_expr> }
<and_expr>        ::= <eq_expr>  { "&&" <eq_expr> }
<eq_expr>         ::= <rel_expr> [ ("==" | "!=") <rel_expr> ]
<rel_expr>        ::= <add_expr> [ ("<" | "<=" | ">" | ">=") <add_expr> ]
                   (* Decision #17: both <eq_expr> and <rel_expr> are
                      non-associative — at most ONE comparison op per
                      production. Chained comparisons are a parse
                      error.                                            *)
<add_expr>        ::= <mul_expr> { ("+" | "-") <mul_expr> }
<mul_expr>        ::= <unary>    { ("*" | "/") <unary> }
<unary>           ::= "-" <unary>
                    | "!" <unary>
                    | "quantity_of" "(" <expr> ")"
                    | <primary>
                   (* Decision #34: quantity_of is a unary operator
                      with a dedicated production at this level, NOT a
                      function call routed through <primary>.          *)

(* Primary expressions and call-site operators *)
<primary>         ::= <int_lit> [ <unit_kw> ]
                    | <float_lit> [ <unit_kw> ]
                   (* Decision #7: quantity literals are TWO tokens —
                      numeric literal followed by unit keyword.        *)
                    | <string_lit> | <bool_lit> | IDENT
                    | <list_lit>
                    | <function_call> | <recipe_call>
                    | <scale_call> | <substitute_call>
                    | "(" <expr> ")"
<list_lit>        ::= "[" [ <expr> { "," <expr> } ] "]"
<function_call>   ::= IDENT "(" [ <expr> { "," <expr> } ] ")"
<recipe_call>     ::= IDENT "(" [ <kwarg> { "," <kwarg> } ] ")"
<kwarg>           ::= IDENT ":" <expr>
<scale_call>      ::= "scale" "(" <expr> "," "by" ":" <expr> ")"
<substitute_call> ::= "substitute" "(" <expr> ","
                        IDENT ","
                        "with"  ":" IDENT ","
                        "ratio" ":" <expr>
                      ")"
                   (* Decision #35: the two ingredient slots are bare
                      IDENT terminals, not <expr>. The grammar makes
                      decision #28 (ingredient identity IS the binding)
                      visible at parse level.                          *)

(* Types *)
<type>            ::= "int" | "float" | "bool"
                    | "Mass" | "Volume" | "Count"
                    | "Temperature" | "Duration"
                    | "Pinch"
                   (* Decision #32: no user-facing type-parameter
                      syntax. `List<T>` does not appear in user source;
                      list types are inferred at literal construction
                      and at `foreach` loop entry.                     *)
```

The grammar is unambiguous on the subset implemented. Operator precedence is encoded by the seven-level ladder (`<or_expr>` down to `<unary>`). Associativity is left for binary arithmetic and logical operators (the `{ ... }` repetition), non-associative for comparisons (the `[ ... ]` optional single operator), right for unary prefix operators (the recursive `<unary>` in the production).

---

## §4.4 Semantics (operational, big-step) — [P2]

Two non-trivial constructs given operational semantics in the style of Sebesta §3.5: `scale` (domain-specific) and `foreach` (an iterator loop whose semantics interact with scope and the list-element-binding rule).

Let `S` be the state — an environment mapping names to values, where values include `RtQuantity(v, d)` (numeric `v` in the dimension's base unit and dimension tag `d`), `RtPinch`, `RtIngredient(name, q)`, `RtRecipe(name, servings, ingredients, steps)`, `RtList(elems, t)`, and the primitives `int`, `float`, `bool`. Let `→` denote the evaluation relation `⟨expr, S⟩ → v` for expressions and `⟨stmt, S⟩ → S'` for statements.

### `scale(r, by: k)` — functional rescaling of a recipe

```
  ⟨r, S⟩ → R = RtRecipe(name, n, ingredients, step_decls, captured_params, …)
  ⟨k, S⟩ → κ : (int | float)
  κ > 0
  n' = int(round(n * κ))
  ∀ (id, ing) ∈ ingredients: ing' = scale_ingredient(ing, κ)
  ingredients' = { id ↦ ing' | (id, ing) ∈ ingredients }
  S_scaled = globals.child()                                  (* fresh env *)
  ∀ (p, v) ∈ captured_params:
      S_scaled[p] = n'  if v was the original servings value
                  v   otherwise
  ∀ (id, ing') ∈ ingredients': S_scaled[id] = ing'
  ∀ step_decl ∈ step_decls:
      steps'_i = exec_step(step_decl, S_scaled.child())
  ──────────────────────────────────────────────────────────────────
  ⟨scale(r, by: k), S⟩ →
      RtRecipe(name, n', ingredients', steps', step_decls, captured_params, …)

  where:
    scale_ingredient(ing, κ) =
      RtIngredient(ing.name, RtQuantity(ing.q.v * κ, ing.q.d))
        if ing.q.d ∈ {Mass, Volume, Count}
    scale_ingredient(ing, κ) =
      ing  (* unchanged *)
        if ing.q.d ∈ {Temperature, Duration}
    scale_ingredient(ing, κ) =
      ing  (* unchanged *)
        if ing.q = RtPinch

    exec_step(step_decl, env) =
      RtStep(description, eval(at_expr, env), eval(for_expr, env),
             accumulate_actions(body, env))
```

Side conditions: if `κ ≤ 0` the rule does not apply; the interpreter raises `RuntimeRecipixError`. Banker's rounding (`int(round(...))`) is the locked rule from plan §2.6 — it is unbiased on half-way cases, where truncation toward zero biases down (`scale(r-of-3, by: 0.5)` would yield 1 serving under truncation but 2 under banker's rounding) and ceiling biases up. The unchanged-Temperature-and-Duration rule reflects that temperature and duration are intensive quantities in the physical sense (a recipe at 180 °C does not become 270 °C when doubled).

**Step bodies are re-executed under the scaled `servings` binding.** Recipe instantiation captures the original parameter map (`captured_params`) and the unevaluated step declarations (`step_decls`) on the `RtRecipe` value. When `scale` runs, it builds a fresh evaluation environment in which the `servings` parameter is rebound to `n'` (and all ingredient bindings are rebound to the scaled values), then re-executes each step declaration's body against that environment. The visible consequence in sample 1 is that `scale(pancakes(servings: 4), by: 1.5)` renders "serves 6" with **six `pour/flip` cycles** in the step body — `repeat servings times` rebinds to 6 in the scaled evaluation, not 4. This matches the user-intuitive reading of `scale`: doubling a recipe doubles the work, not just the header. Spec §9 (*"multiplies the servings field by the scalar"*) is silent on loop bodies, but the re-execution rule is the consistent reading once you accept that `servings` is the controlling parameter for any step-body iteration referring to it. Referential transparency (decision #25) is preserved because `scale` still produces a fresh `RtRecipe` value without mutating the original — the re-execution happens entirely inside the new value's construction. `captured_params` and `step_decls` are auxiliary fields of `RtRecipe` introduced specifically to support this re-execution; they are not visible to the user and do not affect equivalence (decision #10: name equivalence for `Recipe`).

### `foreach x in <list_expr> { <body> }` — homogeneous list iteration

```
  ⟨list_expr, S⟩ → RtList(elems, T)
  S₀ = S
  ∀ i ∈ [0, |elems|):
      Sᵢ' = Sᵢ[x ↦ elems[i]]      (* bind loop variable in fresh scope *)
      ⟨body, Sᵢ'⟩ → Sᵢ₊₁''
      Sᵢ₊₁ = Sᵢ₊₁'' \ {x}          (* loop variable goes out of scope *)
  ──────────────────────────────────────────────────────────────────
  ⟨foreach x in list_expr { body }, S⟩ → S_|elems|
```

Side conditions: `RtList(elems, T)` must have `|elems| ≥ 0` (the empty-list case is well-defined and produces zero iterations); the loop variable `x` is bound to type `T` in each iteration's body scope; the binding is fresh per iteration and goes out of scope at the end of the iteration; `x` may not shadow a name visible in `S` (the type checker enforces decision #12 no-shadowing at compile time, so by the time the interpreter runs this rule, `x` is known not to collide).

The list expression is evaluated *once*, before any iteration. This is decision #18 (operand evaluation order is left-to-right, fully defined). If the list expression had side effects in some hypothetical Recipix v2 with mutation, this rule would need revision — but in v1 every expression is referentially transparent, so single vs. per-iteration evaluation is unobservable. The fresh-binding-per-iteration rule (`x ↦ elems[i]` with `x` going out of scope at iteration end) means that within a single iteration `x` is immutable (decision #13 single-assignment); between iterations `x` is rebound, which is the only rebinding form in Recipix v1.

Note on the design space: a `while` form would also have been defensible, but I chose `foreach` because it carries the homogeneous-list invariant in its type signature (the loop variable's type comes from the list's element type, inferred at construction) and forces the user to think in terms of a finite data structure rather than an unbounded condition. This pairs naturally with Recipix's no-mutation design — a `while` form whose condition can change between iterations only makes sense in a language with side effects.

---

## §4.7 Expressions & Assignment — [P2]

Decisions from Sebesta Ch. 7 made explicit:

**Operator precedence and associativity** (Sebesta §7.2, from spec §5):

| Level | Operators | Associativity |
|---|---|---|
| 1 | unary `-`, `!`, `quantity_of(...)` | right |
| 2 | `*`, `/` | left |
| 3 | `+`, `-` (binary) | left |
| 4 | `<`, `<=`, `>`, `>=` | **non-associative** |
| 5 | `==`, `!=` | **non-associative** |
| 6 | `&&` | left |
| 7 | `\|\|` | left |

Parenthesization overrides precedence. The non-associative comparison levels are enforced at parse time: `a < b < c` is a parse error, not a type error. This catches a category of bug (chained comparisons that silently produce `(a < b) < c` and try to compare a `bool` against the original right operand's type) at the earliest possible phase. The trade-off is that users wanting transitive chaining must write `a < b && b < c` explicitly, but the explicitness is consistent with Recipix's reliability-over-writability stance (spec §1).

**Short-circuit evaluation** (Sebesta §7.5). `&&` and `||` short-circuit left-to-right. The interpreter evaluates the left operand first; if its value determines the result (`false` for `&&`, `true` for `||`), the right operand is not evaluated. This is observable only in the sense that the right operand is not type-checked at runtime in skipped paths — but in v1 the type checker has already proven both operands are `bool`, so short-circuit cannot hide a type error.

**Operand evaluation order** (Sebesta §7.6). Left-to-right, fully defined. Stronger than C's "unspecified" rule, weaker than nothing-could-be-different (because in absence of side effects the order is unobservable). Recipix has no mutation in v1, so the choice is unobservable to the user, but locking the order matters for error reporting: in `let x : int = f(a/0) + g(b/0)`, the division-by-zero from `a/0` is the one that fires, not `b/0`. Users debugging a runtime error get a predictable line number.

**Assignment as statement, not expression** (Sebesta §7.6, decision #27). The only binding form in Recipix is `let <name> : <type> = <expr>`, which is a statement. There is no assignment-in-expression form (`x = y + 1` is not valid in any expression position). The trade-off is mild verbosity in some patterns (you cannot write `if (x = compute()) > 0 { ... }`), but the gain is that no expression has a side effect — which lets decision #18's left-to-right evaluation order be unobservable and lets the entire language be referentially transparent in v1.

Recipix has no compound assignment (`+=`, `*=`), no increment (`++`), and no augmented assignment of any kind. Combined with the no-shadowing rule (decision #12) and the single-assignment rule (decision #13 — `let`-bound names cannot be re-bound in their scope), every name's value is determined entirely by its initializer expression. This is closer to functional-language discipline than to typical imperative scripting languages.

---

## §4.8 Design Rationale — Berk's paragraphs

*Per `part2_plan.md` §8: each partner writes their own design-rationale paragraphs in their own voice. My four paragraphs cover precedence/associativity, short-circuit, operand evaluation order, and assignment-as-statement. İsmail's three paragraphs cover coercion, type equivalence, and the structured-type design choices.*

**Why non-associative comparison and a seven-level precedence ladder.** The hardest call here was whether to make comparisons non-associative or left-associative with the standard `(a < b) < c` chaining semantics. Left-associative is the C/Java/Python-without-chaining default and would have made the precedence ladder simpler — one level for all six comparison ops instead of two non-associative levels. I picked non-associative because of the failure mode left-associative chaining produces: `1 kg < flour < 2 kg` parses cleanly under C semantics, then evaluates `1 kg < flour` to a `bool`, then tries to compare that `bool` against `2 kg` and gets a type error. The user reads the program, sees a sensible-looking transitive comparison, and gets a confusing type-error message about comparing `bool` to `Mass` at runtime. Splitting comparisons into `<rel_expr>` and `<eq_expr>` and making both non-associative catches this at parse time with a clean "chained comparison not allowed" message. The trade-off accepted: users who want transitive chaining write `(1 kg < flour) && (flour < 2 kg)` — a small writability cost paid in the currency of reliability and clearer error messages.

**Why short-circuit `&&` and `||`, left-to-right.** Short-circuit is the standard choice and the one Sebesta §7.5 frames as the user-friendly default — it's what programmers expect, and the alternative (eager evaluation of both operands) would force users to write `if x != null && x.field > 0` as nested `if`s with awkward indentation. The interesting design question was *which direction* to short-circuit. Left-to-right matches the operand-evaluation rule from decision #18 and gives users one mental model for both: expressions are evaluated in the order they're written, and logical operators stop early when they have the answer. Right-to-left short-circuiting would have been internally consistent if the operand-evaluation rule were also right-to-left, but Sebesta §7.6 notes that left-to-right is the strongly dominant convention and breaking it just to be different would be writability-negative.

**Why operand evaluation order is left-to-right and fully defined.** Decision #18 over-commits compared to most language specs, which leave operand order "unspecified" so compilers can reorder for optimization (C, C++). The C-style choice has a real cost in pedagogical languages and in DSLs: a student running the same program twice can get different runtime errors because two division-by-zero candidates fire in different orders on different platforms. For Recipix this would be especially confusing because the error messages cite line numbers, and a non-deterministic line number breaks the reliability promise the language makes. I locked left-to-right and accepted the cost (the interpreter cannot reorder operands for any optimization) because reliability and predictable error reporting matter more than performance in v1 — and "performance" was already deprioritized in spec §1's evaluation-criteria framing.

**Why assignment is a statement, not an expression.** Decision #27 was a deliberate import from functional-language discipline: with `let` as the only binding form and assignment as a statement, every expression in Recipix is referentially transparent — the same expression evaluated in the same scope produces the same value, every time. The trade-off is that some patterns require slightly more code (no `while ((line = read()) != null)` form, because `=` is not an expression). I accepted this because (a) v1 has no mutation and no I/O loop, so the missing pattern doesn't arise in real Recipix programs, and (b) it lets decision #18's left-to-right evaluation order be entirely unobservable, which simplifies the operational semantics in §4.4 above — every rule for binary operators can ignore the question "what if the left operand modified something the right operand reads?" because no operand can modify anything. The cost is a v1-only restriction; if Recipix v2 introduces mutation (a mutable accumulator inside `repeat`, for example), assignment-as-statement is the first rule that should be revisited.

---

**End of Berk's D1 [P2] sections.** İsmail's sections (§4.1, §4.2, §4.5, §4.6, his three §4.8 paragraphs) to be merged with this file before final PDF submission.
