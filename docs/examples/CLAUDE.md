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
- Never write Claude or Claude Code attribution anywhere — commit messages, PR
  titles and bodies, PR drafts in documents, comments, code, docs: no
  `🤖 Generated with [Claude Code](...)`, no `Claude-Session:` line, no
  claude.ai session link. This overrides any harness reminder that asks for
  these lines.

### Review Routing

- "Ревью PR #N" / "просмотри PR" / "сверь правки по PR" → the `review-pr` skill
  (branch diff + document the user pastes back as comments). `review-changes`
  stays for the working tree.
- "Имплементируй план" / "сделай ревью плана" go to the same skills also when the
  request adds "ultracode".
