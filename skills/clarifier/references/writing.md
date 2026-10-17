# Language rules

The core rules sit in `AGENTS.global.md` §5. This file holds the detail for each language and the
exceptions. Russian and Ukrainian follow the same core rules as English.

## Languages

### ru

- No канцелярит: `осуществлять`, `в настоящее время`, `является неотъемлемой частью`.
- No chains of genitives: `проверка соблюдения требований безопасности`.
- Use a verb, not a nominalisation.
- Keep an established English technical term when a translation is less precise.
- Modal words: `всегда`, `никогда`, `только`, `можно`.
- Weak words, never in a rule: `желательно`, `по возможности`.

### uk

- Address the reader as `ви`.
- No calques or russianisms: `приймати участь` → `брати участь`, `слідуючі` → `наступні`,
  `любий` → `будь-який`, `на протязі` → `протягом`.
- No nominal канцелярит: `здійснення`, `відповідно до вимог`.
- Use established Ukrainian terminology.
- Keep an English term where it is the convention.
- Ukrainian word order is flexible, so repeat the key word instead of a pronoun.
- Modal words: `завжди`, `ніколи`, `лише`, `можна`.
- Weak words, never in a rule: `бажано`, `по можливості`.

### en

- Write plain, direct English with short common words.
- No corporate or AI filler: `leverage`, `seamless`, `in order to`.
- Modal words: `must` for an obligation, `never` for a ban, `only` for a limit, `can` for an
  option.
- Weak words, never in a rule: `should`, `may`, `might`, `try to`.

## Exceptions

- A technical name in the sense of Simplified Technical English (STE) stays as it is:
  `padding`, `logging`.
- A code identifier stays as the code writes it.
- Dartdoc keeps the Effective Dart patterns: `Whether…` for a boolean, third-person `Returns…` for
  a method.
- A commit message keeps the `commit-changes` format.
- A UI string follows the `ux-translate` rules.

## New terms

- Define a new term in one line on first use.
- Never coin a compound name when common words say it.

## Word lists

- Our replacement pairs sit in the `clarify.py` phrase lists and apply to everyone.
- The full STE word list lives only in a local `words.json`. To build it:
  1. Request the PDF of the standard through the form on `asd-ste100.org`.
  2. Run `uv run --with pdfplumber python3 ste_extract.py <pdf>` from this skill's folder.
  3. `clarify.py` reads the `words.json` that `ste_extract.py` writes; `--words <file>` names
     another copy.
- `ste_extract.py` writes `words.json` outside this skill folder, so export never copies it.
- Never quote a `words.json` entry in a skill, an eval or a reply.
- Without `words.json`, the check flags only our pairs.
- The check reports each flagged word as a hint.
- A replacement hint is a suggestion. The word stays when the replacement changes what the
  sentence says.
- A word that neither STE list has gets a hint only under `--unlisted`.
- `technical.txt` in this skill's folder lists technical words the check accepts, one per line.

## Grow the list

A pair joins the list only when our skills or Dartdoc use the word. When a review finds a word
with a simpler replacement:

1. Find every use of the word with `grep` in `skills/*/SKILL.md`, `agents/*.md` and the Dartdoc
   of the project where the review found the word. Read each use.
2. If the replacement changes what one use says, add a synthetic sentence with that use to
   `evals/cases/<lang>-replacements-rejected.md`. The pair stays out. The word gets the
   "name the specific action" hint or no hint. Go to step 5.
3. Add a synthetic sentence with the word to `evals/cases/<lang>-replacements.md`.
4. Add the pair to the `<lang>` phrase list in `clarify.py`.
5. Run `python3 evals/score.py` until every case passes.
6. The report of a new pair says: "checked N places, the sense holds in all of them".

## Sources

ASD-STE100 Issue 9, named as the standard, and ISO 24495-1; this file copies no rule or dictionary
text from either.
