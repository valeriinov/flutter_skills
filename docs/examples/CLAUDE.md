# CLAUDE.md

@AGENTS.global.md

## Personal additions

### Rules from retrospectives

Rules proposed from retrospectives or usage reports need recurrence evidence:
2+ sessions or memories. One-off incident → no rule. Recurring but local → the
rule goes into the skill/file where it bit, not into global instructions. No
new skill for a rarely-performed operation.

### Git

- Never add a `Co-Authored-By` trailer to commit messages unless the user
  explicitly asks for it.

### Output Shape

The `i-have-adhd` plugin injects the full ruleset behind the Output Shape section of
AGENTS.global.md at SessionStart. It reaches only the main thread; subagents carry their own
output rules.

- Subagent prompts and agent-to-agent output stay caveman-compressed (`cavecrew-*`).
- No time estimates unless asked outright — this overrides the ruleset's rule 6.
- The plan file is never replayed as prose in chat after `ExitPlanMode`.

### Review Routing

- "Ревью PR #N" / "просмотри PR" / "сверь правки по PR" → the `review-pr` skill
  (branch diff + document the user pastes back as comments). `review-changes`
  stays for the working tree.
- `caveman-review` is an output format, not a review depth — use it only on an
  explicit `/caveman-review`.
- `cavecrew-reviewer` — only when explicitly asked to save context / use
  cavecrew.
- "Имплементируй план" / "сделай ревью плана" go to the same skills also when the
  request adds "ultracode".
