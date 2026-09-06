#!/bin/bash
input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id')
state_dir="/tmp/claude-edit-confirm"
mkdir -p "$state_dir"
mode_file="$state_dir/mode-$session_id"

mode="confirm"
[ -f "$mode_file" ] && mode=$(cat "$mode_file")

if [ "$mode" = "auto" ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"session edit-mode: full auto (explicitly enabled this session)"}}'
  exit 0
fi

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"edit-mode is confirm - prompts every edit until explicitly switched to full auto this session"}}'
