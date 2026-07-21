---
name: naming
description: Check whether a name (field, method, class, key) is consistent
  with project vocabulary and honest about behavior. Use for "удачное ли имя",
  "консистентность нейминга".
argument-hint: [ file:line or symbol name ]
---

For the symbol at $ARGUMENTS (if the placeholder is not expanded, take the symbol from the user's request):
1. If the project AGENTS.md has a "Naming Conventions" section — read it
   first and check the name against it.
2. Read the declaration and its usages.
3. Grep the project for sibling patterns (same layer, same suffix/prefix
   family) — collect the actual vocabulary in use.
4. Judge: consistency with that vocabulary; honesty (does the name promise
   more than the code does?); length/clarity per project norms.
5. Answer in Russian: verdict, precedents found (file:line), and — only if
   the current name is worse — 1-2 grounded alternatives. Don't rename
   anything until confirmed.
