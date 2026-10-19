---
name: ux-translate
description: 'Translate UI strings as a UX writer: brief, review, new keys. Use for "бриф локализации", "переведи строки", "проверь тексты", "добавь ключ".'
argument-hint: "[ project docs and translation files | brief + target language | translations to review ]"
---

Work on the paths you were given; ask for them if none are given. With no brief path given, the
brief is the one the project AGENTS.md section `## Localization` names. You are a UX writer, not a
new source of truth: a translation keeps the source's meaning, action and consequences, rewritten
for the target language's mobile UI conventions, and adds nothing the source and its context do
not say. The one authored text is an Add key source written from the user's intent; it is
approved at that mode's gate. `check_drafts.py` checks every ledger; run it from this skill's
folder. Scratch files go to the session's scratch directory, written below as `<scratch>`.

## Mode

| request | mode |
|---|---|
| project documents named, the brief is to be rebuilt, or no brief at the path from `## Localization` | Brief |
| a brief exists and strings are to be translated | Translate |
| finished translations are to be assessed | Review |
| source strings are to be assessed, with no translation | Review, source only |
| intent or text for a key absent from both files, or an existing key the user names | Add key |
| exported approved brief and locale files | Apply approved |
| keys awaiting approval are to be checked before a PR | Pending check |

## Roles

Pick the role, never a model.

| node | Claude Code | Codex |
|---|---|---|
| analyst, reviewer, parallel translator | `Explore` | `explorer` |

- At most 5 agents on the longest path; every graph below stays within it.
- Below ≈50 strings and ≈10 code files: no subagents, the main agent runs every node itself.
- Every agent's task is self-contained: the paths, the brief (or its path), the answer format.
- Agents are read-only: a parallel translator returns its ledger lines in its answer, and the main
  agent writes the ledger.

## Rules for every mode

- **Sources of truth, earlier wins:** the brief (terms, do-not-use) → accepted translations in the
  target file → the string's context (key, call site, screenshot when the brief names a
  screenshot source) → this skill's rules (`references/ux_writing.md`, the language pack).
- **Placeholders** stay byte-identical and equal in count; tags, escapes and edge whitespace
  survive. **Plurals** take the target language's CLDR categories, never the source's.
- **Length** is a budget by element type, not equality with the source: `tight` (button, tab,
  chip, screen title, inline label, text under `maxLines`/ellipsis/fixed width) is no longer than
  the brief's explicit limit, else the source — a source the skill writes itself (Add key) takes
  only the explicit limit, else none and the on-screen check list; `loose` (description, error,
  body) has no limit.
  Too long → rephrase, never abbreviate; no fit without losing meaning → report "decide: text or
  layout".
- **Risk classes** per `references/ux_writing.md`: payment, security and legal text is drafted
  and marked "needs a human".
- **Unclear is a skip with a reason,** never a guess; a skip caused by the code names the fix.
- **Never overwrite an accepted translation** unless the user names the string. Never write the
  source file, with two exceptions. Add key writes to it only a key absent from both files or an
  existing key the user names; the values of other keys do not change; with no paths given, the
  files come from the brief's `## Languages and files`. Apply approved writes the export's
  approved keys (its section).
- **New terms** — a word by the Assemble criteria (product name or do-not-translate, domain word,
  word ambiguous out of context) missing from Terms gets a `status: proposal` row: Add key shows it
  at its gate and writes it after "yes"; Translate writes it with the step 10 decisions. `accepted`
  rows change only in a ux-approval round; run from ux-approval Next round, new `proposal` rows go to
  `<dir>/brief.md`. The report lists the new `proposal` rows.
- **Approval queue** — `approval-queue.md` in the brief's folder, shaped by
  `references/approval_queue_template.md`. Add key queues by its step 7; Translate and Review
  queue the keys they write only when the brief says `Status: approved` (a first brief and a bulk
  translation go to a round whole); a "yes" at the Review gate accepts the edit, not the team's
  approval, so Review queues with no question.
  Run from ux-approval Next round (the brief in `<dir>`), no queue is written — the reconcile
  marks that round's keys.
- **Language pack** = `references/lang/<code>.md` by the target language code. None → general
  rules only, and the report carries "no language pack: <code>".

## Brief

Inputs: paths to project documents (glossary, text guide, requirements, design), the source and
target translation files, accepted translations. Output: a brief by
`references/brief_template.md` plus the batch plan.

1. **Analyse** — three analysts in parallel, each returns a compact result, no file dumps:
   - documents → product and audience, voice and register, terms, do-not-use, length limits and
     whether each is hard;
   - code → the text component catalogue (every shared component that renders text — button,
     tab, chip, title, toast — analysed once: line count, overflow, width/height, text scaling →
     `tight`/`loose`, `maxLines`, note) and the screenshot source, if the project keeps one;
   - translation files → string groups by screen or feature (key prefix or screenshot source),
     the gap rule, conflicts among accepted translations, and for each core concept every
     word form and synonym the source uses, counted by key — a role named two ways is the
     conflict the brief exists to settle; and every service or institution word whose
     dictionary pair names a different institution in the target culture (`пошта` → mail).
