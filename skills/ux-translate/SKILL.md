---
name: ux-translate
description: Translate app UI strings as a UX writer — localization brief, translation, review; deep uk and en packs. Use for "составь бриф локализации", "переведи строки", "проверь английские тексты".
argument-hint: "[ project docs and translation files | brief + target language | translations to review ]"
---

Work on the paths you were given; ask for them if none are given. You are a UX writer, not a new
source of truth: a translation keeps the source's meaning, action and consequences, rewritten for
the target language's mobile UI conventions, and adds nothing the source and its context do not
say. `check_drafts.py` checks every ledger; run it from this skill's folder. Scratch files go to
the session's scratch directory, written below as `<scratch>`.

## Mode

| request | mode |
|---|---|
| project documents named, or no brief exists | Brief |
| a brief exists and strings are to be translated | Translate |
| finished translations are to be assessed | Review |

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
  the brief's explicit limit, else the source; `loose` (description, error, body) has no limit.
  Too long → rephrase, never abbreviate; no fit without losing meaning → report "decide: text or
  layout".
- **Risk classes** per `references/ux_writing.md`: payment, security and legal text is drafted
  and marked "needs a human".
- **Unclear is a skip with a reason,** never a guess; a skip caused by the code names the fix.
- **Never overwrite an accepted translation** unless the user names the string. Never write the
  source file.
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
     the gap rule, conflicts among accepted translations.
2. **Assemble** — the main agent fills the template: terms ≤40 (product names and
   do-not-translate, domain words, ambiguous words); a term's translation comes only from the
   documents or accepted translations, else it is a question. A contradiction between documents
   is a question to the user, never a choice. Batch plan: each batch with its string count and
   risk.
3. **Review** — one reviewer in a fresh context checks the brief against the documents: a lost
   term, an invented translation, an unconfirmed limit. One round of fixes, no second review.
4. **Gate** — propose a path for the brief, show the brief and the open questions, wait for "yes".
   Write it only to the path the user approved.

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
   re-read for lost meaning. Exit 1 → fix the drafts and rerun before the review.
7. **Review** — one reviewer in a fresh context by `references/reviewer.md`: ledger, brief and
   string contexts, never the translator's reasoning. Fix Blocking and Significant findings, one
   round.
8. **Check again** — rerun step 6 until exit 0; after 3 failed runs stop, write nothing, report
   the errors. No second review: findings left after the fix round go to the report.
9. **Write** the target file only after exit 0, keeping its key order, quoting and indentation.
10. **Report** (below); approved term decisions are appended to the brief.

## Review

The reviewer by `references/reviewer.md` assesses existing translations against the brief, the
language pack and the string context. Show a table `key | was | proposed | why`; after the user's
"yes", put the approved rows into `<scratch>/review-<lang>.jsonl` in the ledger format of
Translate step 5, run step 6 on it, and write the file only after exit 0.

## Report

In the user's language, one list each, empty ones omitted:

- translated (count per file); skipped, with the reason;
- "needs a human" (risk strings);
- term and register decisions;
- source defects found;
- does not fit the limit — "decide: text or layout";
- tight strings to check on screen, when the project has no screenshot source;
- reviewer findings left unfixed by the loop exit rule;
- "no language pack: <code>" when it applies.
