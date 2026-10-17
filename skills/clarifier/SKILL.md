---
name: clarifier
description: Turn a document into a short text read in 3–5 minutes (RU, UK, EN) without losing facts; checks text for skills. Use for "упрости текст", "сделай понятно", "clarify".
argument-hint: "[ path to the document (optionally: 3 min) ]"
---

Clarify the document at the path you were given; ask for it if none is given. You are an editor,
not a new source of truth: the result says what the source says, shorter. `clarify.py` checks the
result; run it from this skill's folder. The skill writes text only — a diagram is the `visualize`
skill's job, on a separate request.

## Flow

1. **Read** the whole source. Language of the result = language of the source unless the user
   names another; Ukrainian is written in Ukrainian from the start, never translated from Russian.
   Budget: 5 minutes by default, 3 when the user asks.
2. **Diagnose** — what the reader must take away: the main point, the decisions, the conditions,
   the open questions. List what is noise: preamble, repeats, meta text, history. Check first,
   rewrite only on violations: a source that already passes `clarify.py check` and the contract
   below is returned as is.
3. **Form** — pick the shape by document type (table below), then write by the contract.
4. **Write** `<source stem>.clear.md` beside the source.
5. **Check** — `python3 clarify.py check <stem>.clear.md --lang <ru|uk|en> --source <source>`
   (add `--minutes 3` for a 3-minute budget) must print `ok`. Fix each error line, rerun; after 3
   failed runs stop and report the remaining errors.
6. **Reader test** — compose 5–10 questions a reader of the source would ask, each with the
   source's answer. Hand only the result file and the questions (never the answers, never the
   source) to a fresh read-only agent: `Explore` in Claude Code, `explorer` in Codex, told to
   read only that file. An answer that differs from the source, or "not stated" where the source
   states it, is a fix in the text. Rerun the check after fixing. At most 2 rounds; what still
   diverges goes to the report.

## What `clarify.py check` reports

- Usage: `check <file> [--lang ru|uk|en] [--source <src>] [--minutes N]`. For `.md`, `--lang` is
  required; for `.json` (a `visualize` document, `brief.json` included) the language comes from
  its `lang` field. A bad language or minutes value → usage line, exit 2.
- `check <path>... --instructions|--dart [--lang ru|uk|en] [--words <file>] [--unlisted]
  [--summary]` reads skill, agent and rule files or the `///` lines of Dart files. With a
  folder, the check reads every `.md` file. With `--dart`, it reads every `.dart` file and skips
  generated ones (`*.g.dart`, `*.freezed.dart`, `*.gr.dart`, `*.config.dart`). The language
  defaults to `en`. Every finding is a `hint:`, then `ok`, exit 0.
- Errors (exit 1): words over `minutes × rate` (ru and uk 160/min, en 190/min); a sentence over
  25 words; a paragraph over 5 sentences; a list over 5 items; a nested list; with `--source`,
  `new: <token>` — a number or date the source does not have.
- Hints (`hint:` lines, exit unchanged): an abbreviation without expansion on first use; stock
  phrases, closers and meta text per language; with `--source`, `lost: <token>` — a number,
  date, URL or `code` of the source missing from the result.
- No errors → hints, then `ok`, exit 0.
- Skipped: fenced code, inline `code`, HTML comments, headings. Text inside `<details>` is
  checked but does not count toward the budget. A list item and a line starting with `Label:`
  each count as a separate paragraph.
- `new:` is always fixed: remove the number or restore the source's one. `lost:` is a decision:
  keep the token when the reader needs it, drop it when it is detail; the reader test catches a
  lost meaning. Every other hint is fixed unless the phrase is the source's term.

## Form by document type

| Document | Shape |
|---|---|
| Plan, design note | decision and its scope → what changes, by part → open questions |
| Recommendation, research | conclusion → why → the caveat that matters → options in `<details>` |
| Instruction | one line of context → numbered steps |
| Comparison | conclusion → small table → details only if needed |
| Contract, spec | what it is for → rules and conditions → edge cases |

Every shape:

- The first paragraph carries the main point; a reader who stops there knows the outcome.
- At most 5 points, one per heading or paragraph; a heading states the conclusion, not the topic.
- Points do not overlap and together cover the whole source.
- Secondary detail the reader may need goes into `<details><summary>…</summary>`, never deleted
  silently. A short source gets no headings.
- One paragraph, one thought: answer, reason, action, warning or example.

## Editorial contract

Never change:

- numbers, dates, names, `code`, URLs, citations;
- warnings, conditions, exceptions and every hedge of uncertainty — "probably" stays "probably",
  "unverified" stays "unverified"; uncertainty never turns into certainty;
- the scope of a claim: a qualifier the source attaches ("only on Android", "for new users")
  survives with it.

Never add: a fact, a number, an example, a reason the source does not give. When the source is
unclear or two readings exist, ask the user; when in doubt whether something matters, keep it.

Remove: preamble, a restatement of the question, a closing recap that repeats the body, offers
like "если нужно — скажите" or "let me know", filler, meta text ("в этом документе"), the
"не X, а Y" frame, history of how the document changed.

Write:

- by the core writing rules of `AGENTS.global.md` §5;
- a term or abbreviation explained on first use: `ABBR (full name)` or `full name (ABBR)`;
- "потому что" / "поэтому" / "because" kept inside a sentence — a reason is never cut into
  list fragments; a list is only for parallel items;
- facts and numbers instead of judgments ("в 3 раза быстрее", not "значительно быстрее") — but
  only numbers the source gives.

## Language rules

RU, UK and EN detail, modal words and exceptions: `references/writing.md`.

## Check for another skill

When another skill asks to check its text (`brief.json`, a `visualize` document, a `.md`):

1. Run `python3 clarify.py check <file>` (with `--lang` for `.md`; `--instructions` for a skill,
   agent or rule file; `--dart` for a Dart file) — no rewrite, no reader test.
2. Fix error lines in that file within the caller's own fix loop and run limit; change only the
   flagged sentence, paragraph or list.
3. Hints are the caller's call: fix a stock phrase, leave a term.

## Report

In Russian, one line each: the result path; words / budget and minutes; the checker's last
output (`ok` or the remaining errors); `lost:` tokens dropped on purpose; reader-test rounds and
any answer that still diverges; questions asked to the user.