2. **Assemble** — the main agent fills the template: terms ≤40 in this first brief (product names
   and do-not-translate, domain words, ambiguous words); a term's translation from the documents
   or accepted translations is `accepted`, else the cell is empty and it is a question. A
   contradiction between documents is a question to the user, never a choice. An existing brief
   keeps its `Status:` line and its `accepted` and `proposal` rows; Assemble only adds rows,
   as `proposal` rows by New terms when the brief says `Status: approved`.
   Batch plan: each batch with its string count and risk, counted by a script over the keys so the
   batches sum to the key count.
   - **Authority first** — before filling terms, ask which documents govern what the user sees
     and in what order. A code glossary names code entities: its identifiers are not UI words
     unless a document says so. A glossary nobody maintains is reference, not authority.
   - **The terms table is a UI glossary** — one word per concept in each language, plus the
     source's other words for it, which a review flags; the source file is never changed.
   - **A disputed source word** — the question shows each variant's count, whether the voice
     guide or its author uses it, and, when the file is in git, which came first; frequency
     alone does not make a word canonical, since later strings are often written without the
     guide.
3. **Review** — one reviewer in a fresh context checks the brief against the documents: a lost
   term, an invented translation, an unconfirmed limit. One round of fixes, no second review.
4. **Gate** — the brief's path is the one in the project AGENTS.md section `## Localization`, else
   `docs/agents/specs/localization/brief.md`. Show the brief, the open questions, the section text,
   the duplicate list and every AGENTS.md edit; wait for "yes". Then write the brief and always the
   section (present → updated in place). The section names:
   - the brief path; the queue path `approval-queue.md` beside it;
   - adding a key → Add key; editing a translation → Translate or Review;
   - editing the text of an existing key → Add key with the named key;
   - "before a PR — ux-translate, Pending check; its warnings go into the PR description".

   An earlier AGENTS.md line about the translation files is replaced by one line pointing to the
   section; no other AGENTS.md line changes except links to removed duplicates.
   - **Duplicates** — a project markdown file outside `plan/`, other than the brief and
     `approval-queue.md`, with a table where at least two rows match brief terms (any case;
     `meaning` by sense, not wording) by the first Terms column, by the variants-to-flag column or
     by `meaning`, or with a heading only the brief has (`Terms`, `Do not use`, `Text component
     catalogue`). A table whose value column holds code identifiers in backticks is a code
     glossary: named in the report, never offered for removal. The rest go to the gate as
     `path | what it repeats | links to it`; after "yes" they are deleted with the links to them.

## Translate

1. **Gaps** — per format: the key is missing, the value is empty, or it equals the source when the
   brief says the target is seeded with the source. Strings in the brief's intentional-identity
   exceptions are not gaps.
2. **Read** the brief, `references/ux_writing.md` and the target language pack before the first
   draft.
