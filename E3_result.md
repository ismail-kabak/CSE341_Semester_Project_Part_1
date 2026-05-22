**Entry #** ___ • **Date** 2026-05-21
**Phase** Type checker • **AI tool** Claude Opus 4.7 (extended thinking: on)
**Source session:** [claude.ai/share/8190d922-7330-4181-84cd-40e1748c1e99](https://claude.ai/share/8190d922-7330-4181-84cd-40e1748c1e99) (two-turn session: cold implementation, then comparison against plan §2.3 and the typechecker stub)

**Goal.** Have the AI implement `_check_ActionStmt` on the `TypeChecker` class — the §10 error-#13 enforcer for the twelve closed verbs in spec §8 — without first showing it the three-class table from plan §2.3, then compare its inferred signatures to the locked design.

**Prompt.** *(verbatim — the twelve verbs, the type-string contract for `env.lookup`, the four test inputs whose right answers I knew in advance)*

> Recipix has a closed set of twelve action verbs (spec §8): `combine, mix, add, sprinkle, pour, drizzle, whisk, blend, knead, melt, bake, flip`. Values are `Ingredient<D>`, `Quantity<D>`, and `Pinch` where D ∈ {Mass, Volume, Count, Temperature, Duration}. Per plan §2.3 the verbs fall into three signature classes — infer or reconstruct the table from the verb semantics plus the spec's closed verb list; do not ask me to paste it. Implement `_check_ActionStmt(self, node)` on a `TypeChecker` class. `node.verb: str`, `node.args: list[Expr]`, `node.line: int`. Identifiers resolve via `self.env.lookup(name)` returning a type string like `"Ingredient<Mass>"` or `"Quantity<Pinch>"`. On any wrong-argument-type call raise `TypeCheckError(node.line, 0, <msg>, error_code=13)` (from `recipix.errors`). Use at least one helper data structure (a verb-signature dict/table).

The AI unsolicited-flagged an ambiguity in this very prompt before answering — *"you said `D ∈ {Mass, Volume, Count, Temperature, Duration}` — Pinch is not in D — but then the example return value mentions `Quantity<Pinch>`, and test #1 uses `Ingredient<Pinch>`. So either Pinch is a valid dimension (your enumeration was incomplete) or `Ingredient<Pinch>` shouldn't have made it past an earlier check. I'm assuming the former."* This is a real prompt bug; the spec treats Pinch as its own primitive, not a dimension, but the test inputs and the implicit projection rule (#31) effectively require the checker to handle `Ingredient<Pinch>` as a well-formed type. Worth keeping in mind for the v4.2 spec wording.

**Response (key part — turn 1, AI's first-pass implementation).** The signature table (the design-significant part) verbatim:

```python
VERB_SIGS = {
    # Multi-ingredient mixing: >=2 ingredients, any dimension each.
    'combine': ('variadic', [], _ingredient_of(), 2),
    'mix':     ('variadic', [], _ingredient_of(), 2),
    'blend':   ('variadic', [], _ingredient_of(), 2),

    # Single ingredient, any dimension.
    'whisk':   ('fixed',    [_ingredient_of()]),
    'flip':    ('fixed',    [_ingredient_of()]),

    # Solid, weighable ingredients.
    'knead':   ('fixed',    [_ingredient_of('Mass')]),
    'melt':    ('fixed',    [_ingredient_of('Mass')]),

    # Liquid ingredients.
    'pour':    ('fixed',    [_ingredient_of('Volume')]),
    'drizzle': ('fixed',    [_ingredient_of('Volume')]),

    # Small-amount addition.
    'sprinkle':('fixed',    [_ingredient_of('Mass', 'Count')]),

    # add(ingredient, [quantity, quantity, ...]) — ingredient first, optional quantities after.
    'add':     ('variadic', [_ingredient_of()], _quantity_of(), 1),

    # bake(target, temperature, duration).
    'bake':    ('fixed',    [_ingredient_of(),
                             _quantity_of('Temperature'),
                             _quantity_of('Duration')]),
}
```

The dispatcher distinguishes two signature kinds — `'fixed'` (positional predicate list) and `'variadic'` (required head predicates + tail predicate + min total arity) — with the per-arg shape-check delegated to predicate factories (`_ingredient_of(*dims)`, `_quantity_of(*dims)`). The body is generic dispatch over those two kinds, raising `TypeCheckError(line, 0, msg, error_code=13)` on every miss. Full implementation is in the share-URL turn 1; the table above is the design-significant payload.

The AI explicitly named its biggest guesses up front: *"`combine`/`mix`/`blend` accept any combination of dimensions. Spec might say 'same dimension across all args' (probably warranted for `blend` — you wouldn't blend Mass with Volume coherently)... `bake` is fixed-arity 3. Spec could equally model it as `bake(ingredient) { ... }` with a block body, or `bake(ingredient, duration)` with an implicit oven temperature. This is the biggest guess in the table."*

**Response (key part — turn 1, predicted verdicts on the four tests).** The AI walked through each test under its own rules:

| # | Test input | AI verdict | AI reason |
|---|---|---|---|
| 1 | `combine(flour: Ingredient<Mass>, salt: Ingredient<Pinch>)` | **accept** | variadic ≥2, both args are Ingredients, count ≥ 2 |
| 2 | `pour(flour: Ingredient<Mass>)` | **reject** | pour locked to `Ingredient<Volume>`; flour is Mass |
| 3 | `bake(x: any)` | **reject** | bake fixed arity 3, called with 1; arity check fires before per-arg |
| 4 | `blend(milk: Ingredient<Volume>, sugar: Ingredient<Mass>)` | **accept** | blend in the same any-mixed-dim bucket as combine/mix |

**Response (key part — turn 2, comparison against plan §2.3 + the typechecker.py stub).** I gave the AI the GitHub link to `part2_plan.md` (§2.3) and `src/recipix/typechecker.py`. The AI's self-categorized verdict:

> *"The verdict is uncomfortable but useful for your E3 entry — I diverged in three substantive ways, and two of four test predictions flip under §2.3."*

The three substantive divergences in its words:

1. **Per-verb table vs three-class collapse (the structural mistake).** *"I built a per-verb table. §2.3 collapses twelve verbs into three classes precisely to avoid the per-verb branch explosion. My table baked in twelve bespoke signatures. The plan calls this out as a deliberate design choice ('twelve special cases is ~12 branches in the checker… that buys no language-design credit'). I optimized for cooking semantics; you optimized for type-system parsimony."*

2. **Heterogeneous-group misses.** Partial credit on `combine`/`mix` (right in spirit but required ≥2 args instead of ≥1); `add` got a bespoke `(Ingredient, *Quantity)` signature that was invented from cooking intuition (spec puts it in the heterogeneous bucket); `sprinkle` was restricted to `Mass|Count` (spec admits any dimension including Pinch). The AI's quoted summary: *"I didn't recognize them as a class. The 'heterogeneous carve-out is decision #29' framing wasn't in my context, so I never had a reason to group them."*

3. **Homogeneous-group misses.** Most divergent. The AI locked per-verb dimensions on `pour`/`drizzle` (Volume), `knead`/`melt` (Mass); the spec just requires same-dimension across args with no per-verb constraint. `whisk` was unary fixed; spec puts it in homogeneous (≥1 arg, shared dim, no Pinch). `flip` was unary; spec is nullary. `blend` was lumped with combine/mix as any-mixed; spec puts it in homogeneous (same dim required). The AI also flagged it had missed decision #31: *"my predicates treated `Ingredient<D>` and `Quantity<D>` as distinct shapes with no coercion."*

The four-test verdicts under §2.3, by the AI's re-run:

| # | Test | AI cold | §2.3 verdict | Status |
|---|---|---|---|---|
| 1 | `combine(flour, salt)` | accept | accept | match (right verdict, wrong rule — AI's any-Ingredient permissiveness, not the decision-#29 carve-out) |
| 2 | `pour(flour)` | reject (Volume req) | **accept** (homogeneous, single arg trivially homogeneous) | **flipped** |
| 3 | `bake(x)` | reject (arity 3 ≠ 1) | reject (arity 0 ≠ 1) | match-by-coincidence (different reason, different message) |
| 4 | `blend(milk, sugar)` | accept (any-mixed) | **reject** (homogeneous, Volume≠Mass) | **flipped** |

The AI's framing of the score: *"If you're scoring strictly on 'did the AI produce the same accept/reject column as the spec,' 2/4. If you're scoring on 'did the AI produce the right verdict for the right rule,' 1/4."*

Then it volunteered a §2.3-aligned correction — its own rewrite, unsolicited:

```python
HETEROGENEOUS = {'combine', 'mix', 'add', 'sprinkle'}
HOMOGENEOUS   = {'pour', 'drizzle', 'whisk', 'blend', 'knead', 'melt'}
NULLARY       = {'bake', 'flip'}

def _check_ActionStmt(self, node):
    verb, args, line = node.verb, node.args, node.line
    arg_types = [self._type_of(a) for a in args]

    if verb in NULLARY:
        if len(args) != 0:
            raise TypeCheckError(line, 0,
                f"action verb '{verb}' takes no arguments (got {len(args)}); "
                f"use 'at'/'for' step modifiers for temperature and duration",
                error_code=13)
        return

    if len(args) < 1:
        raise TypeCheckError(line, 0,
            f"action verb '{verb}' requires at least 1 argument",
            error_code=13)

    if verb in HETEROGENEOUS:
        for i, t in enumerate(arg_types, start=1):
            head, _ = _parse_type(t)
            if head not in ('Ingredient', 'Quantity'):
                raise TypeCheckError(line, 0,
                    f"'{verb}' argument {i}: expected Ingredient or Quantity, got {t}",
                    error_code=13)
        return

    if verb in HOMOGENEOUS:
        dims = []
        for i, t in enumerate(arg_types, start=1):
            d = _project_to_quantity(t)         # decision #31 projection
            if d is None: ...   # rejected: not Ingredient/Quantity
            if d == 'Pinch': ...# rejected: Pinch forbidden in homogeneous
            dims.append(d)
        if len(set(dims)) > 1: ... # rejected: dimension mismatch
        return
```

The AI also flagged three sanity-check items on its corrected version — error-code routing (13 vs 1 for dimension mismatch in homogeneous), order of Pinch-check vs dim-match-check (it chose Pinch-first for diagnostic clarity), and whether the project file uses a `self._err` helper convention rather than direct `raise`. These are the right things to flag for handoff — they're the discretionary calls İsmail still owns.

**Accepted.** The structural skeleton of the dispatcher is reusable. The `_parse_type` helper (parses `"Ingredient<Mass>"` → `("Ingredient", "Mass")`) survives unchanged — it's a Recipix-agnostic utility. The AI's `error_code=13` choice is consistent with the spec. The corrected `_check_ActionStmt` body the AI produced in turn 2 is essentially what İsmail would write from plan §2.3 directly — three-class dispatch with implicit Ingredient→Quantity projection — and I've kept it as a starting point for the actual checker implementation. The Pinch-first-then-homogeneity check ordering it argued for is the more diagnostic one and I'd keep it.

The AI's flagging of the prompt ambiguity (Pinch in D vs. not in D) before answering is also worth keeping in the entry — it's the kind of behavior the depth-of-reflection rubric rewards, and the spec should clarify in v4.2 whether `Ingredient<Pinch>` is a well-formed annotation given that Pinch is a primitive, not a dimension.

**Rejected / modified.** Everything in the cold first-pass except the dispatcher skeleton:

1. **The twelve-row `VERB_SIGS` table.** Replaced wholesale with the three-class form. The plan §2.3 rationale (cuts ~12 checker branches, ~24 tests, plus the exam-memorization load) is exactly the reason this collapse exists; the cold AI couldn't see that reason and reached for cooking-semantics-as-types.

2. **Per-verb dimension locks** on `pour` (Volume), `drizzle` (Volume), `knead` (Mass), `melt` (Mass), `sprinkle` (Mass|Count). §2.3 has no per-verb dimension; the homogeneous class requires same-dimension across args, period. Under the spec, `pour(flour)` with flour-as-mass type-checks, which is linguistically odd but is the deliberate cost of the three-class collapse.

3. **`combine`/`mix`/`blend` min-arity ≥2.** Spec is ≥1. The AI inferred ≥2 from "multi-ingredient mixing" semantics; the spec is more permissive.

4. **`add` as `(Ingredient, *Quantity)`.** Bespoke signature, no spec basis. Replaced with the heterogeneous-class default (any Ingredient/Quantity, any dim).

5. **`bake` as fixed arity 3 `(Ingredient, Quantity<Temperature>, Quantity<Duration>)`.** Spec lifts temperature and duration out into `at`/`for` step modifiers (decision #23) and leaves bake nullary. The AI's biggest flagged guess was its biggest miss; would have been caught by reading spec §7 ("step declaration: `step <string_lit> [ at <expr> ] [ for <expr> ] { <step_actions> }`").

6. **`flip` as unary.** Spec is nullary. The AI grouped it with `whisk` from cooking intuition (single-arg action). Both `flip` and `bake` belong to the same nullary class — neither takes an argument because their parameters are step modifiers, not call arguments.

7. **`whisk` as unary instead of homogeneous.** Spec puts `whisk` in the homogeneous class (≥1 arg, shared dim, no Pinch). A subtle miss because `whisk(flour)` looks unary at the call site, but `whisk(flour, sugar)` should also type-check under §2.3 — homogeneous verbs are variadic.

8. **Missing implicit Ingredient → Quantity projection (decision #31).** The AI's predicates treated `Ingredient<D>` and `Quantity<D>` as distinct shapes with no coercion. Under decision #31, an Ingredient in arithmetic/comparison/action context projects to its `Quantity<D>` field. The homogeneous class invokes this projection to compute the dimension to compare.

**Errors caught.** The four E3-mandated test inputs surface the errors cleanly; consolidated to the five concrete findings I'd defend on the exam:

1. **Test 2 (`pour(flour)`) verdict flipped under §2.3.** The AI rejected because it had hard-coded `pour: Volume`. Spec accepts because pour is homogeneous and a single-arg call trivially satisfies homogeneity. This is the **single best illustration of the per-verb-vs-per-class trade-off**: the spec gives up English-language verb semantics ("pour" implying liquid) to buy type-system parsimony. The journal needs this exchange visibly because it's a likely exam question — *"why does pour(flour) type-check in your language?"* — and the answer is "because §2.3 deliberately chose the looser rule, see decision #29 rationale, this is a v2 refinement candidate."

2. **Test 4 (`blend(milk, sugar)`) verdict flipped under §2.3.** AI grouped blend with combine/mix as heterogeneous; spec puts it in homogeneous. Different verdict (accept vs reject), different rule. The AI's cooking intuition was wrong about which group blend belongs to — the spec uses physical-coherence (you can't blend across dimensions without a result that's nonsense) as the homogeneity argument, not the literal cooking sense of "blender = liquid medium."

3. **Test 3 (`bake(x)`) matched verdict for the wrong reason.** AI rejected for arity 3 vs 1; spec rejects for arity 0 vs 1. The accept/reject column matches by coincidence. This is the most subtle finding because a strict-output-checking grader would mark it correct; a strict-reasoning grader would mark it wrong. Worth flagging in the writeup.

4. **Implicit Ingredient → Quantity projection (decision #31) absent.** The AI's predicates couldn't handle an Ingredient appearing in a position that expects a Quantity. Under decision #31, the homogeneous-class check projects through automatically. The AI's predicates would have rejected `whisk(flour, salt)` (`Ingredient<Mass>` and `Ingredient<Pinch>`) for "type mismatch with `Ingredient<Volume>`" even when the user passed the same dimension across both. This bug isn't surfaced by the four test inputs but would surface in real programs.

5. **Per-verb cooking-semantics signatures over-specify against the spec's deliberate type-system parsimony.** The structural finding from the AI's own self-critique: *"I optimized for cooking semantics; you optimized for type-system parsimony."* This is the single most defensible journal-quote line from the session — it names exactly the optimization-target divergence that the rubric will probe.

**Reflection.** The biggest takeaway from this one is that the AI's design instinct — "more rules cover more cases" — is exactly opposite to the spec's instinct of "fewer rules cover the same cases at lower exam and maintenance cost." Twelve per-verb signatures look like authority on first read; the AI's own retrospective lands on this in one line: *"I optimized for cooking semantics; you optimized for type-system parsimony."* That framing is the one I want in §4.8 and in my head for the oral. The per-verb cooking-semantics signatures aren't wrong because the cooking semantics are wrong — they're wrong because pricing language-design decisions in cooking-intuition currency means the action-verb checker has twelve places it can break instead of three. The spec's three-class collapse trades verb-meaning-faithfulness for fewer-places-to-be-wrong. The thing the journal needs to show is that the AI's cold-reasoning instinct went the other way. The other half of the experiment is what happened after the spec came into view: the AI wrote its own §2.3-aligned correction, unsolicited, and got it essentially right. AI implements decisions well. It does not invent them well. That's the working pattern I'll keep across the rest of Part 2 — I drive the decisions, the AI drives the implementation, and the journal is the record of what happens when those roles slip.
