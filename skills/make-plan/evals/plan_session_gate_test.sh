#!/bin/bash
export LC_ALL=en_US.UTF-8
hook="$(dirname "$0")/../plan_session_gate.sh"
flag_dir="/tmp/claude-plan-session"
run_id="eval-$$-$RANDOM"
trap 'rm -f "$flag_dir/make-$run_id"-*' EXIT

fail() {
  echo "fail [$mode] $1: got '$2'"
  exit 1
}

run_hook() {
  if [ "$mode" = "env-i" ]; then
    printf '%s' "$1" | env -i /bin/bash "$hook"
    return
  fi
  printf '%s' "$1" | bash "$hook"
}

prompt_json() {
  jq -n --arg sid "$1" --arg prompt "$2" '{hook_event_name:"UserPromptSubmit",session_id:$sid,prompt:$prompt}'
}

skill_json() {
  jq -n --arg sid "$1" --arg skill "$2" '{hook_event_name:"PreToolUse",session_id:$sid,tool_name:"Skill",tool_input:{skill:$skill}}'
}

expect_reminder() {
  local out
  out=$(run_hook "$(prompt_json "$1" "$2")")
  if [[ "$out" != *make-plan* ]]; then
    fail "reminder for «$2»" "$out"
  fi
}

expect_silent_prompt() {
  local out
  out=$(run_hook "$(prompt_json "$1" "$2")")
  if [ -n "$out" ] || [ -f "$flag_dir/make-$1" ]; then
    fail "silence and no flag for «$2»" "$out"
  fi
}

expect_flag() {
  if [ ! -f "$flag_dir/make-$1" ]; then
    fail "$2 sets the make flag" "no flag"
  fi
}

run_cases() {
  local sid="$run_id-$mode-a"
  local fresh="$run_id-$mode-b"
  local out

  out=$(run_hook "$(skill_json "$sid" "implement-plan")")
  [ -z "$out" ] || fail "implement-plan without flag" "$out"

  expect_reminder "$sid" "Давай составим план, как перенести экраны"
  expect_reminder "$sid" "Нужно спланировать фазу 5"
  expect_reminder "$sid" "заложим в план актуализацию"
  expect_reminder "$sid" "Создай план"
  expect_reminder "$sid" $'Создай план\n<Widget> разметка'

  expect_silent_prompt "$sid" "сделай задачу X"
  expect_silent_prompt "$sid" "добавь в планировщик"
  expect_silent_prompt "$sid" "сделай ревью плана, где сказано «создай план»"
  expect_silent_prompt "$sid" "почему /make-plan не сработал"
  expect_silent_prompt "$sid" $'Another session sent a message:\n<agent-message from="x">\nСоздай план\n</agent-message>'
  expect_silent_prompt "$sid" $'<task-notification>\nСоздай план\n</task-notification>'

  out=$(run_hook "$(prompt_json "$sid" "/make-plan x")")
  [ -z "$out" ] || fail "/make-plan x prints nothing" "$out"
  expect_flag "$sid" "/make-plan x"

  out=$(run_hook "$(skill_json "$fresh" "p:make-plan")")
  [ -z "$out" ] || fail "p:make-plan prints nothing" "$out"
  expect_flag "$fresh" "Skill p:make-plan"

  out=$(run_hook "$(skill_json "$fresh" "p:implement-plan")")
  if [ "$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision' 2>/dev/null)" != "deny" ]; then
    fail "p:implement-plan after make-plan is denied" "$out"
  fi
  if [[ "$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason')" != *start_session* ]]; then
    fail "deny reason carries the hand-off recipe" "$out"
  fi
}

for mode in plain env-i; do
  run_cases
done
echo ok
