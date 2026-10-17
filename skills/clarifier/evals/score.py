#!/usr/bin/env python3
"""Run clarify.py check on every case in cases/ and compare the output with the case's expectation.

Usage: score.py

A case is <lang>-<name>.md whose first line is <!-- expect: <fragment>; <fragment> -->.
Every fragment must appear in the output. A fragment written as !<fragment> must not appear.
The run must exit 2 when one fragment is `usage`. It must exit 0 when one fragment is `ok`, and 1 otherwise.
A <lang>-<name>.source.md next to the case is passed as --source.
A <lang>-<name>.json case is a visualize document and expects `ok`.
A <lang>-<name>.dart case runs with --dart and starts with // expect: <fragment>; <fragment>.
A <lang>-<name>.dart folder runs with --dart as one path; its main.dart holds the expect line.
A name with -instructions runs with --instructions. A --dart or --instructions case gets
--words fixtures/ste-words.json when its name has -words.
Any other such case gets fixtures/no-words.json, a path that must not exist.
A name with -unlisted adds --unlisted.
"""

import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import clarify  # noqa: E402

CASES = Path(__file__).resolve().parent / 'cases'
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
EXPECT_RE = re.compile(r'^(?:<!-- expect: (.+) -->|// expect: (.+))$')


def main():
    results = [run_case(path) for path in sorted(CASES.iterdir()) if is_case(path)]
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    sys.exit(1 if failed else 0)


def is_case(path):
    return path.suffix in ('.md', '.json', '.dart') and not path.name.endswith('.source.md')


def run_case(path):
    argv = ['check', str(path)]
    expected = ['ok']
    if path.suffix in ('.md', '.dart'):
        argv += ['--lang', path.name.split('-')[0]] + mode_options(path)
        expected = expectations(path)
    source = path.with_name(f'{path.stem}.source.md')
    if source.exists():
        argv += ['--source', str(source)]
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = clarify.main(argv)
    lines = output.getvalue().splitlines()
    missing = [fragment for fragment in expected if is_missing(fragment, lines)]
    expected_code = expected_exit_code(expected)
    passed = not missing and code == expected_code
    return path.name, passed, f'exit {code}, missing {missing}: ' + ' | '.join(lines[:4])


def mode_options(path):
    options = ['--dart'] if path.suffix == '.dart' else []
    if '-instructions' in path.stem:
        options.append('--instructions')
    if not options:
        return []
    if '-unlisted' in path.stem:
        options.append('--unlisted')
    words = FIXTURES / ('ste-words.json' if '-words' in path.stem else 'no-words.json')
    return options + ['--words', str(words)]


def is_missing(fragment, lines):
    if fragment.startswith('!'):
        return any(fragment[1:] in line for line in lines)
    return not any(fragment in line for line in lines)


def expected_exit_code(expected):
    if 'usage' in expected:
        return 2
    return 0 if 'ok' in expected else 1


def expectations(path):
    case = path / 'main.dart' if path.is_dir() else path
    match = EXPECT_RE.match(case.read_text(encoding='utf-8').split('\n', 1)[0])
    if not match:
        return ['<!-- expect: … --> header']
    return [fragment.strip() for fragment in (match.group(1) or match.group(2)).split(';')]


if __name__ == '__main__':
    main()
