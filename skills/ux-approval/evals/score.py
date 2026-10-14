#!/usr/bin/env python3
"""Run every case in cases/ and compare its output with the case's expectation.

Usage: score.py

A case is a folder cases/<name>/ with expect.json:
  {"steps": [STEP, ...], "exit": <code>, "fragments": [<text>, ...], "absent": [<text>, ...]}
STEP is one of
  [<argv>...]                              a command; a first item ending in .py runs with this Python
  {"copy": <from>, "to": <to>, "set": [[<path>, <value>], ...]}   copy a JSON file, setting values
  {"read": <path>}                         add a file's text to the output
Every path and argument may use {approval}, {template}, {skills}, {cases}, {case} and {tmp}
(a fresh temporary directory per case). Every command before the last must exit 0; the last one
must exit with `exit`. Each fragment must appear in the joined output of all steps, and no
`absent` text may. A folder without expect.json (the synthetic project) is not a case.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parent
CASES = EVALS / 'cases'
SKILL = EVALS.parent


def main():
    results = [run_case(path) for path in sorted(CASES.iterdir()) if (path / 'expect.json').is_file()]
    for name, passed, detail in results:
        print(f'{"ok" if passed else "FAIL"}  {name}' + (f' — {detail}' if not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    return 1 if failed else 0


def run_case(case_dir):
    expected = json.loads((case_dir / 'expect.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as temp:
        tokens = {'approval': str(SKILL / 'approval.py'), 'template': str(EVALS / 'stub_template.html'),
                  'skills': str(SKILL.parent), 'cases': str(CASES), 'case': str(case_dir), 'tmp': temp}
        code, output, failure = run_steps(expected['steps'], tokens)
    if failure:
        return case_dir.name, False, failure
    missing = [fragment for fragment in expected.get('fragments', []) if fragment not in output]
    present = [text for text in expected.get('absent', []) if text in output]
    passed = code == expected['exit'] and not missing and not present
    return case_dir.name, passed, f'exit {code}, missing {missing}, present {present}: ' + tail(output)


def run_steps(steps, tokens):
    outputs = []
    code = 0
    for index, step in enumerate(steps):
        if index and code != 0:
            return code, '', f'step {index} exited {code}: ' + tail('\n'.join(outputs))
        code, text = run_step(step, tokens)
        outputs.append(text)
    return code, '\n'.join(outputs), None


def run_step(step, tokens):
    if isinstance(step, list):
        return run_command([fill(part, tokens) for part in step])
    if 'read' in step:
        path = Path(fill(step['read'], tokens))
        return 0, path.read_text(encoding='utf-8') if path.is_file() else f'no such file: {path}'
    return copy_json(Path(fill(step['copy'], tokens)), Path(fill(step['to'], tokens)), step.get('set', []))


def run_command(argv):
    if argv[0].endswith('.py'):
        argv = [sys.executable] + argv
    result = subprocess.run(argv, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def copy_json(source, target, changes):
    value = json.loads(source.read_text(encoding='utf-8'))
    for path, new in changes:
        set_path(value, path, new)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0, ''


def set_path(value, path, new):
    for name in path[:-1]:
        value = value[name]
    value[path[-1]] = new


def fill(text, tokens):
    for name, replacement in tokens.items():
        text = text.replace(f'{{{name}}}', replacement)
    return text


def tail(output):
    return ' | '.join(output.strip().splitlines()[-6:])


if __name__ == '__main__':
    sys.exit(main())
