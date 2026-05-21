# Recipix Lexer — Brief Study Notes

> İsmail's component, not yours — but you consumed its output as parser
> owner, so you understand the **token contract** intimately. The examiner
> may ask you basic Ch. 4 lexical-analysis questions or interface questions
> ("how does your parser get tokens from the lexer?"). This file is short
> on purpose: it covers what's defensible for a parser owner, not what
> İsmail would defend.
>
> Honest framing for the exam: if a deep lexer-internals question comes up,
> **say so** — "the lexer was my partner's component; I can speak to the
> token contract we agreed on and the general Ch. 4 principles, but for
> implementation specifics I'd defer." That earns more credit than guessing.

---

## 1. What a lexer *is* (Sebesta §4.2)

The lexical analyzer (scanner) converts a **stream of characters** into a
**stream of tokens**. It's the first phase of compilation. Its responsibilities:

- **Group characters into lexemes** (the literal substring matched).
- **Classify each lexeme** as a token (lexeme + category tag).
- **Skip whitespace and comments** — these never reach the parser.
- **Report lexical errors** with line numbers (unrecognized characters,
  unterminated strings, malformed numbers).

**Lexeme vs. token** — Sebesta's distinction:
- **Lexeme**: the actual substring of source code, e.g. `200`, `recipe`, `<=`.
- **Token**: the categorized unit — `INT_LIT(200)`, `recipe`-keyword, `LTE`.
  A token is "lexeme + classification."

### Why a separate phase?
- **Simplicity**: lexing uses regular grammars (Chomsky type 3); parsing uses
  context-free grammars (type 2). Keeping them separate means each phase
  uses the simplest formalism that suffices.
- **Performance**: lexer is the fastest phase; it filters out whitespace and
  comments so the parser never sees them.
- **Engineering**: state diagrams / DFAs implement lexers efficiently;
  recursive descent or LR tables implement parsers. Different toolkits.

---

## 2. Recipix's token categories (recap from the language notes)

The token-type categories defined in `tokens.py`:

| Category | Token type constant | Example |
|---|---|---|
| Identifier | `IDENT` | `flour`, `pancakes` |
| Integer literal | `INT_LIT` | `200`, `0` |
| Float literal | `FLOAT_LIT` | `1.5`, `0.75` |
| String literal | `STRING_LIT` | `"Mix dry"` |
| Boolean literal | `BOOL_LIT` | `true`, `false` |
| Unit keyword | `UNIT_KW` | `g`, `ml`, `°C`, `tsp` |
| Type-name keyword | `TYPE_KW` | `int`, `Mass`, `Volume` |
| Action-verb keyword | `ACTION_KW` | `combine`, `bake` |
| Reserved keyword | (token type IS the keyword) | `recipe`, `if`, `let` |
| Operator | `PLUS PLUS MINUS STAR SLASH EQ NEQ LT LTE GT GTE AND OR NOT ASSIGN` | `+`, `==`, `<=` |
| Separator | `LPAREN RPAREN LBRACE RBRACE LBRACKET RBRACKET COMMA COLON ARROW` | `(`, `{`, `,`, `->` |
| End-of-file | `EOF` | (synthetic terminator) |

**The reserved-keyword convention.** For reserved keywords like `recipe` or
`if`, the **token type IS the keyword string** — e.g. `Token('recipe', 'recipe', line)`.
This makes the parser's `_check('recipe')` calls read naturally: it's
checking the token type directly against the keyword string.

For type/action/unit categories, the parser uses the category constant —
e.g. `_check(TYPE_KW)` — because the parser usually doesn't care *which*
type or unit, only that some type appeared.

---

## 3. Regular expressions for Recipix tokens

You should be able to write these on the exam (Sebesta §4.2):

| Token | Regex |
|---|---|
| Identifier | `[a-zA-Z_][a-zA-Z0-9_]*` |
| Integer literal | `[0-9]+` |
| Float literal | `[0-9]+\.[0-9]+` |
| String literal | `"[^"\n]*"` (no escapes in v1; newlines inside `"..."` are errors) |
| Whitespace | `[ \t\r\n]+` (skipped) |
| Line comment | `//[^\n]*` (skipped) |

**Note:** Recipix's float literal requires a digit on *both* sides of the dot
— `1.5` is valid, `1.` and `.5` are not. This is a deliberate readability
choice (Sebesta §1.3.1: ambiguity in numeric literal forms is a readability
hazard).

---

## 4. The lexer's algorithm — at the conceptual level

The Recipix lexer is hand-written, not table-driven. Its top-level loop:

