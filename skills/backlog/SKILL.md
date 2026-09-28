---
name: backlog
description: Park deferred work and tech debt in docs/BACKLOG.md, harvest TODOs, groom the list. Use for "запиши в техдолг", "в бэклог", "что в бэклоге", "разбери техдолг", "tech debt".
argument-hint: "[ what to park, or: groom | harvest TODO ]"
---

One file per project: `docs/BACKLOG.md`, committed so the whole team sees the tech debt. Create
it when missing, with this header:

```markdown
# Backlog

Next id: TD-001
```

An entry is only useful if it says **why it was deferred** and **what makes it actionable
again**. Without those two the list turns into a graveyard.

## When to add

Work that is real, out of scope now, and still worth doing:

- the user asks to park it ("запиши в техдолг", "в бэклог");
- something is blocked on an external event — a release, a third-party change, a decision;
- a TODO in the code has no owner and no date (see Harvesting).

A task that uncovers an unrelated defect or cleanup: offer one line — "записать в техдолг:
<title>?" — and add nothing until the user agrees.

## Do not add

- a decision made and rejected — it belongs in the relevant doc as a rejected option;
- speculative improvements nobody asked for;
- anything already in the team's issue tracker — link the ticket instead;
- an open question awaiting an answer — it belongs in the task's own doc.

## Entry format

```markdown
### TD-007 — Short imperative title

- **Status:** deferred | blocked | in progress
- **Opened:** YYYY-MM-DD
- **Source:** code TODO | session | code review | incident
- **Locations:** `path/to/file:123`, `path/to/other:45`
- **Why deferred:** one honest sentence
- **Unblocked by:** a concrete, checkable event
- **What to do:** 2–4 lines, enough to start without archaeology
```

- Take the id from `Next id:`, then increment that line. Ids are never reused.
- `Unblocked by` must be checkable: "when there is time" is not a trigger; "after the API ships
  the `status` field" is.
- Line numbers rot: re-grep the location before touching the code, never trust the stored one.
- Newest entry at the top. Never renumber.
- Done or dropped entry: delete it. Git history keeps it; the commit message names the id.

## Harvesting TODO

```bash
git grep -nIE '(//|#|/\*)[[:space:]]*!?[[:space:]]*(TODO|FIXME|HACK|XXX)([^[:alnum:]_]|$)'
```

Read the surrounding lines, not only the marker — the entry must stand alone. Date each marker
with `git blame -L <n>,<n> <file>`; a three-year-old TODO is a different item from last week's.
Markers that describe one missing capability across several call sites become one entry with
several `Locations`.

Leave the TODO in the code. Append the id — `// TODO(TD-007): …` — only when the user asks,
since that edits source.

## Grooming

On "что в бэклоге", "разбери техдолг", or "what to pick up next":

1. Re-grep each open entry's locations. Report the ones already fixed or whose files are gone
   as candidates to delete.
2. Check every `Unblocked by`. An entry whose event has happened is the most valuable item on
   the list — put it first.
3. Report oldest-first within each status, with age in days.
4. Propose deletions: entries nobody will ever do, with one reason each.

Report in Russian, then wait for the user's decision.

## Never

- Start working an entry during grooming.
- Add an entry without the user's agreement.
- Commit — that is `commit-changes`.
