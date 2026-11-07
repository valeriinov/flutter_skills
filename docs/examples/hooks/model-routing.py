#!/usr/bin/env python3
"""PreToolUse hook for Agent: set `model` of a routed role from `~/.claude/model-routing.json`.

The role comes from the last skill in the transcript, the agent type and the description.
A skill the agent loads inside a routed run (`lint`, `drive-device`) keeps the run's skill;
a slash command of the user starts a new run.
A call outside the routed roles, `inherit`, or any read error leaves the input as it is.
"""
import json
import re
import sys
from pathlib import Path

ROUTING = Path.home() / ".claude" / "model-routing.json"
SCOUT_SKILLS = {"make-plan", "backend-contract"}
RUN_SKILLS = SCOUT_SKILLS | {"implement-plan", "review-changes"}
SLASH_SKILL = re.compile(r"<command-name>/(?:[^<\s/:]+:)?([^<\s/:]+)</command-name>")


def main():
    hook_input = json.load(sys.stdin)
    tool_input = hook_input.get("tool_input") or {}
    skill = last_skill(Path(hook_input.get("transcript_path") or ""))
    role = role_of(skill, tool_input.get("subagent_type") or "general-purpose", tool_input.get("description") or "")
    if role is None:
        return
    model = json.loads(ROUTING.read_text()).get(role, {}).get("model")
    if model in (None, "inherit"):
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {**tool_input, "model": model},
        }
    }))


def last_skill(transcript):
    skill = None
    with transcript.open() as lines:
        for raw in lines:
            if '"Skill"' in raw or "<command-name>/" in raw:
                skill = skill_in(json.loads(raw), skill)
    return skill


def skill_in(line, skill):
    content = line.get("message", {}).get("content")
    if isinstance(content, str):
        match = SLASH_SKILL.search(content)
        return match.group(1) if match and line.get("type") == "user" else skill
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            loaded = (block.get("input") or {}).get("skill", "").split(":")[-1]
            skill = loaded if loaded and not is_nested(skill, loaded) else skill
        if block.get("type") == "text" and line.get("type") == "user":
            match = SLASH_SKILL.search(block.get("text", ""))
            skill = match.group(1) if match else skill
    return skill


def is_nested(run_skill, loaded):
    return run_skill in RUN_SKILLS and loaded not in RUN_SKILLS


def role_of(skill, agent_type, description):
    if agent_type == "Explore" and skill in SCOUT_SKILLS and description.startswith("Scout"):
        return "scout"
    if agent_type != "general-purpose":
        return None
    if skill == "review-changes":
        return "fix-worker"
    if skill != "implement-plan":
        return None
    if description.startswith("Fix"):
        return "fix-worker"
    return "implement-worker"


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError):
        pass
