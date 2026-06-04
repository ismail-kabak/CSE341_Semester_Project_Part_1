# Berk — One-Sheet Cheat (my work, in prose)

*Single A4 side. Prose explanations, not code. Each block is something
a grader can ask me about my own contributions.*

---

**MY ROLE.** I built the parser (Part 1), the interpreter, and the
rendering layer (Part 2). I also wrote D1 §4.3 (EBNF), §4.4 (operational
semantics for scale and foreach), §4.7 (expressions and assignment), and
the §4.8 design-rationale paragraphs for precedence, short-circuit,
operand order, and assignment-as-statement. In D3 I owned Sample 1
(pancakes) and Sample 2 (smoothie). The type checker is İsmail's.

**THE INTERPRETER IS A TREE-WALKER.** It visits each AST node and
dispatches to a handler method named after the node type. It does not
re-derive types — it trusts that the type checker already ran and proved
every expression well-typed, so the interpreter can assume operands have
compatible dimensions and skip defensive checks. The interpreter and the
type checker share one Environment class for scope; I store runtime
values in it, İsmail stores type strings in it, but the scoping logic
(parent-pointer chain, define/lookup) is written once.

**WHY return USES AN EXCEPTION.** A return statement can sit inside
nested if/repeat/foreach blocks, so to jump out of arbitrary nesting
back to the function-call site I raise a ReturnException carrying the
value. The function-call handler catches it and uses the carried value
as the call's result. The alternative — threading a "did we return yet"
flag up through every loop and conditional — is far messier. This is a
standard interpreter technique for non-local control flow.

**HOW SCALE WORKS (and why Sample 1 shows 6 cycles, not 4).** When a
recipe is first instantiated, I evaluate its step bodies *eagerly* using
the original servings value — so pancakes(servings:4) builds a step body
with four pour/flip cycles. Crucially, the resulting recipe value also
*snapshots* the raw step declarations and the original parameter values.
When scale(r, by:1.5) runs, I compute the new servings (banker's
rounding of 4×1.5 = 6), scale the Mass/Volume/Count ingredients while
leaving Temperature/Duration/Pinch untouched, then build a fresh
environment in which servings is rebound to 6 and re-execute the step
bodies against it. Now "repeat servings times" reads 6, so the step
unrolls into six cycles. This is the user-intuitive reading: doubling a
recipe doubles the work, not just the header number. Referential
transparency is preserved because scale builds an entirely new recipe
value and never mutates the original — the re-execution happens inside
the new value's construction (decision #25).

**WHY BANKER'S ROUNDING for scaled servings.** I round servings with
round-half-to-even rather than truncating or ceiling. Truncating
scale(recipe-of-3, by:0.5) would give 1 serving — a 33% loss that
silently halves the cook. Ceiling would over-order ingredients relative
to the servings shown. Banker's rounding is statistically unbiased on
half-way values, so over many scalings it neither systematically loses
nor inflates servings.

**WHY SCALE LEAVES TEMPERATURE AND DURATION ALONE.** Mass, Volume, and
Count are *extensive* — doubling the recipe doubles them. Temperature
and Duration are *intensive* — a cake baked at 180°C for 30 minutes does
not become 360°C for 60 minutes when you double the batch. So scale
multiplies the extensive dimensions and the servings count, and leaves
the intensive ones exactly as written.

