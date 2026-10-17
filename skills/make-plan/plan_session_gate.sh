#!/bin/bash
export LC_ALL=en_US.UTF-8
input=$(cat)
event=$(printf '%s' "$input" | jq -r '.hook_event_name // empty')
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
state_dir="/tmp/claude-plan-session"
mkdir -p "$state_dir"
make_flag="$state_dir/make-$session_id"

plan_phrase='(^|[^[:alpha:]])((создай|составь|давай составим|нужно создать|подготовь|доработай) план|(добавь|заложим) в план)([^[:alpha:]]|$)|(^|[^[:alpha:]])(с|за)планир(уй|уйте|уем|овать)([^[:alpha:]]|$)'
plan_exclusion='ревью плана|проанализируй план|имплементируй план|примени план'
slash_make_plan='^/([^[:space:]/:]+:)?make-plan([[:space:]]|$)'

reason=$(cat <<'REASON'
Never implement here. A request in this session to implement (имплементируй, примени план, внеси правки в код, запусти этап) starts a new session instead: `start_session` with `initiation` "user_asked", `context` "fresh", `cwd` = the folder that holds the plan's `plan/`, `use_worktree` false, `permission_mode` "auto", the prompt `имплементируй план <plan path>` plus the step or stage the user named, a `background` naming the plan; then report the session and stop. A refused start → an own_initiative card when that folder is this session's, otherwise the prompt and the folder for the user. Without session tools → the prompt and the folder for the user.
REASON
)

handle_prompt() {
  local prompt
  prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')
  if printf '%s\n' "$prompt" | head -n 1 | grep -qE "$slash_make_plan"; then
    touch "$make_flag"
    return
  fi
  if [[ "$prompt" == '<'* || "$prompt" == *'<agent-message '* ]]; then
    return
  fi
  if ! printf '%s\n' "$prompt" | grep -qiE "$plan_phrase"; then
    return
  fi
  if printf '%s\n' "$prompt" | grep -qiE "$plan_exclusion"; then
    return
  fi
  echo "The user asked for a plan: handle this request through the make-plan skill, not a hand-written file or the built-in plan mode"
}

handle_skill() {
  local skill
  skill=$(printf '%s' "$input" | jq -r '.tool_input.skill // empty')
  local name="${skill##*:}"
  if [ "$name" = "make-plan" ]; then
    touch "$make_flag"
    return
  fi
  if [ "$name" != "implement-plan" ] || [ ! -f "$make_flag" ]; then
    return
  fi
  jq -n --arg reason "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
}

if [ -z "$session_id" ]; then
  exit 0
fi

if [ "$event" = "UserPromptSubmit" ]; then
  handle_prompt
  exit 0
fi

if [ "$event" = "PreToolUse" ] && [ "$(printf '%s' "$input" | jq -r '.tool_name // empty')" = "Skill" ]; then
  handle_skill
fi
exit 0
