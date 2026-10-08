#!/usr/bin/env python3
"""Run the make-plan gate on eval cases, or score a plan produced by a real make-plan run.

Usage:
  score.py                                  run every case in cases/
  score.py <plan.md> <expect.json> [--root <dir>]   score one plan

The gate is what SKILL.md step 5 runs: `plan_tool.py check` on plan.md, then, when brief.json
lies beside it, `clarify.py check <brief.json> --source <plan.md>` with every `hint:` line dropped.

A case is a folder cases/<name>/ with plan.md, an optional brief.json and expect.txt. The case
folder is the root for Files paths; it is checked in a temporary copy with a `.git` marker, so
citations are checked as in a repository. expect.txt holds `;`-separated fragments, each of which must
appear in the gate output; `ok` means the gate must be clean.

One plan: the gate must be clean, with root = `--root` or the plan's git toplevel.
expect.json keys, all optional:
  steps            [min, max] number of plan steps
  sections         [min, max] number of brief sections
  files            paths each present in the Files table
  questions_min    minimum number of brief questions
  lane             the front matter lane
  text             strings each found in plan.md

Behaviour fixture: copy fixtures/<name>/repo/ to a temp dir, `git init` and commit it, put
fixtures/<name>/inputs/ at plan/<name>/inputs/ there, run make-plan, then
`score.py plan/<name>/plan.md fixtures/<name>/expect.json`.
cases/ok/expect.json scores the ok case in this mode:
`score.py cases/ok/plan.md cases/ok/expect.json --root cases/ok`.
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(SKILL.parent / 'clarifier'))
import clarify  # noqa: E402
import plan_tool  # noqa: E402

CASES = Path(__file__).resolve().parent / 'cases'


def main(argv):
    if argv:
        results = plan_results(argv)
    else:
        results = [run_case(path) for path in sorted(CASES.iterdir()) if path.is_dir()]
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if detail and not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    return 1 if failed else 0


def gate(plan_path, root):
    lines = [f'{path}:{ln}: {msg}' for path, ln, msg in plan_tool.check_plan(plan_path, root)]
    _, _, brief_path = plan_tool.output_paths(plan_path)
    if not brief_path.exists():
        return lines
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = clarify.main(['check', str(brief_path), '--source', str(plan_path)])
    if code == 0:
        return lines
    return lines + [line for line in output.getvalue().splitlines() if not is_dropped(line)]


def is_dropped(line):
    return ': hint: ' in line


def run_case(case_dir):
    expected = expectations(case_dir / 'expect.txt')
    lines = repository_gate(case_dir)
    if 'ok' in expected:
        return case_dir.name, not lines, ' | '.join(lines[:4])
    missing = [fragment for fragment in expected if not any(fragment in line for line in lines)]
    return case_dir.name, bool(lines) and not missing, f'missing {missing}: ' + ' | '.join(lines[:4])


def repository_gate(case_dir):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / case_dir.name
        shutil.copytree(case_dir, root)
        (root / '.git').mkdir(exist_ok=True)
        return gate(root / 'plan.md', root)


def expectations(path):
    if not path.exists():
        return ['expect.txt']
    return [fragment.strip() for fragment in path.read_text(encoding='utf-8').split(';') if fragment.strip()]


def plan_results(argv):
    plan_path = Path(argv[0])
    expect = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    root_arg = argv[argv.index('--root') + 1] if '--root' in argv else None
    lines = gate(plan_path, plan_tool.resolve_root(plan_path, root_arg))
    results = [('gate passes', not lines, ' | '.join(lines[:3]))]
    return results + expectation_results(plan_path, expect)


def expectation_results(plan_path, expect):
    text = plan_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    front_matter, _, _ = plan_tool.parse_front_matter(lines)
    uf = plan_tool.unfenced(lines)
    brief = load_brief(plan_path)
    results = []
    results += range_result('steps', len(plan_tool.find_steps(uf)), expect)
    results += range_result('sections', len(brief.get('sections', [])), expect)
    files = table_paths(uf)
    results += [(f'files: {path}', path in files, '') for path in expect.get('files', [])]
    if 'questions_min' in expect:
        count = len(brief.get('questions', []))
        results.append((f'≥{expect["questions_min"]} open questions', count >= expect['questions_min'], f'{count}'))
    if 'lane' in expect:
        lane = front_matter.get('lane')
        results.append((f'lane: {expect["lane"]}', lane == expect['lane'], f'{lane}'))
    results += [(f'text: {fragment}', fragment in text, '') for fragment in expect.get('text', [])]
    return results


def range_result(key, count, expect):
    if key not in expect:
        return []
    low, high = expect[key]
    return [(f'{low}–{high} {key}', low <= count <= high, f'{count} {key}')]


def load_brief(plan_path):
    _, _, brief_path = plan_tool.output_paths(plan_path)
    if not brief_path.exists():
        return {}
    return json.loads(brief_path.read_text(encoding='utf-8'))


def table_paths(uf):
    return [match.group(1)
            for _, rows in plan_tool.find_tables(uf, ['path', 'change'])
            for _, cells in rows if cells
            for match in plan_tool.BACKTICK_RE.finditer(cells[0])]


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
