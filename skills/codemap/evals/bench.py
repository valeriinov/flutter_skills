#!/usr/bin/env python3
"""Run headless Claude Code sessions on a set of tasks under several variants.

Usage:
  bench.py --tasks <tasks.json> --variants <V0.json> [<V1.json> ...]
           --worktree <dir> --out <dir> --model <model> [--repeats 3]
           [--task-ids <id> ...] [--permission-mode bypassPermissions]
           [--setting-sources user,project] [--budget-usd 3] [--timeout 900]
  bench.py --report --out <dir> [--baseline V0]

Each run is one `claude -p` session in the worktree. The runner adds the task
`prompt_suffix` to the prompt and passes the variant `settings` with
`--settings`. Before the run, the runner removes the `drop_sections` headings
from their files and the `drop_hooks` entries whose command contains the given
text from their settings files. These edits change tracked files of the
worktree; the runner restores them before the verify command runs.

A task has `expect` or `verify`. `expect` is a list of groups; each group is a
list of alternative substrings, and the answer must contain one substring of
every group. `verify` is a shell command; exit code 0 means correct. After the
run, the runner restores the tracked files (`git checkout -- .`) and removes
untracked files that git does not ignore (`git clean -fd`, never `-x`). When the
run changed files, the runner then runs the `after_cleanup` commands of the
tasks file and of the variant. The worktree
must be clean before each run; a dirty worktree stops the runner.

A variant also takes `setup` (commands run once, before its first run, not
timed) and `before_run` (commands run before each run). All commands run in
the worktree. `cli_args` is a list of extra `claude` arguments, such as
`--agents` or `--append-system-prompt`, that leave the worktree unchanged.
`extra_cost_log` is the path of a JSON lines file with a `cost` field per line,
such as the `JEV_COST_LOG` of a hook. The runner empties the file before each
run and writes the sum of `cost` to the run as `jev_cost_usd` and the line
count as `jev_calls`; without the field, both are null and the `jev $` column
stays empty.

Each run appends one line to `<out>/runs.jsonl`; a run already in that file is
skipped, so a stopped benchmark resumes. The raw stream of each run is in
`<out>/raw/`. `results.md` is written after every run.

Weighted tokens = input + cache_write + output + 0.1 * cache_read, summed over
every model of the session (`modelUsage`, subagents included). The winner is
the variant with the lowest median weighted tokens among the variants whose
correct share is not below the baseline variant; a tie goes to fewer turns.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

RUNS_FILE = "runs.jsonl"
RESULTS_FILE = "results.md"
RAW_DIR = "raw"
CACHE_READ_WEIGHT = 0.1


def main():
    args = parse_args()
    if args.report:
        write_results(args.out, args.baseline)
        return
    tasks_file = load_json(args.tasks)
    variants = [load_json(path) for path in args.variants]
    tasks = selected_tasks(tasks_file["tasks"], args.task_ids)
    os.makedirs(os.path.join(args.out, RAW_DIR), exist_ok=True)
    done = recorded_keys(args.out)
    prepared = set()
    for repeat in range(1, args.repeats + 1):
        for task in tasks:
            for variant in variants:
                key = run_key(task["id"], variant["name"], repeat)
                if key in done:
                    continue
                if variant["name"] not in prepared:
                    run_commands(variant.get("setup", []), args.worktree)
                    prepared.add(variant["name"])
                record = run_once(args, tasks_file, task, variant, repeat)
                append_record(args.out, record)
                write_results(args.out, args.baseline)
                print(summary_line(record), flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tasks")
    parser.add_argument("--variants", nargs="+", default=[])
    parser.add_argument("--worktree")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--task-ids", nargs="+")
    parser.add_argument("--permission-mode", default="bypassPermissions")
    parser.add_argument("--setting-sources", default="user,project")
    parser.add_argument("--budget-usd", type=float, default=3.0)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--baseline", default="V0")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if not args.report:
        missing = [name for name in ("tasks", "worktree", "model") if not getattr(args, name)]
        if missing or not args.variants:
            parser.error("--tasks, --variants, --worktree and --model are required")
        args.worktree = os.path.abspath(args.worktree)
    args.out = os.path.abspath(args.out)
    return args


def load_json(path):
    with open(path) as file:
        return json.load(file)


def selected_tasks(tasks, task_ids):
    if not task_ids:
        return tasks
    return [task for task in tasks if task["id"] in task_ids]


def run_key(task_id, variant_name, repeat):
    return f"{task_id}|{variant_name}|{repeat}"


def recorded_keys(out):
    return {run_key(r["task"], r["variant"], r["repeat"]) for r in read_records(out)}


def read_records(out):
    path = os.path.join(out, RUNS_FILE)
    if not os.path.isfile(path):
        return []
    with open(path) as file:
        return [json.loads(line) for line in file if line.strip()]


def run_once(args, tasks_file, task, variant, repeat):
    worktree = args.worktree
    require_clean(worktree)
    edited = apply_variant_edits(variant, worktree)
    run_commands(variant.get("before_run", []), worktree)
    raw_path = os.path.join(
        args.out, RAW_DIR, f"{task['id']}__{variant['name']}__{repeat}.jsonl"
    )
    prompt = f"{task['prompt']}\n\n{tasks_file.get('prompt_suffix', '')}".strip()
    cost_log = variant.get("extra_cost_log")
    if cost_log:
        open(os.path.expanduser(cost_log), "w").close()
    started = time.time()
    timed_out = run_claude(args, variant, prompt, raw_path)
    wall_seconds = round(time.time() - started, 1)
    restore_files(edited, worktree)
    events = read_events(raw_path)
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    answer = str(result.get("result") or "")
    correct, verify_code = judge(task, answer, worktree)
    changed = bool(git(worktree, "status", "--porcelain", "--untracked-files=all").strip())
    cleanup(worktree)
    if changed:
        run_commands(tasks_file.get("after_cleanup", []), worktree)
        run_commands(variant.get("after_cleanup", []), worktree)
    require_clean(worktree)
    return {
        "task": task["id"],
        "kind": task.get("kind"),
        "variant": variant["name"],
        "repeat": repeat,
        "model": args.model,
        "correct": correct,
        "verify_exit": verify_code,
        "timed_out": timed_out,
        "is_error": bool(result.get("is_error", not result)),
        "subtype": result.get("subtype"),
        "num_turns": result.get("num_turns"),
        "wall_seconds": wall_seconds,
        "duration_ms": result.get("duration_ms"),
        "total_cost_usd": result.get("total_cost_usd"),
        "jev_cost_usd": extra_cost(cost_log),
        "jev_calls": len(extra_cost_lines(cost_log)) if cost_log else None,
        "usage": usage_of(result.get("usage") or {}),
        "model_usage": model_usage_sum(result.get("modelUsage") or {}),
        "models": sorted((result.get("modelUsage") or {}).keys()),
        "weighted_tokens": weighted(model_usage_sum(result.get("modelUsage") or {})),
        "permission_denials": len(result.get("permission_denials") or []),
        "hooks": hook_summary(events),
        "tool_uses": tool_use_count(events),
        "answer": answer[:2000],
    }


def extra_cost(cost_log):
    if not cost_log:
        return None
    return sum(line.get("cost") or 0 for line in extra_cost_lines(cost_log))


def extra_cost_lines(cost_log):
    path = os.path.expanduser(cost_log)
    if not os.path.exists(path):
        return []
    with open(path) as file:
        return [json.loads(line) for line in file if line.strip()]


def require_clean(worktree):
    status = git(worktree, "status", "--porcelain", "--untracked-files=all")
    if status.strip():
        sys.exit(f"worktree is not clean:\n{status}")


def apply_variant_edits(variant, worktree):
    edited = set()
    for edit in variant.get("drop_sections", []):
        drop_section(os.path.join(worktree, edit["file"]), edit["heading"])
        edited.add(edit["file"])
    for edit in variant.get("drop_hooks", []):
        drop_hooks(os.path.join(worktree, edit["file"]), edit["command_contains"])
        edited.add(edit["file"])
    return sorted(edited)


def drop_section(path, heading):
    with open(path) as file:
        lines = file.read().split("\n")
    level = heading.split(" ", 1)[0]
    start = lines.index(heading)
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if is_heading_at_or_above(lines[index], level)
        ),
        len(lines),
    )
    with open(path, "w") as file:
        file.write("\n".join(lines[:start] + lines[end:]))


def is_heading_at_or_above(line, level):
    marks = line.split(" ", 1)[0]
    return set(marks) == {"#"} and len(marks) <= len(level) and " " in line


def drop_hooks(path, text):
    settings = load_json(path)
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        groups = []
        for group in hooks[event]:
            kept = [hook for hook in group.get("hooks", []) if text not in hook.get("command", "")]
            if kept:
                groups.append({**group, "hooks": kept})
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]
    with open(path, "w") as file:
        json.dump(settings, file, indent=2)
        file.write("\n")


def run_commands(commands, worktree):
    for command in commands:
        completed = subprocess.run(command, shell=True, cwd=worktree, check=False)
        if completed.returncode != 0:
            sys.exit(f"command failed ({completed.returncode}): {command}")


def run_claude(args, variant, prompt, raw_path):
    command = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-hook-events",
        "--no-session-persistence",
        "--setting-sources",
        args.setting_sources,
        "--settings",
        json.dumps(variant.get("settings", {})),
        "--model",
        args.model,
        "--permission-mode",
        args.permission_mode,
        "--max-budget-usd",
        str(args.budget_usd),
        *variant.get("cli_args", []),
    ]
    with open(raw_path, "w") as raw:
        try:
            subprocess.run(
                command,
                cwd=args.worktree,
                stdin=subprocess.DEVNULL,
                stdout=raw,
                stderr=subprocess.STDOUT,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return True
    return False


def restore_files(paths, worktree):
    if paths:
        git(worktree, "checkout", "--", *paths)


def read_events(path):
    events = []
    with open(path) as file:
        for line in file:
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    return events


def judge(task, answer, worktree):
    if "verify" in task:
        code = subprocess.run(task["verify"], shell=True, cwd=worktree, check=False).returncode
        return code == 0, code
    return all(any(item in answer for item in group) for group in task["expect"]), None


def cleanup(worktree):
    git(worktree, "checkout", "--", ".")
    git(worktree, "clean", "-fd")


def git(worktree, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=worktree, capture_output=True, text=True, check=True
    ).stdout


def usage_of(usage):
    return {
        "input": usage.get("input_tokens", 0),
        "cache_read": usage.get("cache_read_input_tokens", 0),
        "cache_write": usage.get("cache_creation_input_tokens", 0),
        "output": usage.get("output_tokens", 0),
    }


def model_usage_sum(model_usage):
    total = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    for usage in model_usage.values():
        total["input"] += usage.get("inputTokens", 0)
        total["cache_read"] += usage.get("cacheReadInputTokens", 0)
        total["cache_write"] += usage.get("cacheCreationInputTokens", 0)
        total["output"] += usage.get("outputTokens", 0)
    return total


def weighted(usage):
    return round(
        usage["input"]
        + usage["cache_write"]
        + usage["output"]
        + CACHE_READ_WEIGHT * usage["cache_read"]
    )


def hook_summary(events):
    summary = {}
    for event in events:
        if event.get("type") != "system" or event.get("subtype") != "hook_response":
            continue
        name = f"{event.get('hook_event', '?')}:{event.get('hook_name', '?')}"
        entry = summary.setdefault(name, {"count": 0, "context_chars": 0})
        entry["count"] += 1
        entry["context_chars"] += len(hook_context(event))
    return summary


def hook_context(event):
    output = str(event.get("output") or event.get("stdout") or "")
    try:
        parsed = json.loads(output)
    except ValueError:
        return output
    if not isinstance(parsed, dict):
        return output
    return str((parsed.get("hookSpecificOutput") or {}).get("additionalContext") or "")


def tool_use_count(events):
    count = 0
    for event in events:
        if event.get("type") != "assistant":
            continue
        content = (event.get("message") or {}).get("content") or []
        count += sum(1 for block in content if block.get("type") == "tool_use")
    return count


def append_record(out, record):
    with open(os.path.join(out, RUNS_FILE), "a") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def summary_line(record):
    return (
        f"{record['task']} {record['variant']} r{record['repeat']}: "
        f"correct={record['correct']} weighted={record['weighted_tokens']} "
        f"turns={record['num_turns']} wall={record['wall_seconds']}s "
        f"cost={record['total_cost_usd']}"
    )


def write_results(out, baseline):
    records = read_records(out)
    if not records:
        return
    rows = variant_rows(records)
    lines = [
        "# Benchmark results",
        "",
        f"Runs: {len(records)}. Models: {', '.join(sorted({r['model'] for r in records}))}.",
        "",
        "Weighted tokens = input + cache_write + output + 0.1 × cache_read, summed over",
        "every model of the session (`modelUsage`, subagents included).",
        "",
        "| variant | runs | correct | weighted (median) | input | cache read | cache write | output | turns | wall s | cost $ | jev $ |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {row['runs']} | {row['correct']:.0%} | {row['weighted']:.0f} "
            f"| {row['input']:.0f} | {row['cache_read']:.0f} | {row['cache_write']:.0f} "
            f"| {row['output']:.0f} | {row['turns']:.1f} | {row['wall']:.1f} | {row['cost']:.3f} | {row['jev']} |"
        )
    lines += ["", winner_line(rows, baseline), "", "## Weighted tokens per task (median)", ""]
    lines += task_table(records, [row["variant"] for row in rows])
    with open(os.path.join(out, RESULTS_FILE), "w") as file:
        file.write("\n".join(lines) + "\n")


def variant_rows(records):
    rows = []
    for variant in sorted({r["variant"] for r in records}):
        runs = [r for r in records if r["variant"] == variant]
        rows.append(
            {
                "variant": variant,
                "runs": len(runs),
                "correct": sum(1 for r in runs if r["correct"]) / len(runs),
                "weighted": median(r["weighted_tokens"] for r in runs),
                "input": median(r["model_usage"]["input"] for r in runs),
                "cache_read": median(r["model_usage"]["cache_read"] for r in runs),
                "cache_write": median(r["model_usage"]["cache_write"] for r in runs),
                "output": median(r["model_usage"]["output"] for r in runs),
                "turns": median(r["num_turns"] or 0 for r in runs),
                "wall": median(r["wall_seconds"] for r in runs),
                "cost": median(r["total_cost_usd"] or 0 for r in runs),
                "jev": jev_cell(runs),
            }
        )
    return rows


def jev_cell(runs):
    costs = [r["jev_cost_usd"] for r in runs if r.get("jev_cost_usd") is not None]
    return f"{median(costs):.5f}" if costs else ""


def median(values):
    return statistics.median(list(values))


def winner_line(rows, baseline):
    base = next((row for row in rows if row["variant"] == baseline), None)
    if base is None:
        return f"Winner: none — the baseline {baseline} has no runs."
    eligible = [row for row in rows if row["correct"] >= base["correct"]]
    best = min(eligible, key=lambda row: (row["weighted"], row["turns"]))
    return (
        f"Winner: **{best['variant']}** — the lowest median weighted tokens among the "
        f"variants whose correct share is at least {baseline} ({base['correct']:.0%}); "
        "a tie goes to fewer turns."
    )


def task_table(records, variants):
    lines = [
        "| task | " + " | ".join(variants) + " |",
        "|---|" + "---|" * len(variants),
    ]
    for task in sorted({r["task"] for r in records}):
        cells = []
        for variant in variants:
            runs = [r for r in records if r["task"] == task and r["variant"] == variant]
            if not runs:
                cells.append("—")
                continue
            correct = sum(1 for r in runs if r["correct"])
            cells.append(f"{median(r['weighted_tokens'] for r in runs):.0f} ({correct}/{len(runs)})")
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    return lines


if __name__ == "__main__":
    main()
