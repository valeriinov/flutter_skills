#!/bin/bash
input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id')
state_dir="/tmp/claude-edit-confirm"
mkdir -p "$state_dir"
mode_file="$state_dir/mode-$session_id"
context=$(printf 'EDIT-CONFIRM SETUP: before your first Edit/Write/MultiEdit/NotebookEdit tool call this session, ask the user via AskUserQuestion to choose between "Confirm every edit" (every edit this session prompts for approval, no exceptions) and "Full auto" (edits run silently from the start, no prompts). Write the user'\''s literal choice, the single word confirm or auto, into the file %s (e.g. run: echo confirm > %s). If you skip asking, the default (missing file) behaves as confirm - every edit prompts. IMPORTANT: approving a single edit prompt (clicking yes/allow on one Edit call) never switches the session to auto by itself - a hook cannot see which button was pressed, only whether the edit ran. The ONLY way to switch this session to silent full-auto mode is an explicit, deliberate chat request from the user asking to stop asking about edits for the rest of the session (in any language). Only on such an explicit request, write auto into %s yourself via Bash.' "$mode_file" "$mode_file" "$mode_file")
jq -n --arg ctx "$context" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
