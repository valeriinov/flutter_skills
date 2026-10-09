# Localization brief template

The brief is the project's one place for voice, terms and limits; every translator and reviewer
gets it whole. Fill each section from the project's documents, code and translation files. A value
no input confirms stays empty and becomes an open question; never invent it. Keep the headings in
this order.

```markdown
# Localization brief

## Product
<one line: what the product is and for whom>

## Languages and files
| language | code | file | role |
|---|---|---|---|
| <Ukrainian> | uk | <path> | source |
| <English> | en | <path> | target |

## Voice and register
- Register and address per language: <you / ви / ти>
- Tone: <concise, direct, calm, …>
- Conventions: <contractions, exclamation marks, CTA verbs, …>
- Source: <document and section>

## Terms
The UI glossary: at most 40 product names and do-not-translate, domain words, words ambiguous
out of context — one word per concept in each language. Authority, highest first: <the documents
the user named as governing UI wording>. A translation comes only from those documents or
accepted translations; otherwise the cell is empty and the term is an open question. The source
file is never changed: a source string using a flagged variant is reported as a review
recommendation.

| term (source UI word) | <target language> | do not translate | meaning in this product | source variants to flag | source |
|---|---|---|---|---|---|

## Do not use
Rows for both languages, each prefixed with its code.

| word | use instead | source |
|---|---|---|

## Intentionally identical
Keys whose target value equals the source on purpose (brand, unit, code); they are never gaps.

| key | why |
|---|---|

## Gap rule
<a missing key and an empty value; plus "value equals source" when the target is seeded with the
source>

## String context source
- Code: <where the strings are used, how a key is found at its call site>
- Screenshots: <where the project keeps them, or "none">

## Length limits
| element or key | limit (characters) | hard | source |
|---|---|---|---|

`hard: yes` only when a design or document states the limit as binding; it becomes
`limit_hard: true` in the ledger.

## Text component catalogue
Every shared component that renders text, analysed once.

| component | ui (tight/loose) | maxLines | note (overflow, width/height, text scaling) |
|---|---|---|---|

## Risk keys
| key or prefix | risk class | why |
|---|---|---|

Classes as in `references/ux_writing.md`; each is drafted and marked "needs a human".

## Batch plan
| batch (screen or feature) | key prefix or screenshot | strings | risk |
|---|---|---|---|

## Decisions
Term and register decisions approved after translation runs.

| decision | language | date |
|---|---|---|

## Open questions
- <a contradiction between documents, quoted from both; a term without a confirmed translation>
```
