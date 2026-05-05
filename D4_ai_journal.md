# DataScript — AI Usage Journal (D4)
# CSE 341 · Part 1 · Due 8 May 2026

---

## Entry 1 of 4

| Field        | Content |
|--------------|---------|
| **Entry #**  | 1 of 4 |
| **Date**     | 2026-05-01 |
| **Phase**    | Design |
| **AI tool**  | Claude Sonnet 4.6 |

**Goal:** Decide on a language domain and understand which Sebesta Ch. 1 evaluation criteria apply to it.

**Prompt (verbatim):**
> "I need to design a domain-specific language for CSE 341. I'm considering a mini query language over CSV files, similar to SQL but simpler. Using Sebesta's language evaluation criteria — readability, writability, reliability, cost — which criteria should this kind of DSL prioritize and which should it sacrifice? Give me a one-paragraph justification I can use in my design spec."

**Response (key part):**
The AI suggested prioritizing readability and writability because SQL-like syntax is already familiar to the target audience (data analysts), and DSLs gain power by being narrow. It said reliability could be partially addressed through static typing of columns, but general-purpose reliability features (memory safety, exception handling) are unnecessary overhead for this domain. Cost (generality) should be knowingly sacrificed — a DSL is not supposed to be general-purpose.

**Accepted:** The overall framing — readability and writability as primary, cost as the explicit sacrifice — matched my intuition and I used this structure in §4.1. The point about "domain users are not PL experts" was directly useful.

**Rejected / modified:** The AI's draft paragraph was generic boilerplate that could apply to any DSL. It did not cite specific Sebesta section numbers (§1.3.1, §1.3.2, etc.) and did not mention the specific trade-off for *this* domain (no file I/O beyond table loading, no recursion). I rewrote it entirely in my own voice with proper citations and domain-specific trade-offs.

**Errors caught:** The AI said reliability is "not relevant" to a query DSL. This is wrong — strong typing of column values (catching `string > int` comparisons before execution) is directly a reliability feature in Sebesta's sense (§1.3.3). I added this to the spec.

**Reflection:** AI is useful for brainstorming the structure of an argument but produces vague, citation-free prose when asked for academic writing. The real work was mapping its general points onto Sebesta's specific framework. Next time I will include the section numbers in the prompt to get more precise output.

---

## Entry 2 of 4  [Experiment E1]

| Field        | Content |
|--------------|---------|
| **Entry #**  | 2 of 4 |
| **Date**     | 2026-05-02 |
| **Phase**    | Design |
| **AI tool**  | Claude Sonnet 4.6 |

**Goal (E1):** Ask the AI to generate an EBNF grammar for DataScript from a one-paragraph description, then compare its output with my own grammar.

**Prompt (verbatim):**
> "Here is a one-paragraph description of my language DataScript. Please generate a complete EBNF grammar for it.
>
> DataScript is a query DSL for tabular data. A program is a sequence of statements. Statements include: table declarations (table name = load 'file'), let bindings (let name = expr), print statements, if/then/else with mandatory braces, and function declarations with typed parameters and a return type. The main expression type is a query: SELECT col_list FROM table WHERE condition ORDER BY col DESC. Conditions use AND, OR, NOT, and comparison operators (==, !=, <, <=, >, >=). Arithmetic uses +, -, *, /. There are integer, float, string, and boolean literals. Aggregate functions: COUNT, SUM, AVG, MIN, MAX."

**Response (key part):**
```ebnf
<program>    ::= <stmt>*
<stmt>       ::= <table_decl> | <let_stmt> | <print_stmt> | <if_stmt> | <func_decl>
<table_decl> ::= "table" IDENT "=" "load" STRING
<let_stmt>   ::= "let" IDENT "=" <expr>
<if_stmt>    ::= "if" <expr> "then" <block> ("else" <block>)?
<func_decl>  ::= "function" IDENT "(" <params>? ")" ":" <type> <block>
<expr>       ::= <expr> ("AND" | "OR") <expr>
               | "NOT" <expr>
               | <expr> ("==" | "!=" | "<" | "<=" | ">" | ">=") <expr>
               | <expr> ("+" | "-" | "*" | "/") <expr>
               | "-" <expr>
               | <primary>
<primary>    ::= INT | FLOAT | STRING | BOOL | IDENT | "(" <expr> ")"
               | <query_expr> | <func_call> | <aggregate>
<query_expr> ::= "SELECT" <cols> "FROM" IDENT ("WHERE" <expr>)?
                 ("GROUP" "BY" <cols> ("HAVING" <expr>)?)?
                 ("ORDER" "BY" <order>)?
```

**Accepted:** The overall structure (statement list, block-based if, query shape) was correct and matched my design. The primary production and the query clause structure were a good starting point.

**Rejected / modified — three specific problems:**

1. **Operator precedence is completely absent.** The AI wrote `<expr> ::= <expr> ("AND" | "OR") <expr> | <expr> ("==" ...) <expr> | <expr> ("+" | "-" | ...) <expr>`. This is an ambiguous grammar — `a + b * c` has two valid parse trees. My grammar uses layered non-terminals (`or_expr → and_expr → not_expr → compare_expr → add_expr → mul_expr → unary_expr → primary`) to encode precedence unambiguously, which is the standard technique from Sebesta §3.4. The AI's flat grammar would require a separate precedence table in the parser, defeating the purpose of writing an unambiguous grammar.

