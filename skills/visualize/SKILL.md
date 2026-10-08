---
name: visualize
description: Turn a plan, brief or contract into an HTML page with one overall diagram and a small diagram per point. Use for "визуализируй", "нарисуй схему", "visualize this doc".
argument-hint: "[ path to the document ]"
---

Visualize the document at the path you were given; ask for it if none is given. You write only a
JSON document; `visualize.py` checks it and renders the page. Never write mermaid or HTML by hand.
Run the script from this skill's folder.

## Page model

The page is read top-down, and each level is enough on its own:

1. **Overall diagram** — the whole document at a glance. A reader who looks only at it can retell
   the document: what starts it, the one main branch with every variant, what each variant leads
   to, what every side sees in the end. Every new or changed entity is on it; every write the
   source makes is a node or a `note` on one. A secondary condition that lives inside one variant
   ("only if the order has a discount") is a `note` on that node here and a branch in its own
   section.
2. **Points** — at most 6, each collapsed to `title` + `takeaway`. Reading only the takeaways
   retells the source. Open questions sit below the points in `questions`, never as a point.
3. **Point diagram** — every point has one. It zooms into its own topic: it may start from one
   overall node, and it adds at least one node or branch the overall diagram does not have. Text
   under it only adds detail the diagram cannot carry.

Each fact appears once, at the level that shows it best. A topic too thin for its own point
merges into the point it serves.

## Flow

1. **Read** the whole source document.
2. **Model** — list what the document creates, changes or relies on (entities); mark each `new`,
   `changed` or `same` from what the document says. Then draft the overall diagram, then the
   points, following the page model.
