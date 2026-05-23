# Recipix

A small domain-specific language for parameterized recipes with
dimensional types. Every ingredient quantity carries a dimension
(`Mass`, `Volume`, `Count`, `Temperature`, `Duration`); the type
system enforces dimensional correctness at compile time, so adding
grams to milliliters or substituting a volume for a mass is rejected
before the program runs.

Designed and implemented as the CSE 341 Concepts of Programming
Languages semester project at Gebze Technical University, Spring 2026.

## Example

```recipix
function half(n: int) -> int { return n / 2 }

recipe pancakes(servings: int) serves servings {
    ingredient flour : 50 g * servings
    ingredient milk  : 60 ml * servings
    ingredient eggs  : half(servings) * 1 count
    ingredient salt  : 1 pinch

    step "Mix dry"     { combine(flour, salt) }
    step "Add wet"     { combine(milk, eggs) }
    step "Cook batches" at 180 °C for 3 min {
        repeat servings times { pour(milk) flip() }
    }
}

evaluate scale(pancakes(servings: 4), by: 1.5)
```

The locked language specification lives at
[`docs/recipix_v4_1_spec.md`](docs/recipix_v4_1_spec.md).

## Quick start

Python 3.11+ and the standard library. No third-party dependencies.

```bash
# Parse a file
python main.py docs/../src/tests/fixtures/valid/sample1.rcx

# Type-check only
python main.py --typecheck src/tests/fixtures/valid/sample1.rcx

# Run end-to-end (parse + type-check + interpret + render)
python main.py --run src/tests/fixtures/valid/sample1.rcx

# Run the full test suite
python -m unittest discover src/tests
```

The test suite reports **152 tests, 0 failures** at submission.

## Architecture

A four-phase compiler/interpreter pipeline:

```
source → lexer → parser → type checker → interpreter → rendered output
```

| Phase | Module |
|---|---|
| Lex | `src/lexer.py` |
| Parse | `src/recipix/parser.py` |
| Type-check | `src/recipix/typechecker.py` — all 19 spec §10 errors enforced |
| Interpret | `src/recipix/interpreter.py` |
| Render | `src/recipix/rendering.py` |

Shared infrastructure: `src/recipix/environment.py` (lexical scope
chain, used by both checker and interpreter),
`src/recipix/runtime_values.py` (`RtQuantity`, `RtIngredient`,
`RtRecipe`, `RtList`, `PINCH`, plus the unit-conversion table),
`src/recipix/errors.py` (`ParseError`, `TypeCheckError`,
`RuntimeRecipixError`).

## Repository layout

```
.
├── main.py                       CLI entry point
├── src/
│   ├── lexer.py
│   ├── recipix/                  parser · ast · typechecker · interpreter · rendering
│   └── tests/                    lexer · parser · interpreter · regression suites
└── docs/
    ├── README.md                 docs-folder index
    ├── recipix_v4_1_spec.md      locked language specification (v4.1)
    ├── part2_plan.md             joint Part-2 runtime contract (Rev 3)
    ├── ISMAIL_GUIDE.md           type-checker build companion guide
    ├── Part1 Docs/               Part 1 deliverables (D1–D6) as submitted 8 May 2026
    ├── Part2 Docs/               Part 2 deliverables (D1–D6) as submitted 22 May 2026
    │   └── sources/              LaTeX sources for the Part-2 PDFs
    └── notes/                    exam-prep notes
```

## Authors

- **Berk Hakan Öge** (210104004132) — parser, interpreter, rendering, half of D1 / D3, D4, D5, half of D6.
- **İsmail Kabak** (1901042652) — lexer, type checker, half of D1 / D3, D4, D5, half of D6.

## Status

Submitted in two parts:

- **Part 1** (8 May 2026): language spec, lexer, parser, AST, test fixtures.
- **Part 2** (22 May 2026): type checker, interpreter, rendering, full
  documentation (D1 design spec, D2 source zip, D3 test report, D4 AI
  usage journal, D5 retrospective + self-assessment, D6 contribution
  report).

## License

Submitted as coursework for CSE 341 Spring 2026 at Gebze Technical
University. No external license granted.
