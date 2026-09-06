---
name: naming
description: Check whether a name (field, method, class, key) fits project vocabulary and states what the code does. Use for "удачное ли имя", "консистентность нейминга", "is this a good name".
---

For the symbol the user names — `file:line` or a bare symbol name; ask which one if none is given:
1. If the project AGENTS.md has a "Naming Conventions" section — read it
   first and check the name against it.
2. Read the declaration and its usages.
3. Grep the project for neighbouring patterns (same layer, same suffix/prefix
   family) — collect the actual vocabulary in use.
4. Judge: consistency with that vocabulary; honesty (does the name promise
   more than the code does?); length/clarity per project norms.
5. Answer in Russian: verdict, precedents found (file:line), and — only if
   the current name is worse — 1-2 grounded alternatives. Don't rename
   anything until confirmed.