3. **Write** `<source stem>.visual.json` beside the source, in the shape below.
4. **Trace** — walk the source paragraph by paragraph and name where each fact sits on the page
   (overall node, note, section diagram, `lines`, view) or why it is left out (only a parent
   document's context). A fact with no place gets one; a fact in two places loses one. Every
   condition, reason and precondition the source gives is a fact.
5. **Check** — `python3 visualize.py check <json>` must print `ok`. Then
   `python3 ../clarifier/clarify.py check <json>`: fix its errors as check errors; `hint:` lines
   are optional. Fix each reported line, rerun; after 3 failed runs stop and report the remaining
   problems.
6. **Review** — one reviewer in a fresh context: `visual-reviewer` in Claude Code
   (`<plugin>:visual-reviewer` as a plugin); in Codex, `explorer` with the visual-reviewer
   criteria, told to read only the two files. Pass both paths and both contents. Verify each
   finding against the source, the JSON and the page model; drop the ones that do not hold,
   including any that moves a fact to the level the page model does not give it.
7. **Correct** — apply every finding that holds, Minor included, then rerun the check. Then
   review again in a new fresh context and correct once more. Stop after the second correction
   even if findings remain: they go to the report, a remaining Blocking or Significant first.
8. **Render** — `python3 visualize.py render <json>` writes `<json stem>.html` beside it.
9. **Look** — open the page in a browser; a mermaid error shows as an error box, not a failed
   command. Then hand the page to the user.

## Document shape

```json
{
  "title": "Order export to CSV",
  "summary": "One sentence: what the document makes different.",
  "lang": "en",
  "ui": {"new": "new", "changed": "changes", "same": "unchanged", "context": "nearby, unchanged",
         "overview": "Whole picture", "files": "Files", "branch": "branch by condition",
         "decide": "To decide", "question": "Question", "recommend": "Recommend"},
  "questions": [
    {"title": "Export cancelled orders too?",
     "gist": "The source does not say; a cancelled order has no total, so its row would be half empty.",
     "options": [{"key": "A", "text": "Skip them", "consequence": "the file holds only paid orders"},
                 {"key": "B", "text": "Export them", "consequence": "accounting sees every order"}],
     "recommendation": {"key": "A", "why": "the export is for accounting"}}
  ],
  "entities": [
    {"id": "screen", "name": "Orders screen", "code": "OrdersScreen", "status": "changed",
     "change": "export button", "files": [{"path": "lib/orders/orders_screen.dart", "status": "changed"}]},
    {"id": "export", "name": "Order export", "code": "OrderExport", "status": "new",
     "change": "orders to CSV rows", "files": [{"path": "lib/export/order_export.dart", "status": "new"}]}
  ],
  "links": [{"from": "screen", "to": "export", "label": "starts"}],
  "flow": {
    "nodes": [
      {"id": "tap", "label": "User taps Export", "entity": "screen"},
      {"id": "has", "label": "Any orders?", "kind": "check"},
      {"id": "csv", "entity": "export", "note": "one row per order"},
      {"id": "empty", "label": "Message: nothing to export", "kind": "result"}
    ],
    "edges": [
      {"from": "tap", "to": "has", "label": "checks"},
      {"from": "has", "to": "csv", "label": "one or more"},
      {"from": "has", "to": "empty", "label": "none"}
    ]
  },
  "sections": [
    {"title": "The orders screen gets an export button",
     "takeaway": "One button on the orders screen saves every order as a CSV file.",
     "entities": ["screen"],
     "lines": [{"label": "Now", "text": "Orders can only be viewed."}]},
    {"title": "Rows follow the order list",
     "takeaway": "Each order becomes one row; cancelled orders are left out.",
     "flow": {
       "nodes": [
         {"id": "o", "label": "Each order", "entity": "export"},
         {"id": "st", "label": "Order status?", "kind": "check"},
         {"id": "row", "label": "Row in the file", "kind": "result"},
         {"id": "skip", "label": "Skipped", "kind": "result"}
       ],
       "edges": [
         {"from": "o", "to": "st", "label": "checks"},
         {"from": "st", "to": "row", "label": "`paid`, `shipped`"},
         {"from": "st", "to": "skip", "label": "`cancelled`"}
       ]},
     "views": [{"type": "table", "title": "Columns", "columns": ["Column", "From"],
                "rows": [["id", "`Order.id`"], ["total", "`Order.total`"]]}]}
  ]
}
```

- `ui` — every string the page shows besides the content, in the document's language (`lang`).
- Entity — `name` is what a non-developer calls it; `code` the identifier as written in code or
  on the wire (optional for actors such as "backend"); `change` what becomes different (required
  unless `same`); `files` every file the document changes for it — never a document it only
  references.
- Overall diagram — a top-level `flow` when the source describes behaviour (a contract, a
  feature); without it the page draws `entities` + `links`, which fits a set of code changes (a
  plan). A link `label` is a verb: who calls, feeds, reads or writes whom.
- Flow node — `{"id", "label", "entity", "kind", "status", "note"}`. `entity` reuses an entity's
  name, code and status; `kind` is `step` (default), `check` (a branch question) or `result`, and
  may be combined with `entity`; `label` and `note` ≤40 characters not counting backticks; `note`
  says what changes.
- A `note` tells what happens at its own node. A write or step that comes later in the source's
  order sits on the later node, never as a "+ also" note on an earlier one. A rule the source
  gives for every case ("metadata first, then messages") goes where every case is shown, not into
  one variant's section.
- Flow edge — `{"from", "to", "label"}`; `"hidden": true` only places a node below another.
  - An arrow out of a `check` is a variant: its label names the exact values or the condition it
    covers (`` `paid`, `shipped` ``, "not the order's owner"), ≤6 words — never "else",
    "the rest", "and later", or an order like "first"/"second" when the source branches on a
    state. Every case the source names gets its own arrow; never merge cases into "other".
  - Any other arrow carries an action verb, ≤3 words.
  - An arrow leaving a node applies to every case that reaches it. When a later step holds for
    one variant only ("after `received`"), give that variant its own node and start the arrow
    there, or name the variant in the arrow's label; never let two variants join a node whose
    next step only one of them takes.
  - The page draws branches, their arrows and their variant labels in their own colour and lists
    them in the legend (`ui.branch`). Every variation the source describes — outcome by status,
    role, presence of a value — is a `check` node, never parallel steps or a `note`.
- Section — `title`, `takeaway` (its conclusion in one sentence, ≤15 words), and its diagram:
  `flow` when its point is a condition, an order or a rollout; `entities` when its point is what a
  component becomes (drawn with one-link neighbours greyed). `lines` are labelled one-sentence
  statements the diagram cannot carry; `files` holds files no entity owns.
- Views, each optional, in `views`:
  - `{"type": "shape", "title", "root": node}` — a payload as a field tree; a node is
    `{"name", "type", "status", "example", "note", "values", "children"}`. An enum or any field
    whose allowed values the source lists carries them all in `values`
    (`[{"value", "status", "note"}]`), each new or changed one marked so it renders green or blue
    — never in a `note`. Unchanged neighbour fields with no example may share one node:
    `"name": "id · title · createdAt"`; every other field gets its own node.
  - `{"type": "table", "title", "columns", "rows"}` — a hex colour cell renders as a swatch.
  - `{"type": "steps", "title", "items": [{"text", "tag", "note"}]}`.
- Verification — a plan's tests and manual checks become one `lines` entry per section saying
  what they prove ("Tests: day rollover compresses yesterday, deletes expired"); test files go
  in `files`. Individual test cases are not listed.
- Question — `gist` says what is undecided, why it matters and what it affects, with an example;
  every option names its consequence; `recommendation` picks one and says why.
- Text fields accept `` `code` `` and `**bold**`.

## What `check` enforces

- Size: ≤8 entities, ≤10 links; overall flow ≤10 nodes, ≤12 arrows and one level of branching
  (at most one `check`); at most 6 sections; a section flow ≤6 nodes and ≤7 arrows; an entity
  diagram ≤6 nodes with neighbours.
- Coverage: every new or changed entity is on the overall flow and in some section; every section
  shares an entity with the overall flow and has a diagram; a section flow has a node the overall
  flow does not, never reuses the overall branch's variants and never repeats an overall note; under an overall flow a section
  draws a `flow`, not entities already on it; no section repeats the entity diagram of an earlier
  one; a section with a `flow` carries no `steps` view — the order lives in the flow.
- Text: `name`, `code`, `change` ≤40 chars; labels as above; vague variants rejected; no sentence
  in `lines` over 25 words; a `takeaway` in every section.
- Payloads: a changed field shows its `values` or children; a merged `a · b` node is unchanged and
  has no example. Questions are complete.

## What `check` cannot see

- The overall diagram alone retells the document; the takeaways alone retell it too.
- A node name a reader without the code understands; the code name carries the identifier.
- `lines`, notes and examples restate the source; a fact it does not state is left out, never
  guessed. Every condition the source attaches to a rule survives on the page.
- A `lines` statement never retells a node, note or arrow already drawn — on the section's diagram
  or on the overall one; before writing a line, look for its fact on both diagrams and drop it if
  it is there. A section whose diagram says everything has no `lines`.

## Report

In Russian, one line each: the HTML path, the JSON path, the reviewer's verdicts per round, the
fixes applied, findings left unresolved, what was left out of the page and why.
