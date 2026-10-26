#!/bin/bash
# PreCompact hook: logs the compaction for the weekly retro and prints the
# handoff template. Claude Code passes stdout to the compaction as custom
# instructions.
set -euo pipefail

input=$(cat)
jq -c '{ts: (now | todate), session_id, trigger, cwd, transcript_path}' \
  <<<"$input" >>~/.claude/compact-log.jsonl || true

cat <<'EOF'
Write the summary as a handoff for an agent that continues this work. Include these sections:
1. Goal: the user's request and the success criteria.
2. Decisions: each decision with its reason, and each rejected approach.
3. Done: the changed files and what each change does.
4. Current step: the step in progress and its state.
5. Remaining: the steps that are not done, in order.
6. Verification: the checks that ran with their result, and the checks that did not run.
7. References: plan files, branches, PRs, and commands to run again.
8. User preferences and corrections from this session.
Quote the user's words when a decision depends on them.
EOF
