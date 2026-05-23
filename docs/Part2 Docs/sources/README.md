# LaTeX sources for the Part 2 deliverable PDFs

The five `.tex` files in this folder are the canonical sources for the
five rendered PDFs sitting one level up:

| Source | Renders to | Type |
|---|---|---|
| `D1.tex` | `210104004132-1901042652_D1_P2.pdf` | joint pair — design specification |
| `D3.tex` | `210104004132-1901042652_D3_P2.pdf` | joint pair — test report |
| `D4.tex` | `210104004132_D4_P2.pdf`            | individual — Berk's AI journal continuation |
| `D5.tex` | `210104004132_D5_P2.pdf`            | individual — Berk's retrospective + self-assessment |
| `D6.tex` | `210104004132-1901042652_D6_P2.pdf` | joint pair — contribution report |

## Build

No external bibliography or custom class. Standard `pdflatex` or any
modern distribution (TeX Live, MiKTeX, MacTeX) with `lmodern`,
`microtype`, `listings`, `geometry`, `fancyhdr`, `hyperref`, `titlesec`,
`booktabs`, `longtable`, `enumitem`, `xcolor`, `babel`, and `tcolorbox`
(D4 only) is enough.

```bash
# From this folder:
for f in D1 D3 D4 D5 D6; do pdflatex "$f.tex" && pdflatex "$f.tex"; done

# Or with latexmk:
for f in D1 D3 D4 D5 D6; do latexmk -pdf "$f.tex"; done
```

Two `pdflatex` passes are needed for cross-references and the table of
contents (where present) to resolve. The rendered PDFs in the parent
folder are the canonical submission artefacts; this folder exists so
those PDFs can be regenerated faithfully.
