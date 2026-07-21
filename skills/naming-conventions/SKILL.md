---
name: naming-conventions
description: Analyze the project's actual naming conventions across layers
  (data/domain/presentation) and record them as a Naming Conventions section
  in the project AGENTS.md. Use for "проанализируй нейминг проекта",
  "зафиксируй нейминг-конвенции".
argument-hint: [ optional layer or directory to focus on ]
---

1. Map the project layout: locate the data / domain / presentation layers
   (or the project's actual layer structure).
2. Per layer, collect the real vocabulary via grep, counting occurrences —
   the dominant pattern is the rule, deviations become listed exceptions:
   - class suffixes/prefixes and which layer owns which (Entity, Data/Dto,
     Repository, UseCase, Cubit/State, Screen/Widget, ...);
   - fields and variables: booleans, collections, ids, dates, callbacks;
   - methods: CRUD verbs, mappers (toEntity/toData), predicates, handlers;
   - constructor/method argument naming;
   - key formats if present: routes, locale keys, analytics events.
3. Write a compact "## Naming Conventions" section (~15-20 lines) into the
   project AGENTS.md: one rule per category + 1-2 real precedent paths.
   Areas without a clear winner: mark "no dominant convention". If the
   section already exists — update it in place, don't duplicate.
   Touch only the "## Naming Conventions" section: never rewrite or delete
   other sections (e.g. "## Review Conventions" — maintained by hand from
   user feedback, not derivable from code).
4. Report in Russian: what was recorded, dominant patterns, and found
   inconsistencies worth cleaning up (file:line).