1. **Skip** whitespace and `//` comments.
2. If end-of-input, return `EOF` token.
3. Look at the next character to dispatch:
   - Digit → scan a number
   - `"` → scan a string
   - Letter or `_` → scan a word, then classify
   - `°` → scan the `°C` unit token
   - Operator/separator characters → try two-char first (maximal munch),
     then single-char
4. Repeat.

This is a **direct hand-coded scanner** — not a generated DFA, but it
implements the same logic that a DFA would. Each "scan" function is a
small loop that consumes characters as long as they fit the current
lexeme's pattern. This corresponds to Sebesta's "ad-hoc lexer" approach
described in §4.2.

### Maximal munch (§4.2 — the lexer's longest-match rule)

When multiple tokens could match a prefix, take the **longest** one. Recipix
applies this in two places:

1. **Two-char operators tried before one-char.** When the lexer sees `<`,
   it first peeks for `=` to decide between `LT` and `LTE`. Without
   maximal munch, `<=` would lex as `<` followed by `=` (two tokens) —
   wrong.
2. **Keywords vs. identifiers.** A word is scanned greedily as a maximal
   `[a-zA-Z_][a-zA-Z0-9_]*` lexeme, *then* classified. So `recipe` lexes
   as one word and is classified as a reserved keyword; `recipe_v2` lexes
   as one word and is classified as `IDENT` (because it isn't in the
   reserved set).

---

## 5. Keyword pre-emption — the classification cascade

After a word is scanned, the lexer classifies it by trying categories in
this order:

```
true / false    → BOOL_LIT
unit keyword    → UNIT_KW
type-name kw    → TYPE_KW
action verb     → ACTION_KW
reserved kw     → Token(word, word, line)
otherwise       → IDENT
```

**Why this order matters:** every keyword and unit name is **reserved** —
the user cannot use `recipe`, `g`, `Mass`, or `combine` as an identifier.
The cascade ensures the lexer always picks the keyword interpretation
first; only words that match *no* keyword category fall through to
`IDENT`. This is Sebesta's **reserved word** policy (§5.2), as opposed
to the much rarer **predefined identifier** policy (where keywords could
in principle be redefined by the user).

**Defense for the exam:** reserved words simplify parsing because the
parser knows, just from the token type, that `recipe` introduces a recipe
declaration. With predefined identifiers, the parser would need symbol
table information to know whether a name still meant what it did
"originally."

---

## 6. The two-token quantity literal (Decision #7) — at the lexer level

This is **the one decision where the lexer encodes a Recipix-specific rule.**

The lexer scans `200 g` as **two tokens**:
- `Token(INT_LIT, 200, line)`
- `Token(UNIT_KW, 'g', line)`

It scans `200g` (no space) as a **lexical error** with a clear message
recommending the correct form.

**Why an error and not just two tokens?** Without the rule, `200g` could
tokenize as `INT_LIT(200)` followed by `IDENT('g')` — but `g` is reserved
as a unit keyword. The lexer detects this case explicitly (in
`_check_no_unit_glued`) and produces a useful diagnostic instead of
silently producing an unparseable token sequence.

**What about `200foo` (a non-unit word after a number)?** That's *not* an
error. It tokenizes as `INT_LIT(200)` followed by `IDENT('foo')` and the
parser will report a syntax error in context. The lexer only special-cases
the unit-keyword-after-number case because that's the user-error pattern
Decision #7 was designed to catch.

---

## 7. The `°C` token — Unicode at the lexical level

`°C` is a **single token**: `Token(UNIT_KW, '°C', line)`. The lexer has a
dedicated `_scan_degree_c` function. The `°` character by itself cannot
appear in a Recipix program — it must always be followed by `C`. This is
defensive against Unicode classification surprises (the degree symbol
isn't in any of Python's `isalpha`/`isdigit` categories, so without an
explicit case it would fall through to the "unexpected character" error).

---

## 8. Error reporting

The lexer raises `LexerError(message, line)` for:
- Unrecognized characters (e.g. `@`, `#`)
- Unterminated string literals (newline inside `"..."`, or EOF before
  closing `"`)
