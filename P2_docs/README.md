# P2_docs — LaTeX projects for D1 and D3

This folder contains the LaTeX sources for the two written deliverables
of the Recipix Part 2 submission:

| Folder | Deliverable | Final PDF name |
|---|---|---|
| `D1/` | D1 — Design Specification (Part 2) | `1901042652-210104004132_D1_P2.pdf` |
| `D3/` | D3 — Test Report (Part 2) | `1901042652-210104004132_D3_P2.pdf` |

Both PDFs are joint pair deliverables — only one partner uploads each
to Microsoft Teams.

## Build instructions

Each LaTeX project is a single `.tex` file with no external bibliography
or custom class. Standard `pdflatex` (TeX Live, MiKTeX, MacTeX, or any
modern distribution with `lmodern`, `microtype`, `listings`, `geometry`,
`fancyhdr`, `hyperref`, `titlesec`, `booktabs`, `longtable`,
`enumitem`, `xcolor`, and `babel`) builds them with a single pass:

```bash
# From the repo root:
cd P2_docs/D1
pdflatex D1.tex
pdflatex D1.tex   # second pass for cross-references / TOC if added

cd ../D3
pdflatex D3.tex
pdflatex D3.tex
```

Or use `latexmk` for automatic pass management:

```bash
cd P2_docs/D1
latexmk -pdf D1.tex

cd ../D3
latexmk -pdf D3.tex
```

After the build, rename the output PDFs to the submission filenames
listed above and upload to the Teams Assignment for Part 2.

## What's in each document

### D1 — Design Specification (Part 2)

Eight sections per handout §4 [P2]:

1. Language Overview — domain, sample program, Sebesta §1.3 evaluation
   criteria, what makes Recipix a DSL.
2. Lexical Structure — token categories with regex patterns; the
   two-token quantity literal rule (decision #7).
3. Syntax — complete EBNF grammar with annotated design decisions
   (#7, #17, #20, #23, #34, #35).
4. **Semantics** [P2] — operational semantics for `scale` and `foreach`,
   covering the step-body re-execution rule and the homogeneous-list
   iteration semantics.
5. **Type System** [P2] — primitive types, strong typing, coercion rules
   (within-dimension + int→float), type equivalence split (structural
   for Quantity/Ingredient/List, name for Recipe), structured-type
   design decisions per Sebesta §6.5–6.7.
6. Names, Binding, Scope, Lifetime — legal identifiers, compile-time vs.
   run-time bindings, static lexical scoping, no-shadowing,
   single-assignment, lifetime table.
7. **Expressions & Assignment** [P2] — precedence/associativity table,
   short-circuit `&&`/`||`, left-to-right operand evaluation,
   assignment-as-statement (decision #27).
8. **Design Rationale** [P2] — seven paragraphs in each author's voice
   covering coercion, equivalence, structured-type, precedence,
   short-circuit, operand order, and assignment-as-statement.

### D3 — Test Report (Part 2)

Six sections:

1. Overview — what the report demonstrates, reproduction commands.
2. Sample 1 — Pancakes (function + recipe + scale + evaluate). Source,
   rendered output, 3–5 sentence discussion of the step-body
   re-execution under scaled servings.
3. Sample 2 — Smoothie (substitution at the call site). Source,
   rendered output for both `evaluate` variants, discussion of
   bare-IDENT slot resolution and the no-`this` design.
4. Sample 3 — Dimension-mismatch type error. Source, verbatim
   type-error trace, discussion tying the trace to decision #31's
   implicit Ingredient→Quantity projection.
5. Parse-error fixtures (carryover from Part 1) — five malformed
   programs with their parser error messages.
6. Summary — test count, coverage statement.
