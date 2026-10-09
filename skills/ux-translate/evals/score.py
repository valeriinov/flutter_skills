#!/usr/bin/env python3
"""Run check_drafts.py on every case in cases/ and compare the run with the case's expectation.

Usage: score.py

A case is <name>.jsonl. Its first line is the expectation and the arguments:
  {"expect": {"exit": <code>, "lines": [<fragment>, ...]}, "lang": <code>, "ratio": "<min>,<max>"}
`ratio` is optional. The remaining lines are the ledger. The run must exit with `exit`, print
exactly as many lines as `lines` holds, and each fragment must appear in one of them; an empty
`lines` means a silent run.
fixture/ is a training project for a trial run of the skill, not a case.
"""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_drafts  # noqa: E402

CASES = Path(__file__).resolve().parent / 'cases'


def main():
    results = [run_case(path) for path in sorted(CASES.glob('*.jsonl'))]
    for name, passed, detail in results:
        print(f'{"ok" if passed else "FAIL"}  {name}' + (f' — {detail}' if not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    return 1 if failed else 0


def run_case(path):
    header, _, ledger = path.read_text(encoding='utf-8').partition('\n')
    case = json.loads(header)
    expected = case['expect']
    with tempfile.TemporaryDirectory() as temp:
        ledger_path = Path(temp) / path.name
        ledger_path.write_text(ledger, encoding='utf-8')
        argv = [str(ledger_path), '--lang', case['lang']]
        if 'ratio' in case:
            argv += ['--ratio', case['ratio']]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = check_drafts.main(argv)
    lines = output.getvalue().splitlines()
    fragments = expected['lines']
    missing = [fragment for fragment in fragments if not any(fragment in line for line in lines)]
    passed = code == expected['exit'] and not missing and len(lines) == len(fragments)
    return path.name, passed, f'exit {code}, missing {missing}: ' + ' | '.join(lines[:4])


if __name__ == '__main__':
    sys.exit(main())