- `°` not followed by `C`
- A number glued directly to a unit keyword (Decision #7)

Format: `Lexer error at line {line}: {message}`. (Your D5 retrospective
notes that this format differs slightly from the parser's
`parse error at line {line}, col {col}: ...` — a Part 2 cleanup item.)

---

## 9. The token contract you depended on

As parser owner, this is what mattered to *you*:

**Every token exposes three fields:**
- `.type` — string constant (e.g. `'IDENT'`, `'INT_LIT'`, or the keyword
  string itself for reserved words)
- `.value` — the Python-typed value (int for `INT_LIT`, str for `IDENT`,
  bool for `BOOL_LIT`, etc.)
- `.line` — 1-based line number where the token started

**Three category-vs-content conventions you relied on:**
1. **Reserved keywords:** token type IS the keyword string. So
   `_check('recipe')` matches the keyword `recipe`.
2. **Type/Action/Unit keywords:** token type is the *category constant*
   (`TYPE_KW`, `ACTION_KW`, `UNIT_KW`); the specific word is in `.value`.
3. **EOF is a real token.** The lexer terminates the stream with
   `Token(EOF, None, line)` — the parser never has to check for "ran out
   of tokens"; it just checks `_check(EOF)`.

This contract was **negotiated and frozen** (via the shared `tokens.py`
file) before either of you started writing. That's why integration was
painless — both sides imported the same constants.

---

## 10. Likely exam questions

**Q: What's the difference between a lexeme and a token?**
A: A lexeme is the substring of source code that was matched. A token is
the lexeme plus its category — e.g. the lexeme `200` matched as the token
`INT_LIT(200)`. Sebesta §4.1: "tokens are categories of lexemes."

**Q: Why is your lexer a separate phase from the parser?**
A: Three reasons. **Theoretical**: lexing uses regular grammars while
parsing uses context-free grammars, so each phase uses the simplest
formalism. **Engineering**: the lexer filters out whitespace and
comments, so the parser never deals with them. **Performance**: the
lexer is the fastest pass, processing characters one at a time without
backtracking.

**Q: Is `200g` a valid Recipix lexeme?**
A: No. Decision #7 requires whitespace (or a comment) between the number
and the unit. `200g` is a lexical error. The lexer detects the case
explicitly and produces a message recommending `200 g`. The motivation
is to keep the lexer's number-scanning state machine independent of the
keyword-scanning state machine — splitting numbers and units into separate
tokens preserves that orthogonality.

**Q: How does the lexer distinguish `recipe` from a user identifier?**
A: After scanning a maximal `[a-zA-Z_][a-zA-Z0-9_]*` word, the lexer
classifies it through a cascade: BOOL_LIT, UNIT_KW, TYPE_KW, ACTION_KW,
RESERVED keyword, otherwise IDENT. `recipe` matches the reserved-keyword
set, so it produces `Token('recipe', 'recipe', line)`. A word like
`recipe_v2` doesn't match any keyword category and produces `Token(IDENT,
'recipe_v2', line)`.

**Q: What's "maximal munch" and where does your lexer use it?**
A: Maximal munch is the rule that when multiple tokens could match a
prefix, the lexer takes the longest match. Recipix applies it for
two-character operators: when scanning `<=`, the lexer first checks
whether the next char is `=` before falling back to `<`. Without this
rule, `<=` would lex as two tokens.

**Q: What's the regular expression for a Recipix identifier?**
A: `[a-zA-Z_][a-zA-Z0-9_]*`. ASCII only, case-sensitive. The first
character must be a letter or underscore; subsequent characters may also
be digits.

**Q: Could you implement your lexer with a DFA?**
A: Yes. The lexer's logic is regular — it consumes characters and
transitions between states based on what it has seen. Every regular
grammar has an equivalent DFA (Sebesta §4.2). The hand-written version
is essentially a manual DFA: each scan function represents a state, and
each character read is a transition. We chose hand-written for the same
reasons we chose hand-written recursive descent — readability and
error-message control.

**Q: Why is `°C` one token rather than two?**
A: Two reasons. **Semantically**, `°C` is a single unit of measurement —
treating it as one token preserves that identity in the AST and avoids
weird intermediate states. **Practically**, `°` is not in any of Python's
standard character classes (`isalpha`, `isdigit`), so without a dedicated
case it would trigger the "unexpected character" error. The `°C` scan
function reads both characters and emits one `UNIT_KW` token.

**Q: How does your lexer report errors?**
A: It raises `LexerError(message, line)`. The line number is tracked
across newlines as the lexer advances. Format:
`Lexer error at line {line}: {message}`. There's no column number in
the lexer's current format — that's a known cosmetic difference from
the parser's format, flagged as a Part 2 cleanup.

---

## 11. What I'd say if asked something I don't know

> "That's a lexer-internals question and the lexer was my partner's
> component — I can speak to the token contract we agreed on and the
> general Sebesta Ch. 4 principles, but for implementation specifics
> like the exact ordering of branches in the scanner I'd want to defer
> to my partner."

This is **better than guessing.** The handout (§3.1, §9) explicitly
warns that pairs are graded individually based on their own components
— and that exam questions target what each partner personally worked
on. Honesty about scope is rewarded; faked knowledge is the worst
possible outcome.
