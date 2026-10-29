---
name: ux-approval
description: 'Run UI text approval rounds in a shared artifact: create, append new keys, next round from answers and the project. Use for "утверди тексты", "следующий раунд", "approval round".'
argument-hint: "[ ux-translate brief, review and locale files | artifact url + next round | artifact url + append ]"
---

Run from the project whose branch will receive the approved texts. The artifact is the source of
truth for the texts: each round keeps its brief, a snapshot of every key, the review and the
answers. You publish the artifact and read its database yourself. You read the project for the
reconcile, the stages and key context. You write only three things into the project:
- the `Approval:` line of its `approval-queue.md` ([Approval queue](#approval-queue));
- the stage lines of its `## Localization` section, after the user's "yes" ([Stages](#stages));
- approved texts, through ux-translate, after the user's choice ([Deliver](#deliver)).

A cut is the close of a round: Next round applies its answers and Deliver offers its approved
texts. Working files go to the
session's scratch directory, written below as `<scratch>`. `approval.py` runs from this skill's
folder; `check_drafts.py` is the neighbouring skill's, `../ux-translate/check_drafts.py`.

## Mode

| request | mode |
|---|---|
| no artifact yet: ux-translate outputs and locale files named | Create |
| artifact url, its latest round open, new or changed project keys | Append |
| artifact url, its latest round closed by the owner | Next round (the cut) |

Latest round still open (no `rounds/<n>` document) → compare the keys of the approval queue with
the artifact's keys. Show the keys that the artifact lacks and ask "append to the artifact?".
"Yes" runs Append. "No" → tell the user that the owner closes the round with "Завершити раунд" on
the page, and stop. Append runs only after this "yes".

An old page whose latest round is final takes no new round: `check` refuses it.

## Spec shape

You write the spec; `approval.py check` validates it and `build` turns it into the page.

```json
{
  "title": "Погодження текстів Example app", "lang": "en", "product": "Example app", "slug": "example-texts",
  "ui": {"…": "every interface string the page shows, in `lang`: each key page_template.html reads with t() and tMap()"},
  "round": 1, "final": false, "fullReview": {"en": 1, "fr": 1},
  "origin": {"branch": "main", "commit": "3f2a9c1"},
  "brief": "# Localization brief\n…",
  "files": {
    "source": {"lang": "uk", "path": "l10n/uk.json",
               "values": {"card.title": "Банківська картка", "items": {"one": "{n} товар", "few": "{n} товари", "many": "{n} товарів", "other": "{n} товару"}},
               "base": {"…": "project values at the last reconcile"}},
    "targets": [{"lang": "en", "path": "l10n/en.json", "values": {"…": "…"}, "base": {"…": "…"}},
                {"lang": "fr", "path": "l10n/fr.json", "values": {"…": "…"}, "base": {"…": "…"}}]
  },
  "terms": [{"id": "банківська-картка", "source": "банківська картка", "target": "bank card",
             "meaning": "a payment card linked to the account", "variants": ["bank card", "card"],
             "match": {"stems": ["банківськ\\w* картк"], "keys": ["card.title"]}}],
  "questions": [{"id": "Q1", "title": "Formal or informal address?", "gist": "…",
                 "options": [{"key": "A", "text": "Formal", "consequence": "…"},
                             {"key": "B", "text": "Informal", "consequence": "…"}],
                 "recommendation": {"key": "A", "why": "…"}, "terms": [], "keys": []}],
  "review": [{"lang": "uk", "key": "card.title", "severity": "significant", "reason": "term",
              "was": "Банківська картка", "proposal": "Картка", "why": "…"}],
  "projectChanges": [], "invalid": [], "interpreted": [], "rejected": [],
  "approved": {"en.card.title": {"round": 2, "value": "Bank card"}},
  "releases": {"prod": {"tag": "v1.8.2b435_PROD", "version": "1.8.2+435"},
               "test": {"tag": "v1.8.4b437_FOR_TEST", "version": "1.8.4+437"}},
  "stages": {"en.card.title": {"stage": "test", "inTest": true, "prodText": "Card"}},
  "codeDefects": [{"key": "pay.confirm", "text": "One button for two different dialogs: no text fits both",
                   "uses": [{"where": "Leaving the cart", "question": "Leave without paying?", "action": "leaves the cart", "needed": "Leave"},
                            {"where": "Removing a card", "question": "Remove this card?", "action": "removes the card", "needed": "Remove"}],
                   "why": "…", "now": "…", "devTask": "Split into two keys: …"}],
  "compositions": [{"id": "pay-total", "keys": ["pay.prefix", "pay.items"], "pattern": "{pay.prefix} {n} {pay.items#n}",
                    "sample": {"n": 3}, "site": "lib/pay/total.dart:42"}],
  "risk": [{"keys": ["pay.confirm"], "class": "payment",
            "why": "The text confirms a charge: a wrong word makes people pay by mistake or abandon payment."}],
  "identical": [{"key": "brand.name", "why": "product name"}],
  "batches": [{"id": "pay", "label": "Payments", "prefixes": ["pay."], "expected": 2},
              {"id": "rest", "label": "Other", "prefixes": [], "expected": 4}]
}
```

- `title` — `Погодження текстів <product>` for all values of `lang`. `build` writes it into the
  page's `<title>`, and the artifact gets its name from that tag.
- `values` — the artifact's texts; `base` — the project's values at the last reconcile; in
  round 1 `base` equals `values`.
- `files.targets` — one entry per translation, the first one fixed across rounds; a spec with
  `files.target` (one object) reads as a list of one, `apply` writes `targets`. `check` refuses a
  repeated language and a source key starting with `<lang>.` of a later target. Terms, questions
  and the decision rows of the brief belong to the first target.
- A plural is the object of CLDR forms as in the file — in `values`, `was` and `proposal` alike.
- `was` and `proposal` are the key's full strings. No full string derivable → `proposal` is
  empty and the instruction goes to `why`. A review row covering several keys is split per key.
- Every key below high confidence shows "Що вирішити" on its card: one line per reason (review
  row, code defect, risk, invalid or interpreted edit, question, project change, change since the
  last round, untranslated term), with "Детальніше" opening the review row with its answer buttons
  (the same answer as on the Review tab), the defect fields and the risk class's `why`.
- `fullReview` — per target, the round whose ux-translate Review covered every key of its file;
  `apply` carries it into the next round and prints `no full review: <lang>` for each target it
  lacks.
- `risk` items may carry `why`: what goes wrong for the user if a text of that class is wrong.
- `codeDefects` — a defect only the code can fix. Its readers are analysts and designers, not
  developers: say what the user sees, never file names or identifiers. `text` is one line: what is
  wrong and what it means for the text. `uses` lists each place the key shows (`where` as the user
  names the screen or dialog, `question` the text around it, `action` what the control does,
  `needed` the text that place calls for); `why` is the problem in two sentences, `now` what an
  editor does this round, `devTask` the change in code, worded for a ticket. All but `key` and
  `text` are optional; the card shows `text` and folds the rest under "Детальніше". A key in a
  composition shows its phrase under `text` too.
- `compositions` — a phrase the code assembles from several keys. `pattern` is the assembly as the
  code does it: `{<localeKey>}` for a key, `{<name>}` for a `sample` value, `{<localeKey>#<name>}`
  for a plural key counted by that sample value. Each named key's card shows the assembled phrase
  in both languages with its own part marked; `check` refuses a key outside the source values, a
  key of `keys` the pattern lacks, a token naming neither, and a non-numeric count. A
  placeholder inside a key's text takes the sample value of its name; a positional `{}` takes
  `sample[""]`.
- `interpreted` (`{lang, key, text, by}`) — an editor's text that failed the checks and that you
  rewrote by its evident intent: `text` and `by` are the editor's original and name, the key's
  value is your rewrite. The key drops to low confidence and its card quotes the original.
- Term `id` — the source word in lower case, spaces as `-`, only letters of any alphabet, digits
  and `-`. A term without a translation has an empty `target`.
- A question's `title` quotes its Open questions item of the brief verbatim — `apply` finds the
  item by it. Options come only from the brief and the review — for a question raised by an
  editor's comment, also from that comment and the language pack; `recommendation` is omitted when
  none of them gives one.
- A question's `keys` — the locale keys it is about; `check` refuses an unknown key, and each
  named key's card lists the question.
- Batches: a key falls into the first batch whose prefix matches, in spec order; the last batch
  has no prefixes and takes the rest; `expected` is its key count.
- `projectChanges` (`{lang, key, kind, value}`), `invalid` (`{lang, key, reason}`) and `rejected`
  (`{lang, key, proposal}`) are written by `apply`; round 1 has them empty, as `interpreted`,
  except the `added` entries of the queued keys ([Approval queue](#approval-queue)).
- `apply` writes `approved` (`{"<lang>.<key>": {round, value}}`). A text is approved in
  round n when an editor answered its slot in round n: an edit, a review answer or a tick. An
  unanswered `conflict` of that language keeps the text unapproved. An answer on a target approves
  the key's source text too. `apply` carries an entry to the next round only when the reconcile
  left the key `artifact` and the value stays the same. The key card shows an approved mark per
  language.
- `stages` ([Stages](#stages)) writes `releases` (`{prod: {tag, version} | null, test: {tag,
  version} | null}`) and `stages` (`{"<lang>.<key>": {stage, inTest, prodText}}`).
  `stage` is `prod` when the text equals the prod tag's text, else `test` when it equals the test
  tag's text, else `dev`. `inTest` is true when the text equals the test tag's text. `prodText` is
  the prod tag's text when the prod tag holds the key with another text. The key card shows the
  stage and the build version per language; the Keys tab filters keys by stage.
- Confidence is computed per language too: the key-wide reasons (question, risk, code defect) count
  for every language, the rest for the language they name, an untranslated term for the target.
  The card shows each language's level beside its text and the worst one in the head. An
  untranslated term counts for every target.
- `text_rules.json` holds the rules both `apply` and the page run on an editor's text: a script
  foreign to the language, placeholders differing from the round's text, an empty plural form.
- A term's `approved` is the round whose answer set its `target`, written by `apply`; the page
  folds approved terms until someone opens or answers them. `apply` also writes each approved term
  into the Terms table of the brief: the row whose first cell is the term's `source` (any case) gets
  `target` in its second cell and `accepted` in the `status` column, if the table has one; without
  such a row a new one gets `source`, `target`, `meaning` in the column whose header starts with
  `meaning`, `accepted` in `status`, the rest empty. The brief thus carries every approved term.
- A row nobody answered, whose `was` still matches the text, `apply` carries into round n+1 as
  is, in any language. A target text an editor set in round n shows its round-n text on the Keys
  tab and gets Review in step 6.
- Page ids are fixed by this shape and survive rounds: `key.<localeKey>` for the first target,
  `key.<lang>.<localeKey>` for every later one, `source.<localeKey>`, `comment.<localeKey>`,
  `review.<lang>.<localeKey>`, `term.<id>`, `q.<id>`.
- The Review and Keys tabs show the source with one target at a time; with two or more targets a
  switcher above the list picks the pair and counts each pair's answers. The Review tab lists the
  target's rows first, the source's last; a language filter above them shows all rows, the
  source's or the target's, counts each option's rows and keeps the choice in the browser.

Round 1 from ux-translate outputs:

| ux-translate output | spec field |
|---|---|
| brief | `brief`; Terms rows with status `proposal` and terms without a translation → `terms` (`accepted` rows stay only in the brief); Open questions → `questions`; intentional-identity exceptions → `identical`; batch plan → `batches` |
| Review, source only, and "source defects found" | `review` rows with the source `lang` |
| Review of a target | `review` rows with that target's `lang` |
| skips caused by the code | `codeDefects` with `uses`, `why`, `now`, `devTask` read from the code at each call site; for each one assembled from several keys, also `compositions` — grep the code for the key and copy its assembly |
| "needs a human" | `risk`, each class with `why`: what goes wrong for the user if its text is wrong, in words for analysts and designers |

### UI strings

Strings of the key card's fields, toggles and comment, the summary sections, the comment, review
and row-language filters, the export order panel, the stage line, the approved mark and the stage
filter; `{n}`, `{lang}`, `{text}` and `{version}` stay as written.
`releaseProd` and `releaseTest` serve the round bar and the key card. `stageNone` also labels the
"not in a build" option of the stage filter; `stageFilter` is that filter's `aria-label`.

| key | uk | en |
|---|---|---|
| `reviewOverridden` | Перекрито правкою на вкладці «Ключі». | Overridden by an edit on the Keys tab. |
| `commentToggle` | Коментар | Comment |
| `divergeHint` | Відповідь іншого редактора відрізняється від вашої | Another editor's answer differs from yours |
| `divergeLine` | інша відповідь | different answer |
| `editedMark` | ваша правка | your edit |
| `conflictHint` | Текст змінено і тут, і в проєкті — оберіть, який залишити | The text changed both here and in the project — pick which one to keep |
| `restoreTo` | Повернути «{text}» | Restore “{text}” |
| `sectionSource` | Тексти джерела | Source texts |
| `sectionKeyComments` | Коментарі до ключів | Key comments |
| `filterCommented` | з коментарями | with comments |
| `filterReviewRows` | з пропозицією ревʼю | with a review proposal |
| `exportOrderTitle` | Порядок редакторів для {lang}.json | Editor order for {lang}.json |
| `exportOrderIntro` | Кілька редакторів змінили тексти. Кожен текст береться від першого в списку, хто його змінив. Закриття раунду це не зачіпає. | Several editors changed texts. Each text comes from the first editor in the list who changed it. Closing the round is not affected. |
| `exportOrderConfirm` | Вивантажити | Download |
| `exportTerms` | Словник (md) | Glossary (md) |
| `commentsTitle` | Коментарі редакторів | Editors' comments |
| `roleSource` | основа | source |
| `roleTarget` | переклад | translation |
| `confidenceOverall` | Найнижча впевненість серед мов ключа | The lowest confidence among the key's languages |
| `langWhy` | Чому: {reasons} ↑ | Why: {reasons} ↑ |
| `phraseTitle` | Частина фрази {pattern}; виділено цей ключ | Part of the phrase {pattern}; this key is marked |
| `phraseSite` | Збирається в коді: {site} | Assembled in code: {site} |
| `interpretedNote` | {lang}: правку {who} «{text}» витлумачено як поточний текст; не так — виправте | {lang}: {who}'s edit “{text}” was read as the current text; fix it if that is wrong |
| `issuesNote` | Ця правка не застосується: {issues}. Пояснення — у «Коментар» | This edit will not apply: {issues}. Put explanations in Comment |
| `issue_foreignScript` | літери іншої абетки | letters of another alphabet |
| `issue_placeholders` | змінні мають бути {detail} | placeholders must be {detail} |
| `issue_emptyForm` | порожня форма {detail} | empty form {detail} |
| `pairsLabel` | Пара мов | Language pair |
| `reviewLangLabel` | Мова рядків | Row language |
| `defectMore` | Детальніше | Details |
| `defectLess` | Згорнути | Hide |
| `defectComposed` | Фраза складається з кількох ключів: перевіряйте її цілком | The phrase is assembled from several keys: check it whole |
| `defectUses` | Де використовується | Where it shows |
| `defectWhy` | Чому це проблема | Why it is a problem |
| `defectNow` | Що зробити зараз | What to do now |
| `defectDevTask` | Що потрібно від розробки | What development needs to do |
| `defectTaskTag` | задача | task |
| `useQuestion` | Текст: «{text}» | Text: “{text}” |
| `useAction` | Кнопка {text} | The button {text} |
| `useNeeded` | Тут потрібно: | Needed here: |
| `reasonComposed` | склейка фрази | assembled phrase |
| `decideTitle` | Що вирішити | What to decide |
| `decideReview` | {lang}: ревʼю пропонує інший текст ({severity}) | {lang}: the review proposes another text ({severity}) |
| `decideDefect` | Дефект коду | Code defect |
| `decideRisk` | Ризик: {risk} | Risk: {risk} |
| `decideQuestion` | Питання {id}: {title} | Question {id}: {title} |
| `decideChanged` | {lang}: текст змінено з раунду {n} | {lang}: text changed since round {n} |
| `decideTerm` | Термін без перекладу: «{term}» | Untranslated term: “{term}” |
| `reviewNow` | Зараз | Now |
| `reviewProposes` | Ревʼю пропонує | The review proposes |
| `reviewWhy` | Чому | Why |
| `decideSameAnswer` | Та сама відповідь, що на вкладці «Ревʼю»: зміниться і там. | The same answer as on the Review tab: it changes there too. |
| `stageNone` | ще не в збірці | not in a build yet |
| `releaseProd` | прод: {version} | prod: {version} |
| `releaseTest` | тест: {version} | test: {version} |
| `stageProdText` | у проді інший текст | other text in prod |
| `stageProdLine` | у проді {version}: | in prod {version}: |
| `approvedMark` | затверджено · раунд {n} | approved · round {n} |
| `answerReset` | Текст змінено в проєкті після відповіді: відповідь не враховано. | The project text changed after the answer: the answer does not count. |
| `stageFilter` | Збірка | Build |
| `stageAll` | Усі збірки | All builds |
| `stageProd` | прод | prod |
| `stageTest` | тест | test |
| `stageTestUnapproved` | тест, не затверджено | test, not approved |

`reasonCode` is a map, one entry per reason kind: `question` питання / question, `risk` ризик /
risk, `codeDefect` дефект коду / code defect, `review` ревʼю / review, `conflict` конфлікт з
проєктом / conflict with the project, `invalid` правка не пройшла перевірку / edit failed the check,
`interpreted` правку витлумачено / edit interpreted, `changed` змінено з минулого раунду / changed
since the last round, `term` термін без перекладу / untranslated term, `project` змінено в проєкті /
changed in the project, `added` новий ключ / new key.

## Database

The page writes, you read:

- `log/<auto>` — `{object, by, at, round, pick, text, reviewed}`, one document per answer change;
  `object` is a page id, or `note.<id>` for an editor's comment (`pick: "custom"`, the comment in
  `text`; an empty pick and text withdraw it).
  - `key.<localeKey>` sets the first target's text (the source text when only the source has a
    project conflict), `key.<lang>.<localeKey>` that target's text, `source.<localeKey>` the
    source text (`pick: "custom"`, the text in `text`; an empty pick and text restore the round's
    text). Each shares a slot with `review.<lang>.<localeKey>` of the language it sets; `apply`
    takes the editor's latest value-setting answer in the slot.
  - `comment.<localeKey>` is a comment on one key, shaped like `note.<id>`; each author has their
    own.
- `editors/<userId>` — `{email, name, firstSeenAt}`.
- `rounds/<n>` — `{closedAt, by, priority: [userId, …]}`, written by the owner; its presence
  closes round n.

## Approval queue

`approval-queue.md` lies beside the project's brief, whose path the `## Localization` section of
the project's AGENTS.md names; it holds the line `Approval: <artifact url>, round <n>, open` and the
table `| key | date |` of keys awaiting approval. No such section → the queue
is not read, no `Approval:` line is written, and the Report says so.

- Create puts each queued key into `projectChanges` as `{lang, key, kind: added, value}`, one entry
  per language whose file has the key, so editors see it.
- An open latest round: the start compares the queue's keys with the artifact's keys ([Mode](#mode)).
- Next round reads no queue: the reconcile already marks keys changed in the project `added` or
  `project` and names them in `named-keys.txt`.
- After each publish write one line `Approval: <url>, round <n>, open` into
  the queue file in the working tree, replacing its previous `Approval:` line; no file → create it
  with that line and the empty `| key | date |` table. Do not commit it.

## Stages

Every mode runs Stages on the spec before `check`.

1. **Lines** — read `Prod tag:`, `Test tag:` and `Test branch:` from the `## Localization` section
   of the project's AGENTS.md. `Prod tag:` and `Test tag:` hold a tag glob; `Test branch:` names
   the branch of test builds. A line is missing → ask the user for its value, show the lines, and
   write them into the section after "yes".
2. **Tags** — `git -C <root> fetch --tags`.
3. **Stages** — `python3 approval.py stages <spec> --project <root> --prod-tag <glob> --test-tag
   <glob>`. It rewrites `releases` and `stages` in the spec. It picks the newest tag of each glob
   by version. It drops the test tag when its commit is not newer than the prod tag's commit. For
   each test-tag text that differs
   from the prod tag's text and lacks an `approved` entry of that value, it prints
   `release <version>: unapproved <n>: <keys>`. This line goes to the Report as a warning; it
   stops nothing.

## Create

1. **Snapshot** — read every locale file in full into `files.source.values` and
   `files.targets[].values`; `origin` is the project's branch and `HEAD` commit. Locale files with uncommitted changes → ask the user first.
   Read the queue ([Approval queue](#approval-queue)).
2. **Review** — ux-translate Review, source only, over every source key, and ux-translate
   Review of each target over every key of its file; their findings become `review` rows by the
   table above.
3. **Spec** — write `<scratch>/spec.json` by the shape and table above, `round: 1`,
   `fullReview: {<target>: 1}` for each target.
4. **Check** — [Stages](#stages) on `<scratch>/spec.json`, then
   `python3 approval.py check <scratch>/spec.json` must print `ok`; fix each
   `spec:` line and rerun. Exit 0 ok, 1 spec errors, 2 usage error.
5. **Build** — `python3 approval.py build <scratch>/spec.json --stats` writes `page.html` beside
   the spec.
6. **Publish** — Artifact publish of `page.html` with an `icon`, `title` from the spec and:
   ```
   capabilities: {
     db: {rules: [
       {path: "log", read: "view", write: "admin"},
       {path: "editors", read: "view", write: "owner"},
       {path: "editors/{self}", write: "admin"},
       {path: "rounds", read: "view", write: "owner"}]},
     user: {scopes: ["profile"]},
     downloads: true}
   ```
   Then write the `Approval:` line ([Approval queue](#approval-queue)).
7. **Verify** — `ArtifactData list` of `log`, `editors` and `rounds`, then each again with
   `as_level: "view"`. `set` of `rounds/probe` with `as_level: "admin"` must be refused; a write
   that lands means the rules are wrong — delete the probe, fix the declaration, republish.

## Next round

Next round is the cut of round n.

1. **Read** — Artifact read of the url; the saved `page.html` is `--previous` and the rollback.
   Its latest round is n.
2. **Answers** — `ArtifactData list` of `log` and `editors` (page with `query.limit` and
   `next_cursor`, or `out_dir`), `get` of `rounds/<n>`. An `editors` document with an empty
   `name` gets the display name `ArtifactData profiles` returns for its id. Save `log` and
   `editors` as one JSON file each in `<scratch>` — the list of `{id, data}` documents as
   returned — and the `rounds/<n>` document `{id, data}` as `round.json`.
3. **Apply** — `python3 approval.py apply <page.html> <log.json> <editors.json> <round.json>
   --project <root> -o <dir>`, `<dir>` a fresh folder in `<scratch>` (inside `<root>` → exit 2).
   It writes `spec-next.json`, `brief.md`, `<lang>.json` per language, `named-keys.txt`,
   `changed-<target>.jsonl` per target, `conflicts.md`, `free-text.md`, `suspect.jsonl`, and on
   stdout `no full review: <lang>` for each target the page records no full Review for.
4. **Check editors' texts** — for each target, `python3 ../ux-translate/check_drafts.py
   <dir>/changed-<target>.jsonl --lang <target>` with `--ratio` as ux-translate runs it. Each key
   in a non-`warning:` line keeps its round-n value in `spec-next.json` and goes to `invalid` with
   the reported problem. A key whose value this step sets loses its `review` row of that language.
   Each line of `suspect.jsonl` is an editor's text that failed `text_rules.json` — often a comment
   typed into the text field. Its intent evident (one reading only) → write the text it asks for in
   that language into `spec-next.json` and `<dir>/<lang>.json`, and add `{lang, key, text, by}` from
   the line to `interpreted`. Ambiguous → the key keeps its round-n value, goes to `invalid`, and the
   text becomes a question as in step 5, `keys: [<key>]`.
5. **Brief** — `apply` has already put the `term.*` answers into `<dir>/brief.md`; fold each
   `note.*`, `comment.*` and `q.*` answer of `free-text.md` into it where it belongs (a decision, a
   rule). Each `note.*` line is an editor's comment: a settled fact goes into the
   brief; an open point becomes a question for the next round — options, consequences and a
   recommendation. Each `comment.<localeKey>` line is the same, and its question carries
   `keys: [<localeKey>]`.
6. **ux-translate** on the files in `<dir>` with `<dir>/brief.md`, for the keys of
   `named-keys.txt` unless a bullet names other keys — naming them lifts its no-overwrite rule:
   - Review, source only → `review` rows of the source language;
   - Review and Translate of each target → texts written to `<dir>/<target>.json` after its exit 0;
   - Review of each target, also for every key of `changed-<target>.jsonl` → `review` rows of that
     target. Such a key has a text an editor set this round: it gets Review, not Translate;
   - Review of each target `apply` printed as `no full review: <target>`, over every key of
     `<dir>/<target>.json` → `review` rows of that target.
   Its tables go to the artifact, not to the user: the next round is where editors answer them.
7. **Merge** — into `spec-next.json`: `brief` from `<dir>/brief.md`, the new source and target
   `review` rows (a new row replaces a carried row of the same language and key), the questions
   raised by comments, the named keys' target texts into `files.targets[].values`, `interpreted`
   from step 4, `fullReview[<target>]` set to n+1 for each target reviewed in full in step 6, and
   `compositions` for codeDefects keys that lack one (as in the Create table). `apply` copies `ui`
   from the previous page: add each key of [UI strings](#ui-strings) that `ui` lacks, in the spec's
   `lang`.
8. **Deliver** — [Deliver](#deliver).
9. **Check and build** — [Stages](#stages) on `<dir>/spec-next.json`, then
   `python3 approval.py check <dir>/spec-next.json --previous <page.html>` must print `ok`; then
   `python3 approval.py build <dir>/spec-next.json --previous <page.html> --stats`.
10. **Publish** the new `<dir>/page.html` to the same url with `title` from the spec, without
    `capabilities`. Rollback: publish the saved previous `page.html` to that url. Then write the
    `Approval:` line ([Approval queue](#approval-queue)).
11. **Duplicates** — search `--project` for a second source of truth on terms: a markdown file
    outside `plan/`, other than the brief and `approval-queue.md`, with a table where at least two
    rows match terms of `<dir>/brief.md` (any case; `meaning` by sense, not wording) by the first
    Terms column, by the source-variants-to-flag column or by `meaning`, or with a heading only the
    brief has (`Terms`, `Do not use`, `Text component catalogue`). A table whose value column holds
    code identifiers in backticks is a code glossary and not a duplicate. The project is not written: duplicates go to the
    Report.

## Deliver

1. **List** — `python3 approval.py deliver <dir>/spec-next.json --previous <page.html> --project
   <root> -o <dir>`. It writes
   `approved-<lang>.json`: each approved text of any round that the project working tree lacks, as
   `{key, source, round, was, value}`. It leaves out keys of `invalid`, `interpreted` and
   `suspect.jsonl` and keys that steps 4–7 changed, and removes them from `approved`. It also writes
   `approved-keys.txt`: the keys approved in every language.
2. **Ask** — every `approved-<lang>.json` is empty → skip this step. Otherwise ask one question
   with the count of texts:
   - "write here" → ux-translate Apply approved in the working tree of the run branch, with the
     files of `<dir>`. Do not commit. The Report names the changed files.
   - "PR into `<Test branch>`" — only when the run branch is another branch. Make a worktree from
     `Test branch` and run ux-translate Apply approved step 1 there. Commit only the locale files,
     open a PR, then run `bash ~/.claude/skills/implement-plan/prune_worktrees.sh <worktree>`.
     Then run Apply approved steps 2–3 in the working tree of the run branch.
   - "not now" → write nothing. The Report lists the keys, and the next cut offers them again.

## Append

Append adds new or changed project keys to the open round n. Round n stays open and keeps its
answers.

1. **Read and answers** — steps 1–2 of Next round, without the `rounds/<n>` document.
2. **Apply** — `python3 approval.py apply --append <page.html> <log.json> <editors.json> --project
   <root> -o <dir>`. It applies no answers, and `round` stays n. A key with a round-n answer whose
   project text changed gets a `conflict` with `since`, the append time. An answer older than
   `since` does not decide that conflict. `since` comes from this machine's clock and `at` from the
   editor's browser, so a slow editor clock can drop an answer given just after the append.
3. **ux-translate** — step 6 of Next round, without the Review for `no full review` lines.
4. **Merge** — step 7 of Next round, with three changes. A new review row does not replace a
   carried row that has a round-n answer. `fullReview` stays n. `interpreted` stays as
   `apply --append` wrote it. Remove the `approved` entry of each text that this step changes:
   `check` refuses an approved value that differs from the files.
5. **Check and build** — step 9 of Next round, with `--append` on `check` and `build`.
6. **Publish** — step 10 of Next round.

## Report

In the user's language, one line each, empty ones omitted:

- artifact url and round number;
- branch and commit of the reconcile (`origin`);
- answers applied; disputes and their winners (`conflicts.md`);
- the release warning lines of [Stages](#stages);
- Deliver: the keys written and the changed files; the keys not applied, with the reason; the
  keys left for the next cut after "not now";
- `invalid` keys with the reason; `interpreted` keys with the editor's original; `project`, `conflict`, `added` and removed keys, counted;
- keys passed to ux-translate, counted;
- what Verify exercised and what it could not (Create);
- the `Approval:` line written to `approval-queue.md` and left uncommitted, or that the project's
  AGENTS.md has no `## Localization` section, so the queue was not read;
- duplicates of the brief, `path | what it repeats`: remove them with ux-translate Brief;
- the next action: editors answer, the owner closes the round.
