---
name: backend-contract
description: Write, extend or review a backend contract — endpoints, fields, statuses, events. Use for "контракт для бэкенда", "сверь контракт с реализацией", "разбери сырой контракт бэка", "backend contract".
argument-hint: "[ tasks, or the contract to extend or audit ]"
---

Write the backend contract for the task or tasks the user named.

The deliverable is a document a backend developer reads instead of asking questions — never a
conversational answer. It states what the backend must deliver and why the client needs it exactly so. It
never advises how to implement it inside the backend.

## 1. Mode

- **New** — nothing covers this feature yet. Full skeleton.
- **Extension** — a parent contract exists and stays in force; describe only the delta.
- **Audit** — the document exists; check it against the acceptance criteria and the client code,
  then append what is missing.
- **Review** — the backend sent its own draft or a revision of ours; judge whether it fits
  (step 8a).

Take the mode from the user's request. Ask only when the target is genuinely ambiguous.

The client's architecture outranks every input: the backend, the tickets and the design decide
what happens and the wire shape, never how the client handles it.

## 2. Inputs

Collect what exists, then ask once, in a single question, for whatever is still missing:

- task ids and their acceptance criteria — pasted, a file, or the repository's planning folder;
- designs — a link is enough; the contract quotes what a screen needs, never its layout;
- the parent contract, in extension and audit modes; the backend's draft, in review mode;
- the client implementation (step 3).

## 3. Mine the client — it is the source of truth for the wire shape

Launch 1–2 parallel read-only exploration agents (`Explore` in Claude Code) over the client code.
Each returns, with `file:line`:

- the models and parsers that will consume the payload — exact field names, types, nullability;
- every enum the payload carries — the complete set of values, spelled as the client spells them;
- the stubs, mocks or test data that already fake this response — their shape is the contract's;
- the interface element each fact feeds, so every field in the document has a named consumer.

Never invent a name for a field the client already parses, and never quote a name the client
does not have without saying it is a proposal. When the feature has no client implementation
yet, say so in the report: then every name in the document is a proposal, not an observation.

## 4. Split state from history

Before writing anything, sort every fact from the acceptance criteria into two buckets. This
split is the document's opening rule, and it settles most later questions:

- **State** — what the interface draws in a fixed place and must always show as of now: banners,
  action panels, list rows, buttons, and the gates that enable them. Delivered by whatever
  carries current state in this system — a field of the response, an entity's metadata, a socket
  payload.
- **History** — what stands as a record at its own position with its own timestamp: events,
  messages, records of an action that happened.

Three consequences to state explicitly: state never depends on whether an event was delivered;
the client never reconstructs state from history; a fact that already became a history record is
not duplicated in state.

Name the transport for each bucket, and say whether a state change wakes a disabled client — if
it does not, the contract must name the separate signal that does.

## 5. Draft

Follow `reference/skeleton.md`. Skip a section the feature does not have rather than pad it.

## 6. Self-check before reporting

One line per check, each answered against the draft:

- every acceptance criterion is covered by a field, an endpoint, an event or an explicit rule;
- every field in the document has a named consumer in the interface;
- every enum is listed whole, with the client's fallback for an unknown value;
- every optional field says what absence means and what the client draws instead;
- ordering of operations, the race of two actors, and backfilling already existing entities are
  each answered once;
- nothing in the document tells the backend how to build it internally;
- no assumption of the backend's about client internals — errors, retries, states — entered
  the document or the client plan;
- the document goes to the backend as is: no thread of earlier correspondence is left open.

## 7. Extension mode

The header names the parent, declares it in force unchanged, and says what starts where the
parent ends. Describe only the delta: new fields, new enum values shown beside the existing
ones, new statuses and transitions. Never edit the parent document — a rule of the parent that
the delta invalidates goes into the delta's open questions instead.

## 8. Audit mode

Re-check the document against the acceptance criteria and the client code, then bring it to what
is true now: missing rules go into their own section and everything unresolved into the open
questions; negotiation rounds, answered questions and whatever the backend no longer has to
decide are removed.

## 8a. Review mode

Read the backend's draft as a wire interface only — paths, fields, enums, statuses, events. Its
notes on how the client should process data, handle errors or retry are not requirements and are
not argued back.

- A verdict per point: fits or does not, checked against the acceptance criteria and the client
  facts of step 3.
- A point that breaks the client's architecture or naming gets a counter-proposal worded as the
  field, endpoint or rule the client needs — never a bare question. A wire name the backend keeps
  may differ from the client's key; the client maps it.
- Counter-proposals are appended as a section of the backend's document unless the user names
  another place.
- Once a revision fits, switch to audit mode (step 8).

## 9. Writing rules

- Language: the language the existing contracts of the repository are written in; ask if there
  are none. The reader is a backend developer who has never seen the client code.
- Every non-obvious requirement carries its reference to the acceptance criterion.
- Tables for anything enumerable; a minimal, realistic JSON example per payload, no ellipsis.
- One fact per row, one rule per bullet. No retelling of the client's screens.
- An open question carries the concrete proposal the client would ship, so the answer is yes
  or no.
- Only what the backend has to change or decide: what already matches, what was agreed and what
  a call closed are left out, not listed as done.
- The document stands alone: no path into the client repository, no image or file on the
  author's machine, and an acceptance criterion is cited with its ticket (`<TICKET> AC §4.3`).
- Path: beside the existing contracts of the repository; ask when there are none.

## 10. Report

In Russian, one line each: путь к документу, режим, что вошло, открытые вопросы, и чего не
удалось подтвердить кодом клиента. Документ прозой не пересказывать.