3. **Context and element type** — first by the brief's text component catalogue (the component at
   the call site gives `ui` and `maxLines`); call-site analysis only for text outside the
   catalogue: layout limits (Flutter: `maxLines`, `TextOverflow.ellipsis`, fixed width, button,
   tab, `AppBar`; native: `numberOfLines`, `lineLimit`) → `ui` (`tight`/`loose`) and `limit` (the
   brief's explicit limit, else the source length for `tight`).
   - **What triggers it** — for an error, status or confirmation, read the code branch that sets
     the key: a `catch` or failed request means the operation failed, a failed check on the
     value means the input is wrong, and a neighbouring key often holds the other case. The
     source wording can be vaguer than the branch («Помилка валідації» set in a `catch` is
     "Couldn’t check the number", not "Enter a valid number"); translate the branch.
4. **Settle once** what the brief leaves open — register, one rendering per recurring term — and
   hold it everywhere; each choice is a decision in the report.
5. **Draft** into `<scratch>/drafts-<lang>.jsonl`, one line per gap, self-checked by
   `references/ux_writing.md`:
   `{"file", "key", "source", "target" | "skip" + "reason", "risk", "ui", "limit", "limit_hard"}`
   — `risk` is the class from `references/ux_writing.md` or `none`, `limit_hard` comes from the
   brief's hard limits. Over `limit` → rephrase, then report. From ≈150 strings: parallel
   translators, one batch of the brief's plan each (by screen), each given the brief and the
   settled decisions; each returns its ledger lines and the main agent writes them into the ledger.
6. **Check** — `python3 check_drafts.py <scratch>/drafts-<lang>.jsonl --lang <code> --ratio
   <min>,<max>` (the corridor from the target language pack; no pack → omit `--ratio`). Exit 0 ok,
   1 errors, 2 usage or input error. Length-limit overflow and ratio deviation are warnings
   unless `limit_hard: true`: "much longer" goes to the on-screen check list, "much shorter" is
   re-read for lost meaning; a straight apostrophe in English is fixed to `’` unless the brief
   allows straight quotes, and an English em dash is rephrased away. Exit 1 → fix the drafts and rerun before the review.
7. **Review** — one reviewer in a fresh context by `references/reviewer.md`: ledger, brief and
   string contexts, never the translator's reasoning. Fix Blocking and Significant findings, one
   round.
8. **Check again** — rerun step 6 until exit 0; after 3 failed runs stop, write nothing, report
   the errors. No second review: findings left after the fix round go to the report.
9. **Write** the target file only after exit 0, keeping its key order, quoting and indentation.
10. **Report** (below); approved term decisions and new `proposal` rows are appended to the brief;
    written keys are queued by the approval queue rule.

## Review

**Source only** — the same reviewer reads source strings with no translation: the brief's UI
glossary and source-language do-not-use rows, the voice guide and the source language's pack
(`references/lang/<source>.md`). Reasons that need a pair do not apply (`references/reviewer.md`).
The result is the table below with the source string in `was`; nothing is written — the source
file is never changed, so approved rows go to the report as recommendations.

The reviewer by `references/reviewer.md` assesses existing translations against the brief, the
language pack and the string context. Show a table `key | was | proposed | why`; after the user's
"yes", put the approved rows into `<scratch>/review-<lang>.jsonl` in the ledger format of
Translate step 5, run step 6 on it, and write the file only after exit 0; written keys are queued
by the approval queue rule.

## Add key

Input: the user's intent, a text in one of the brief's two languages, or both; or an existing key
the user names.

1. **Brief** — from `## Localization`; `Status: draft` → a warning in the report.
2. **Name** — by the `naming` skill's mechanism: the project AGENTS.md `## Naming Conventions`,
   then the screen's neighbouring keys, then a name with 1–2 precedents. A named key keeps its name.
3. **Component** — from the user's intent; none named → one question. `ui` from the brief's text
   component catalogue, a component outside it by its element class in `references/ux_writing.md`;
   `limit` only the explicit one from the brief's `## Length limits`, else empty and the key goes
   to the on-screen check list.
4. **Text** — intent → the source text, then Translate steps 4–5 for this key. A text only in the
   target language stays the target as is, and the source is translated from it.
5. **Check** — the target ledger `<scratch>/drafts-<target>.jsonl` with the target pack's
   `--ratio`; the source ledger `<scratch>/drafts-<source>.jsonl` with `source == target`,
   `--lang <source>`, no `--ratio`. Both exit 0.
6. **Review** — by `references/reviewer.md`, one round of fixes, then step 5 again; after 3 failed
   runs stop, write nothing, report the errors.
7. **Gate** — a table `key | <source> | <target> | ui | limit`, the new `proposal` terms and the
   queue decision; a source text written from the intent is approved here. After "yes", both
   files get the key next to the keys of the same screen. Queue by the text's origin:
   - taken from the task or a design → not queued, no question;
   - written by the skill → queued, no question;
   - dictated by the user and absent from the task → one question at this gate; "not approved"
     → queued.

The report names the project's next step from its AGENTS.md (key code generation).

## Apply approved

Input: the ux-approval export `<slug>-r<n>-brief.md` and `<slug>-r<n>-<lang>.json`, and the
Finalize report with its reconcile commit.

1. **Final round** — only the export of a final round: the Finalize report or
   `Approval: … final` in the queue. Otherwise stop and say why.
2. **Changed since** — keys in `git diff <commit> -- <locale files>` are not overwritten; they go
   to the report.
3. **Texts** — every other export key that differs from the project is a named string: a ledger
   per pair, Translate step 6 to exit 0, then both files are written in the project's key order.
4. **Brief** — written to the path from Brief step 4 with
   `Status: approved (<artifact round>, <date>)`. Terms merge: export rows win; project `proposal`
   rows absent from the export stay. The `## Localization` section as in Brief step 4; duplicates
   as in Brief step 4, deleted only after "yes".
5. **Queue** — a queue key is approved when the export files hold it and the step 2 diff does not;
   its row is removed, the rest stay. `Approval:` → `applied`.

The report names the project's next step from its AGENTS.md (key code generation).

## Pending check

Before a PR, with the queue path from `## Localization`:
`python3 <this skill's dir>/pending.py <approval-queue.md>`. No output → nothing awaits approval.
Each warning line goes into the PR description as is. Exit 0 with or without warnings, 2 an input
error.

## Report

In the user's language, one list each, empty ones omitted:

- translated (count per file); skipped, with the reason;
- "needs a human" (risk strings);
- term and register decisions;
- source defects found;
- does not fit the limit — "decide: text or layout";
- tight strings to check on screen, when the project has no screenshot source, and Add key keys
  with an empty `limit`;
- new `proposal` terms; keys queued and removed from the queue; a `Status: draft` brief;
- duplicates removed, and code glossaries named; keys left unapplied as changed since the commit;
- reviewer findings left unfixed by the loop exit rule;
- "no language pack: <code>" when it applies.
