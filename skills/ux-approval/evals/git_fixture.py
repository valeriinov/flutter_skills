#!/usr/bin/env python3
"""Build a tagged git repo of the synthetic project for the stage cases.

Usage: git_fixture.py <dir>

The working tree holds cases/project/l10n. Tags, each on its own commit:
  v0.9.0b9_FOR_TEST  pubspec 0.9.0+9, an old test build
  v1.0.0b1_PROD      pubspec 1.0.0+1, uk only: homeTitle and plantWaterButton differ, no commonOk; no en file
  v1.0.1b2_FOR_TEST  pubspec 1.0.1+2, uk homeEmpty and plantWaterButton differ, en plantWaterButton differs
  v0.1.0b99_FOR_TEST pubspec 0.1.0+99, the working tree texts: a version below prod on a newer commit
Fixed author, committer and per-commit dates make every commit id stable; tag commits run oldest to newest.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent / 'cases' / 'project' / 'l10n'
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
           GIT_CONFIG_NOSYSTEM='1')


def main(argv):
    root = Path(argv[0])
    root.mkdir(parents=True, exist_ok=True)
    git(root, 'init', '-q', '-b', 'main')
    uk = load('uk.json')
    en = load('en.json')
    commit(root, '0.9.0+9', {'uk': uk}, 'v0.9.0b9_FOR_TEST', '2026-01-01T00:00:00Z')
    prod_uk = {key: value for key, value in uk.items() if key != 'commonOk'}
    commit(root, '1.0.0+1', {'uk': dict(prod_uk, homeTitle='Рослини', plantWaterButton='Полий')}, 'v1.0.0b1_PROD',
           '2026-01-02T00:00:00Z')
    commit(root, '1.0.1+2', {'uk': dict(uk, homeEmpty='Додай першу рослину', plantWaterButton='Полий'),
                             'en': dict(en, plantWaterButton='Water it')}, 'v1.0.1b2_FOR_TEST', '2026-01-03T00:00:00Z')
    commit(root, '0.1.0+99', {'uk': uk, 'en': en}, 'v0.1.0b99_FOR_TEST', '2026-01-04T00:00:00Z')
    commit(root, '1.0.2+3', {'uk': uk, 'en': en}, None, '2026-01-05T00:00:00Z')
    print(f'fixture {root} {git(root, "rev-parse", "HEAD")}')
    return 0


def load(name):
    return json.loads((PROJECT / name).read_text(encoding='utf-8'))


def commit(root, version, files, tag, date):
    (root / 'l10n').mkdir(exist_ok=True)
    for name in ('uk', 'en'):
        path = root / 'l10n' / f'{name}.json'
        if name in files:
            path.write_text(json.dumps(files[name], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        elif path.exists():
            path.unlink()
    (root / 'pubspec.yaml').write_text(f'name: garden_notes\nversion: {version}\n', encoding='utf-8')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.com', 'commit', '-q', '-m', version,
        env=dict(ENV, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date))
    if tag:
        git(root, 'tag', tag)


def git(root, *args, env=ENV):
    return subprocess.run(['git', '-C', str(root), *args], env=env, check=True, capture_output=True,
                          text=True).stdout.strip()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
