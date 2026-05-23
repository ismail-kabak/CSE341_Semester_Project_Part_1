# Recipix — `docs/` index

Map of the documentation tree.

| Path | What it is |
|---|---|
| `recipix_v4_1_spec.md` | The locked v4.1 language specification — single source of truth for the language design. |
| `part2_plan.md` | The joint Part-2 runtime contract between Berk and İsmail. Rev 3. |
| `ISMAIL_GUIDE.md` | Companion guide written when İsmail's half of Part 2 needed onboarding. |
| `CSE341_Project_Handout.pdf` | Course handout (assignment text). |
| `CSE341_Submission_Guide.pdf` | Course submission-format guide. |
| `210104004132_D4_P2.md` | Markdown source for Berk's D4 AI usage journal (continuation). |
| `210104004132_D5_P2.md` | Markdown source for Berk's D5 retrospective + self-assessment. |
| `D1_P2_Berk_sections.md` | Markdown working draft of Berk's portion of the joint D1. |
| `D3_P2_Berk_sections.md` | Markdown working draft of Berk's portion of the joint D3. |
| `Part1 Docs/` | Part 1 deliverables (D1–D6 PDFs/markdowns) as submitted on 8 May 2026. |
| `Part2 Docs/` | Part 2 deliverables (D1–D6 PDFs + D2 source zip + Claude Code session transcripts) as submitted on 22 May 2026. |
| `Part2 Docs/sources/` | LaTeX source files for the Part-2 deliverable PDFs, with build instructions. |
| `notes/` | Exam-prep notes (language, lexer, parser, mock exams). |

## Reading order for a new visitor

1. **`recipix_v4_1_spec.md`** — what the language *is*.
2. **`Part2 Docs/210104004132-1901042652_D1_P2.pdf`** — the formal design specification with semantics, type system, and design rationale.
3. **`Part2 Docs/210104004132-1901042652_D3_P2.pdf`** — three sample programs with rendered output + the dimensional type-error demonstration.
4. The Part 1 PDFs in `Part1 Docs/` if you want to see how the parser was scoped before the type checker / interpreter landed.

The source code lives at the repo root under `../src/`.
