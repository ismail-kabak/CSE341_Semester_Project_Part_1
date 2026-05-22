-----
**Late-execution acknowledgment.**
Experiment E1 was required for the Part 1 D4 journal (submitted earlier this term) but was omitted from my submission by oversight. I noticed the gap on 2026-05-21 during a Part 2 D4 prep pass and am running E1 here, honestly dated, as a catch-up entry filed with my Part 2 D4 submission. This entry does **not** retroactively satisfy the Part 1 requirement; it documents the experiment for completeness and is also noted in my D5 retrospective. The model used (Claude Opus 4.7) postdates Part 1's working window, which is another reason to be explicit about when this was run rather than smuggle it into earlier dates.

-----

**Entry #** ___ • **Date** 2026-05-21
**Phase** Design / EBNF retrospective • **AI tool** Claude Opus 4.7 (extended thinking: on)
**Source session:** [claude.ai/share/6d67cab6-006e-414f-b05c-ada5fa5b0d22](https://claude.ai/share/6d67cab6-006e-414f-b05c-ada5fa5b0d22) (two-turn session: cold EBNF generation, then comparison against the locked spec)

**Goal.** Generate a first-pass EBNF grammar for Recipix from a short prose description and compare it against my locked spec (v4.1, §13), so I can see which language-specific decisions an AI derives on its own and which it silently smooths over into PL-textbook defaults.

**Prompt.** *(verbatim, one paragraph, no productions or repository content leaked into turn 1; only the one-paragraph description below)*

> Recipix is a small domain-specific language for writing parameterized recipes that can be scaled and have ingredients substituted. The primitive types are `int`, `float`, `bool`, five quantity types (`Mass`, `Volume`, `Count`, `Temperature`, `Duration`), and a separate `Pinch` type. The structured types are `Ingredient`, `Recipe`, `Step`, and `List`. User-visible constructs are: recipe declarations with parameters and a `serves` clause; function declarations (`-> ReturnType`); ingredient declarations; step declarations with optional temperature and duration modifiers written with `at` and `for`; `let` bindings; `if`/`else`; `repeat N times`; `foreach x in list`; ordinary function and recipe calls; and three call-site-only operators: `evaluate <recipe>`, `scale(r, by: k)`, and `substitute(r, x, with: y, ratio: k)`. Quantity literals look like `200 g`, `1.5 kg`, `180 °C`, and `1 pinch`. There is a unary `quantity_of` operator that projects an `Ingredient` to its `Quantity`. Operator precedence should be standard (arithmetic, then comparison, then logical), and the chained-comparison case (`a < b < c`) should not be ambiguous. Please give me an EBNF grammar.

**Response (key part — turn 1, AI's first-pass EBNF generated cold).** Highlights from the AI's response, with the precedence ladder and the four spec-specific design choices verbatim; the rest paraphrased:

```ebnf
(* Top level *)
Program        ::= TopLevelDecl* EOF
TopLevelDecl   ::= RecipeDecl | FunctionDecl | IngredientDecl

(* Expression ladder — lowest to highest precedence *)
Expression     ::= LogicalOr
LogicalOr      ::= LogicalAnd ( "or"  LogicalAnd )*
LogicalAnd     ::= Comparison ( "and" Comparison )*
(* Non-associative on purpose — see notes on `a < b < c`. *)
Comparison     ::= Additive ( CompOp Additive )?
CompOp         ::= "<" | "<=" | ">" | ">=" | "==" | "!="
Additive       ::= Multiplicative ( ( "+" | "-" ) Multiplicative )*
Multiplicative ::= Unary ( ( "*" | "/" | "%" ) Unary )*
Unary          ::= ( "-" | "not" | "quantity_of" | "evaluate" ) Unary
                 | Postfix
Postfix        ::= Primary ( CallSuffix | IndexSuffix )*

(* Call-site operators *)
ScaleExpr      ::= "scale" "(" Expression "," "by" ":" Expression ")"
SubstituteExpr ::= "substitute" "(" Expression "," Expression ","
                                   "with"  ":" Expression ","
                                   "ratio" ":" Expression ")"

(* Quantity literal *)
QuantityLit    ::= ( INT_LIT | FLOAT_LIT ) Unit
```

The AI volunteered the following commentary on each of the four spec-corner cases I had asked it to be explicit about:

- **Quantity literals: "two tokens, joined in the parser. The lexer emits `INT_LIT`/`FLOAT_LIT` and a separate `Unit` token, and `QuantityLit` glues them at the parser level. Treating `200 g` as a single lexer token would force the lexer to keep the full unit set and would be brittle if you ever want user-defined units."**
- **Chained comparison: "forbidden by making `Comparison` non-associative. The production is `Additive ( CompOp Additive )?` — at most one comparison operator."** It explicitly rejected the "desugar to `a < b and b < c`" alternative, noting that left-associative comparison would silently produce `(a < b) < c`, which is a type-error-in-disguise.
- **`if`/`else`: "no dangling-else problem because bodies are braced. `IfStmt ::= "if" Expression Block ( "else" ( IfStmt | Block ) )?`. Because both branches must be `{ ... }`, the classic ambiguity ... never arises."**
- **`quantity_of`: "sits at the unary layer, alongside `-`, `not`, and `evaluate`. So `quantity_of flour + 100 g` parses as `(quantity_of flour) + 100 g`."** Operand was *parenthesis-free*, not the locked `quantity_of(<expr>)` form.

The AI explicitly flagged its own uncertainty about `Count` ("I left it without a dedicated unit on the assumption it's promoted from `INT_LIT` by context") and named that as the most likely divergence from my spec. It also flagged that `evaluate` as a unary operator vs. a statement was a guess — it asked me to confirm in the comparison turn.

**Response (key part — turn 2, comparison against the locked spec).** I gave the AI the GitHub link to `docs/recipix_v4_1_spec.md` (§1, §5, §7, §8, §9, §13). Its self-assessment, in its own words:

> *"I got the high-stakes structural calls right — two-token quantities, non-associative comparison, mandatory `if`/`else` braces, `quantity_of` at the unary level — but missed the `substitute` bare-identifier restriction, and several smaller surface details I'll list at the end."*

Then a per-decision verdict, which I reproduce in compressed form:

| Decision | AI cold | Locked spec | Verdict |
|---|---|---|---|
| #7 quantity literals as two tokens | two tokens, parser-joined | two tokens, spec is sharper ("whitespace and `//` only between number and unit") | **match** (but AI missed `count`, had `°F`/`s`/`h` instead of `min`/`hr`, omitted `mg`) |
| #17 comparison non-associative | non-associative, `(...)?` form | non-associative, split `<rel_expr>`/`<eq_expr>` | **match**, same reasoning |
| #20 mandatory braces on if/else | mandatory, allows `else if` chain inline | mandatory, `else if` chain via nested if | **match** |
| #34 `quantity_of` at unary level | unary level, **operand without parens** | unary level, **operand with parens** | "right floor, wrong storefront" — match on placement, miss on surface syntax |
| #35 substitute slots as bare IDENT | all four slots `Expression` | ingredient slots are `IDENT` terminals | **miss** — the one big design call the AI invented from prose was wrong here |

The AI's own framing of the substitute miss is worth quoting because it identifies the design lesson cleanly:

> *"Your AST node carries `original_name: str` and `replacement_name: str`, not `Expr` — there is no AST shape that pretends the slot could be computed. That's a cleaner separation than what mine produced. ... I'd treat this as the cleanest design lesson in the whole comparison — grammar-as-documentation-of-semantics, not just grammar-as-parser-spec."*

**Accepted.** The four high-stakes calls match the locked grammar's intent — and the AI's *reasoning* on each (lexer simplicity for two-token quantities, parse-time vs type-time error for non-associative comparison, dangling-else-by-construction for mandatory braces, no-`FunctionType`-can-express-this for `quantity_of` at unary) lines up with the design rationale I had locked in spec §2 and the v4.1 decision table. The precedence ladder shape (seven levels in the right top-down order) and the structural skeleton of the program (top-level decls, expression-statement separation, brace-delimited blocks) all match. Even the "right floor, wrong storefront" miss on `quantity_of` proves the type-system reasoning was sound; only the surface syntax differed.

**Rejected / modified.** The one decision-level miss (substitute slots) and a cluster of over-permits, listed in the AI's own self-categorization:

1. **`substitute` slots as `Expression` instead of `IDENT`.** Real miss. Under the AI's grammar, `substitute(r, flour + salt, with: milk, ratio: 1.0)` parses; under the spec, it's a parse error. The decision-#28 rationale (ingredient identity *is* the symbol-table binding, not the `name` field's contents) is invisible in the AI's grammar and visible in mine.
2. **`let` type annotation made optional.** Spec §7 requires it in v1 (no inference). AI under-constrained.
3. **`List<T>` as a user-writable type annotation.** Decision #32 explicitly forbids that in v1; lists are inferred. AI over-permitted.
4. **Top-level `IngredientDecl`.** Spec §6 scopes ingredient names to the enclosing recipe; no top-level ingredients. AI over-permitted.
5. **Step body absent entirely.** The AI's `StepDecl ::= "step" Expression StepModifier*` had no `{ ... }` action block, and described it with a general `Expression` rather than the `STRING_LIT` the spec requires.
6. **Action verbs not anticipated.** No closed reserved set, no Decision #29 homogeneous-list carve-out. At the pure grammar level the AI flagged that action verbs syntactically look like ordinary calls, so this isn't a violation of any locked production — but the linguistic concept was missing.
7. **Recipe calls labelled-argument style.** Spec samples use `pancakes(servings: 4)`; AI's `ArgList ::= Expression ("," Expression)*` is positional-only.
8. **Function body too permissive.** Spec §7 forbids early return (single `return` at end); AI had a general `Block`.
9. **Postfix indexing `e[i]`.** Spec has no user-facing list indexing — `foreach` is the iteration mechanism.
10. **Logical operator surface forms.** AI used keyword spellings (`and`, `or`, `not`); spec §1 uses symbol spellings (`&&`, `||`, `!`). Pure surface choice but a divergence.
11. **Unit set wrong in three places.** Missing `count` (AI predicted `Count` would be promoted from `INT_LIT` by context — and to its credit, the AI itself flagged this as its most likely error before seeing the spec), missing `mg`, and including spurious `°F`/`s`/`h` instead of the locked `min`/`hr`.

**Errors caught.** Consolidated from the seven-point comparison and the post-hoc divergence list, focused on the ones that have a defensible Recipix-specific consequence:

1. **`substitute` slots as `Expression` (decision #35) — wrong.** Under the AI grammar, an arbitrary expression can compute "which ingredient to substitute." That defeats the whole point of decision #28 (ingredient identity is the binding, not a runtime value). The AI's own retrospective on this is the strongest passage in the session: it identifies grammar-as-documentation-of-semantics as the design lesson, which is exactly the rubric language I'd want to surface on the exam.

2. **Cluster of over-permits where the spec locks down (decisions #32, #33-style restrictions, §6 scoping, §7 single-return).** Letting `List<T>` annotations exist, top-level ingredients exist, `let` type annotations be optional, indexing exist, and function bodies have early-return is the predictable shape of "derive a grammar from prose without the locked decisions in view" — when in doubt the AI admits more, where I'd locked more down. This is what the AI itself called "the predictable failure mode of derive-a-grammar-from-prose."

3. **`quantity_of` as parens-free prefix instead of `quantity_of(<expr>)` (decision #34).** Surface syntax miss only; the type-system reasoning was correct. But the parens-free form ambiguates `quantity_of flour + 100 g` (the AI parsed it as `(quantity_of flour) + 100 g`, which is what I want — but the syntactic confusion would bite users who expected function-call semantics). The locked parens form is intentionally call-looking to read naturally while the grammar production keeps it from actually being a function.

4. **Unit set drift (decision #7 corollary).** The unit set is closed in v1 per §1; the AI invented units (`°F`, `s`, `h`) and missed the locked ones (`count`, `mg`). Any program written against the AI grammar with `30 s` or `200°F` would lex fine and parse fine under that grammar, then die against my actual lexer with a "missing separator" or "unknown unit" error. The cost of relying on prose-derived grammars is exactly this kind of silent drift in the lexical layer.

**Reflection.** The thing that surprised me here is how much Opus got right cold with thinking on. Four of five big design calls came back match — quantity literals as two tokens, non-associative comparison, mandatory braces, `quantity_of` at the unary level. I'd expected closer to zero. What didn't change is the kind of thing it still misses. Decision #28 ("ingredient identity is the binding") drives Decision #35 (substitute slots are bare identifiers), and there's no way to derive #35 from prose unless you've already had the #28 conversation. The over-permits — `List<T>` annotations as user-writable, top-level ingredients, optional `let` type, indexing, multi-return function bodies — are the same shape: the AI admits whatever generic PL languages admit; the spec restricts what Recipix specifically restricts. Lesson: I can't trust a "generate a grammar from a paragraph" pass to surface decisions whose rationale lives outside that paragraph. I have to drive the AI with the rationale already in hand. That's also why I'm filing this entry on its real date and not backdated — the value of the experiment is in the comparison, and the comparison only holds if the dates and tool name are honest.
