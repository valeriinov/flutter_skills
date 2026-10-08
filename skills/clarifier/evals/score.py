#!/usr/bin/env python3
"""Run clarify.py check on every case in cases/ and compare the output with the case's expectation.

Usage: score.py

A case is <lang>-<name>.md whose first line is <!-- expect: <fragment>; <fragment> -->. Every fragment
must appear in the output; the run must exit 2 when one fragment is `usage`, 0 when one is `ok`
and 1 otherwise.
A <lang>-<name>.source.md next to the case is passed as --source.
A <lang>-<name>.json case is a visualize document and expects `ok`.
"""

import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import clarify  # noqa: E402

CASES = Path(__file__).resolve().parent / 'cases'
EXPECT_RE = re.compile(r'^<!-- expect: (.+) -->')


def main():
    results = [run_case(path) for path in sorted(CASES.iterdir()) if is_case(path)]
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    sys.exit(1 if failed else 0)


def is_case(path):
    return path.suffix in ('.md', '.json') and not path.name.endswith('.source.md')


def run_case(path):
    argv = ['check', str(path)]
    expected = ['ok']
    if path.suffix == '.md':
        argv += ['--lang', path.name.split('-')[0]]
        expected = expectations(path)
    source = path.with_name(f'{path.stem}.source.md')
    if source.exists():
        argv += ['--source', str(source)]
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = clarify.main(argv)
    lines = output.getvalue().splitlines()
    missing = [fragment for fragment in expected if not any(fragment in line for line in lines)]
    expected_code = expected_exit_code(expected)
    passed = not missing and code == expected_code
    return path.name, passed, f'exit {code}, missing {missing}: ' + ' | '.join(lines[:4])


def expected_exit_code(expected):
    if 'usage' in expected:
        return 2
    return 0 if 'ok' in expected else 1


def expectations(path):
    match = EXPECT_RE.match(path.read_text(encoding='utf-8').split('\n', 1)[0])
    if not match:
        return ['<!-- expect: … --> header']
    return [fragment.strip() for fragment in match.group(1).split(';')]


if __name__ == '__main__':
    main()
