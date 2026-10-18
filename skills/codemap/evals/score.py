#!/usr/bin/env python3
"""Check the Dart extractor against the fixture, then run every case in cases/.

Usage: score.py

The script copies fixtures/dart_app/ to a temporary folder and writes the
`.dart_tool/package_config.json` of its one package there. The extractor case
runs the compiled extractor over that copy and compares its output with
fixtures/dart_app/expected.jsonl line by line.

A case is cases/<name>.json with a list of steps. Each case works in a fresh
copy of the fixture whose index is already built; `"root": "plain"` gives a
folder without Dart instead. `$ROOT` in a step is the path of that copy. A
step does one of:
- `hook`: a payload for `codemap.py hook` (a string goes to stdin as it is);
- `run`: the arguments of `codemap.py`;
- `write` with `content`, or `delete`: a path relative to the copy;
- `remove_index`: deletes `.codemap/`;
- `hold_lock` or `release_lock`: takes or releases the index lock, as a
  running `build` or `refresh` holds it.

A `hook` or `run` step may carry `env` and `expect`. Every fragment of
`expect` must appear in the output; a fragment written as `!<fragment>` must
not appear; `<empty>` asks for no output at all. `max_length` sets the
largest length of the output. The output of a hook is its
event name and its additional context. A step with `poll` repeats until its
expectations hold, for at most ten seconds. `file` checks a file of the copy
against `expect` instead of the output. A hook must exit 0.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EVALS = Path(__file__).resolve().parent
SKILL = EVALS.parent
SCRIPT = SKILL / 'codemap.py'
CASES = EVALS / 'cases'
FIXTURE = EVALS / 'fixtures' / 'dart_app'
POLL_SECONDS = 10
PACKAGE_CONFIG = {
    'configVersion': 2,
    'packages': [{'name': 'dart_app', 'rootUri': '../', 'packageUri': 'lib/', 'languageVersion': '3.9'}],
}

sys.dont_write_bytecode = True
sys.path.insert(0, str(SKILL))
import codemap  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as scratch:
        template = Path(scratch).resolve() / 'template'
        shutil.copytree(FIXTURE, template, ignore=shutil.ignore_patterns('.codemap', 'expected.jsonl'))
        write_package_config(template)
        run_script(['build', str(template)], {})
        results = [extractor_case(template)]
        locks = {}
        for index, path in enumerate(sorted(CASES.glob('*.json'))):
            results.append(run_case(path, template, template.parent / f'case{index}', locks))
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    sys.exit(1 if failed else 0)


def write_package_config(root):
    config = root / codemap.PACKAGE_CONFIG
    if config.exists():
        return
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps(PACKAGE_CONFIG, indent=2) + '\n')


def extractor_case(root):
    sdk = codemap.sdk_path(str(root))
    extractor = codemap.extractor_path(sdk)
    output = subprocess.run([extractor, str(root), sdk], capture_output=True, text=True, check=False).stdout
    expected = (FIXTURE / 'expected.jsonl').read_text()
    if output == expected:
        return 'extractor expected.jsonl', True, ''
    first = next(
        (index for index, (a, b) in enumerate(zip(output.splitlines(), expected.splitlines())) if a != b),
        min(len(output.splitlines()), len(expected.splitlines())),
    )
    return 'extractor expected.jsonl', False, f'first difference at line {first + 1}'


def run_case(path, template, root, locks):
    case = json.loads(path.read_text())
    if case.get('root') == 'plain':
        root.mkdir()
    else:
        shutil.copytree(template, root)
    for number, step in enumerate(case['steps'], start=1):
        failure = run_step(step, root, locks)
        if failure:
            return path.name, False, f'step {number}: {failure}'
    return path.name, True, ''


def run_step(step, root, locks):
    if 'write' in step:
        target = root / step['write']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(step['content'])
        return None
    if 'delete' in step:
        (root / step['delete']).unlink()
        return None
    if step.get('remove_index'):
        shutil.rmtree(root / '.codemap')
        return None
    if step.get('hold_lock'):
        locks[root] = codemap.open_lock(str(root))
        codemap.take_lock(locks[root], blocking=True)
        return None
    if step.get('release_lock'):
        locks.pop(root).close()
        return None
    deadline = time.time() + (POLL_SECONDS if step.get('poll') else 0)
    while True:
        output, code = step_output(step, root)
        failure = check(step, output, code)
        if failure is None or time.time() >= deadline:
            return failure
        time.sleep(0.2)


def step_output(step, root):
    if 'file' in step:
        target = root / step['file']
        return (target.read_text() if target.exists() else ''), 0
    if 'run' in step:
        return run_script([substitute(argument, root) for argument in step['run']], step.get('env', {}))
    payload = step['hook']
    stdin = payload if isinstance(payload, str) else json.dumps(substitute_all(payload, root))
    output, code = run_script(['hook'], step.get('env', {}), stdin)
    if not output:
        return '', code
    hook_output = json.loads(output)['hookSpecificOutput']
    return f'{hook_output["hookEventName"]}\n{hook_output["additionalContext"]}', code


def run_script(arguments, env, stdin=None):
    environment = {**os.environ, 'CODEMAP_AB': '', 'CODEMAP_MAP': '', **env}
    process = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        input=stdin,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    return process.stdout + process.stderr, process.returncode


def check(step, output, code):
    if 'hook' in step and code != 0:
        return f'exit {code}'
    if len(output) > step.get('max_length', len(output)):
        return f'output of {len(output)} characters'
    missing = [fragment for fragment in step.get('expect', []) if not holds(fragment, output)]
    if missing:
        return f'missing {missing}: ' + ' | '.join(output.splitlines()[:4])
    return None


def holds(fragment, output):
    if fragment == '<empty>':
        return output == ''
    if fragment.startswith('!'):
        return fragment[1:] not in output
    return fragment in output


def substitute(value, root):
    return value.replace('$ROOT', str(root))


def substitute_all(value, root):
    if isinstance(value, str):
        return substitute(value, root)
    if isinstance(value, dict):
        return {key: substitute_all(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute_all(item, root) for item in value]
    return value


if __name__ == '__main__':
    main()
