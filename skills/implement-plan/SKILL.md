---
name: implement-plan
description: Implement a plan file step by step, verify, then review the diff. Use for "имплементируй план plan/X.md", "implement the plan".
---

1. Read the plan file the user names (a folder `plan/<name>/` means its
   `plan.md`); ask for the path if none is given. If the user names a step, do
   only that step. If the user names a stage and the plan has `## Stages`, do
   only that stage's steps: refuse while a stage it depends on is not `done`,
   and set its status cell to `in progress` before editing.
2. Worktree: if the front matter sets `worktree:` and that directory does not
   exist, run `git worktree add -b <branch> <worktree> <sha from base>`, or
   `git worktree add <worktree> <branch>` when the branch already exists; then
   run `bash <this skill's base directory>/flutter_worktree_setup.sh
   <worktree>` from the repository root (it copies the files `.worktreeinclude` lists, fetches the SDK,
   packages and pods, and skips what the project lacks); then run the
   project's worktree setup script if the project rules name one. All
   code edits, lint and tests run inside the worktree; without `worktree:`,
   work in the current tree. Plain `git` only, no harness worktree tools.
   The plan and its comments live in `plan/` of the main tree — from inside a
   worktree it is the first `worktree` entry of `git worktree list --porcelain`;
   write every plan status update there, never to a copy in the worktree.
3. Before editing, verify the plan's file references still exist and compare the
   `base` sha with the worktree/branch HEAD; flag drift and divergence.
4. Implement exactly what the plan says — no scope creep.
5. With subagents (the request says «используй субагентов»; `make-plan` sends
   it too): the main session splits the steps into at most 4 chunks by change
   contract — steps editing the same files go together, a stage is one chunk —
   and spawns a fresh worker per chunk with the plan path, the chunk's step ids
   and their `verify`, demanding a reply of at most 15 lines: what changed, the
   verify result, deviations. A step with a device run longer than a few
   minutes is launched by the main session in the background with its report
   written to a file; reading the report and the fixes go to the next fresh
   worker.
6. Verify: if the project has a lint skill use it, otherwise run
   format + analyze + tests for the stack. Fix until clean. Then reread every
   comment line the diff adds and delete each one the comment rule does not allow.
7. Run the `code-reviewer` agent on the diff (listed as `<plugin>:code-reviewer`
   when installed as a plugin; if no such agent is available, do the review
   inline by the same criteria and say so), passing the plan file path and
   content — ask it to check plan compliance (every planned step implemented,
   nothing beyond plan scope) alongside its normal criteria. Fix Blocking
   findings; list the rest. When running a stage, set its status cell to `done`.
8. Report in Russian, one line each: что теперь работает, результат проверки,
   вердикт ревьюера, отклонения от плана (только если есть). End with a single
   offer to commit — never commit without confirmation.
