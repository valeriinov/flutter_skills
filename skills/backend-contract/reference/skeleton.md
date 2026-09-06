# Contract skeleton

Sections in this order. Titles are written in the document's language; the names below are
labels, not headings to copy. Each section says when it is needed — skip the ones that are not,
never pad them.

## 1. Header — always

The feature in one line, then: the task ids with their story numbers, how a reference to an
acceptance criterion reads in the rest of the document, and — in extension mode — the parent
contract with the sentence that it stays in force unchanged and what starts where it ends.

One sentence of ground truth if the feature has a precondition that never varies ("the entity
always exists before anything described here").

## 2. The governing rule — always

The state/history split of SKILL.md step 4, in the document's own words: which interface elements
read state, which records stand in history, and the three consequences. Two short paragraphs.
Everything below leans on this section instead of re-arguing it.

## 3. Who does what — always

| Action | Who performs it |

One row per action the feature contains, including the automatic ones (timers, deadlines,
cascades) and the ones triggered outside the client (admin panel, another service). Close with a
paragraph naming what the client does and nothing more — usually: calls the endpoint on a user
action, and draws the screen from what arrived.

## 4. Endpoints — always, when the feature has request/response calls

Table first:

| Method | Path | Purpose |

Then one subsection per endpoint. Declare the response envelope once for all of them, before the
first example, and show every payload without it.

Per endpoint: the request JSON, the response JSON, then a bullet per field — type, bounds,
meaning, and what the client does with it. Follow with, only where they apply: who may call it
and in which state (a table when there is more than one caller), what the client does *not* need
in the response, validation the backend owns, and the error the client must be able to show.

```json
{ "entityId": 42, "amount": 350 }
```

## 5. Statuses and transitions — only if the feature has a state machine

| Value | What it means | Final |

| From | To | Who initiates | Story |

Below the tables: what stays unchanged across all of these transitions, which values override
which, and what an automatic transition re-reads before it fires.

## 6. State delivery — only if state travels outside plain responses

The transport in three or four bullets a backend developer needs and no more: what the unit of
state is, how a partial update behaves, whether writing it wakes a disabled client, and what
separate signal covers that if it does not.

Then the full field table — every field, not only the new ones, unless this is an extension:

| Field | Type | Purpose |

Then the filling rules as bullets: backfilling entities that already exist, what a partial
update must never delete, what optional means, which fields are cleared together, and which
facts deliberately do not live here because history already carries them.

## 7. Events and their payloads — only if the feature produces history records

Code table first:

| Code | Record type | When |

Then one subsection per record: what the interface draws from it, the JSON, and a bullet per
field. State per record whether it is impersonal or attributed to a person, and to whom — the
actor, not a service account.

```json
{ "eventCode": "somethingHappened", "entityId": 42, "daysCount": 4 }
```

Where the wording differs by who is reading, the record carries a code and the client assembles
the line. Show the mapping as a table and say why the text is not sent ready-made:

| Code | Reader's role | Line |

Close the section with what is deliberately *not* an event, when the backend would otherwise
send one, and what a human-readable text field is still for when the client draws the record
from its payload — usually a preview list and a notification body.

## 8. Scenario walk-throughs — only when one story needs pieces from several sections

A subsection per story whose pieces are scattered across statuses, state fields, history records
and out-of-band signals: what triggers it, what the entity becomes, which records go into
history in which order, and which signal goes out. Nothing new is introduced here — it only
gathers what the sections above already define, so the backend can implement one story without
reassembling it from four tables.

## 9. Rationale — only where the backend would otherwise push back

One short subsection per contested decision: why the backend sends a record it might expect the
client to send, why a fact is state rather than history, why a value is duplicated. Name the
cost of the decision honestly in the last line.

## 10. Order of operations — always, when one action writes more than once

The order for each action, in one line each, plus the rule behind it (usually: the history record
first, the state after, so the other side never sees a changed panel without its record). Close
with what happens when the second write fails — the source of truth does not change.

## 11. Rollout steps — always

Numbered, each step independently shippable and breaking nothing on its own. Then one paragraph
mapping steps to what they switch on, and a sentence about what deliberately stays undone
(history is not backfilled; the client skips what is absent).

A field the same batch of tasks needs but that belongs to none of the sections above gets its
own short closing section — one paragraph naming the field, its type and the response it rides
in — rather than being wedged into a table where it does not fit.

## 12. Open questions — only if there are any

One subsection per question: what the design says, what the contract says today, what changes
once it is answered, and who owns the answer — backend or requirements.

---

# Recurring formulations

Sentences that carry a rule the reader would otherwise ask about. Reword them into the document's
language and domain; keep the rule.

- The response envelope is declared once, before the first example; every payload below is shown
  without it.
- The client does not need the response body — the status is enough; it will see the new state
  where state lives.
- An optional field is either absent or `null`. The client normalizes absence, `null` and an
  unknown value into "none" and simply does not draw what is not there.
- A partial update must not delete any field — neither the new ones nor those written earlier.
  Existing entities are backfilled; history is not.
- A request in a state where the transition is not allowed answers with an error carrying a
  human-readable message. The client shows that message and re-reads the state; it never invents
  a decision of its own.
- Both sides can act at once: the request that reaches the server first wins, the second gets
  the error. The stale screen is cured by re-reading state, not by guessing.
- Where the wording is mirrored by role, the record carries a code and the client assembles the
  line from it and its own role — one record serves both sides and cannot hold two texts.
- Every enum value names the side that acted; a value that names nobody is reserved for what
  happened by itself.
- The history record is written first, the state after.
- If writing the history record fails, the action still happened and state is still updated. The
  source of truth does not change.
- The client does not compute what the backend owns: limits, windows, deadlines and counts
  travel as values, and the document says so where a reader might assume otherwise.