2. **Comparison operators are left-associative.** The AI used `<expr> OP <expr>` recursively, making `a < b < c` syntactically valid. My grammar uses `[ ... ]` (optional, not repeating) for comparisons, making them non-associative by design — `a < b < c` is a parse error. This is an intentional reliability decision.

3. **Function return type uses ":" instead of "->".**  The AI wrote `"function" IDENT "(" ... ")" ":" <type>` — using a colon for return type. In DataScript, colon is used for *parameter* type annotations (`name: type`), and `->` is used for *return* type. The AI mixed these up, which would create an ambiguity in the parser.

**Errors caught:** All three above. I detected the precedence issue by tracing a parse of `a + b * c` through the AI's grammar — both `(a+b)*c` and `a+(b*c)` were valid parse trees, confirming the grammar is ambiguous.

**Reflection:** The AI produced a syntactically plausible-looking grammar that would fail in exactly the parts that require design judgment — precedence, associativity, and disambiguation. These are precisely the decisions Sebesta emphasizes in Ch. 3. The grammar looked correct at a glance but was fundamentally broken. This confirms that using AI output without tracing through concrete examples is dangerous for grammar design.

---

## Entry 3 of 4

| Field        | Content |
|--------------|---------|
| **Entry #**  | 3 of 4 |
| **Date**     | 2026-05-03 |
| **Phase**    | Lexer |
| **AI tool**  | Claude Sonnet 4.6 |

**Goal:** Understand how to handle the comment syntax `--` without conflicting with the subtraction operator `-` and the arrow `->`.

**Prompt (verbatim):**
> "In DataScript, single-line comments start with '--'. The minus operator is '-' and the return type arrow is '->'. In a hand-written lexer, what is the correct order of checks to avoid confusing these three? Should comment stripping happen inside next_token() or before it?"

**Response (key part):**
The AI explained that comments should be stripped in a separate `skip_whitespace_and_comments()` method called at the *start* of `next_token()`, before any operator scanning. The key insight: `--` can only appear where a token boundary exists (after whitespace or another token), so if we skip comments before scanning operators, the operator scanner never sees `--`. The two-character operator `->` is handled by maximal munch — check `->` before checking `-`.

**Accepted:** The architectural separation — skip whitespace and comments first, then scan operators — was exactly right. I implemented `_skip_whitespace_and_comments()` as a separate method that runs at the start of every `_next_token()` call. The maximal munch ordering (check 2-char tokens before 1-char) was already my plan.

**Rejected / modified:** The AI suggested using Python's `re` module with a combined regex to handle all cases at once. I rejected this because the goal is a hand-written lexer where every decision is visible and explainable. A regex-based approach would be harder to defend in the exam.

**Errors caught:** None in this case — the architectural advice was sound.

**Reflection:** Sometimes AI is most useful not for generating code but for confirming a design decision and articulating *why* it works. The explanation of why comment-skipping belongs before operator-scanning clarified the separation of concerns between the two phases of lexical analysis (Sebesta §3.1).

---

## Entry 4 of 4

| Field        | Content |
|--------------|---------|
| **Entry #**  | 4 of 4 |
| **Date**     | 2026-05-05 |
| **Phase**    | Parser |
| **AI tool**  | Claude Sonnet 4.6 |

**Goal:** Understand how to implement the 1-token lookahead needed to distinguish a function call from a bare identifier in `<primary>`.

**Prompt (verbatim):**
> "In my recursive-descent parser for DataScript, the <primary> non-terminal has two alternatives that both start with IDENT: a bare identifier and a function call (IDENT followed by LPAREN). How do I disambiguate these in a recursive-descent parser without backtracking?"

**Response (key part):**
The AI explained this is a classic LL(1) disambiguation: after consuming IDENT, peek at the *next* token. If it is `(`, it is a function call; otherwise it is a bare identifier. In a lookahead-based parser you do not consume IDENT first — instead you peek at both the current token (IDENT) and the one after it (position + 1) before deciding which branch to take.

**Accepted:** The lookahead approach — `self.tokens[self.pos + 1]` before consuming anything — is exactly what I implemented. This avoids backtracking entirely and keeps the parser LL(1) for this production.

**Rejected / modified:** The AI suggested wrapping this in a try/except to handle the lookahead failing at EOF. I used a safer explicit check (`if self.pos + 1 < len(self.tokens)`) instead of exception handling for control flow, which is cleaner and avoids masking real errors.

**Errors caught:** The AI's code sample used `tokens[pos + 1]` without bounds checking, which would raise an `IndexError` at EOF. For example, a program ending with a bare identifier as the last token would crash. I caught this by testing `print x` at EOF and added the bounds check.

**Reflection:** The 1-token lookahead solution is a direct application of LL(1) parsing theory (Sebesta §4.4). Understanding *why* it works — not just that it works — meant I could explain in the exam why DataScript's grammar is LL(1) for this case and where it would break if two alternatives shared a longer common prefix.