**HOW SUBSTITUTE WORKS (and Sample 2's two-vs-one oat_milk).** Substitute
looks up the original and replacement ingredients by bare identifier in
the recipe's binding table (they're identifiers, not expressions, by
grammar — decision #35), multiplies the original's quantity by the
ratio, and relabels the original's slot to use the replacement's name.
Then it *pops* the standalone replacement binding, because the
replacement has been consumed into the substituted slot. That pop is why
Sample 2's vegan variant shows only one oat_milk line. The non-vegan
variant runs the plain recipe with no substitution, so both milk and the
pre-declared oat_milk appear — oat_milk has to be declared inside the
recipe so the call-site substitute can name it, but when unused it just
sits there. This is the no-"this" design: a recipe can't refer to
itself during construction, so alternatives live inside it and the
choice is made at the call site (decisions #25, #28).

**WHY SUBSTITUTE DOESN'T RE-EXECUTE STEP BODIES BUT SCALE DOES.** Scale
changes a value the step body reads (servings), so the body must be
re-run to reflect it. Substitute only swaps an ingredient binding; the
step actions reference ingredients by their binding, so re-rendering the
already-built actions through the new binding table is enough — no
re-execution needed.

**THE RENDERING HEURISTIC.** Internally every quantity is stored in its
base unit (grams, millilitres, minutes) so arithmetic is always
consistent. Rendering is the only place I convert back to a
reader-friendly unit: I show grams below 1000 and kilograms above,
millilitres below 1000 and litres above, minutes below 60 and hours
above. Count and Temperature have no smaller unit so they print as-is,
and a Pinch prints as "a pinch." I strip trailing zeros so 300.0 prints
as 300. The thresholds are pure readability — they don't affect
semantics, only display.

**THE PROJECTION RULE I IMPLEMENT (decision #31).** Inside a step body a
user can write "flour + 100 g" even though flour is an Ingredient and
100 g is a Quantity. In my BinaryOp handler, if either operand is an
Ingredient I replace it with its quantity field before doing the
arithmetic. This is the implicit Ingredient-to-Quantity projection —
it's what keeps recipe arithmetic readable without forcing
quantity_of() everywhere. The explicit form quantity_of(flour) + 100 g
means exactly the same thing.

**PARSER DECISIONS I ENFORCE.** Quantity literals are two tokens, so
after a number I peek for a unit keyword and glue them into one quantity
node (decision #7). Comparisons are non-associative: after I parse one
comparison operator and its right side, I check for a second comparison
and raise a parse error if I find one — that's what makes "a < b < c" a
parse error rather than a runtime type error (decision #17). If/else
both require braces, which I enforce by demanding a left brace on each
branch, eliminating the dangling-else problem by construction (#20).
Step modifiers must be at-before-for, and I raise an error if for comes
first (#23). quantity_of has its own dedicated production at the unary
level so it can never be mistaken for an ordinary function call (#34),
and the two ingredient slots in substitute are required to be bare
identifiers, not arbitrary expressions (#35).

**MY §4.7 / §4.8 DESIGN DEFENSES (the four I have to own).**

*Non-associative comparison (#17).* Left-associative chaining would
parse "1 kg < flour < 2 kg" as "(1 kg < flour) < 2 kg," evaluate the
first comparison to a bool, then try to compare a bool against a Mass —
a confusing runtime type error. Making comparisons non-associative
catches the mistake at parse time with a clear message. The cost is that
users wanting a range write "(1 kg < flour) && (flour < 2 kg)"
explicitly — a small writability price for reliability and better
errors.

*Short-circuit && and || (#19).* These stop evaluating once the left
operand decides the result. It matches programmer expectation and gives
a safety bonus: "x != 0 && y / x > 1" never divides by zero. I made them
left-to-right so they share one mental model with my operand-evaluation
rule.

*Operand evaluation order locked left-to-right (#18).* C leaves operand
order unspecified so compilers can reorder for speed, but that means the
same program can report different runtime errors on different platforms.
Since Recipix prioritises reliability over performance, I lock
left-to-right so error messages cite predictable line numbers. Because
Recipix has no side effects, the order is actually unobservable on
values — it only matters for which error fires first.

*Assignment is a statement, not an expression (#27).* let is the only
binding form. This makes every expression referentially transparent —
the same expression in the same scope always yields the same value — and
it's what lets my left-to-right operand rule be unobservable, since no
operand can mutate anything. The trade-off is no "while ((x = read()))"
pattern, but v1 has no I/O loop anyway. If v2 ever adds mutation, this is
the first decision to revisit.

**REFERENTIAL TRANSPARENCY — why my interpreter is simple.** Three
decisions together guarantee it: parameters are by-value (no caller-
visible mutation), scale and substitute are functional (they build fresh
recipe values, never mutating), and assignment is a statement (no
expression has a value side-effect). Because of this, my BinaryOp
handler never has to worry that evaluating the left operand might change
what the right operand sees — that's why the operational semantics in
§4.4 stay clean.

**SAMPLE NUMBERS TO MEMORISE.** Sample 1: scale(pancakes(servings:4),
by:1.5) → serves 6, flour 300 g, milk 360 ml, eggs 3, salt a pinch, and
six pour/flip cycles. Sample 2 vegan: one oat_milk line (milk slot
relabelled, standalone oat_milk popped). Sample 2 non-vegan: both milk
and oat_milk shown. Sample 3 (İsmail's type-error demo, but I should
know it): "type error at line 13, col 0: dimension mismatch: cannot +
Mass and Volume."
