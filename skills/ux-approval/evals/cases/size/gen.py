#!/usr/bin/env python3
"""Write round specs for a large synthetic project, or measure a built page.

Usage:
  gen.py write <dir> <keys> <rounds>   write <dir>/r<n>/spec.json for rounds 1..<rounds>
  gen.py measure <page> <limit>        exit 0 when the page is under <limit> bytes
"""

import json
import sys
from pathlib import Path

SCREENS = ('home', 'plant', 'settings', 'search', 'profile', 'help')
CHANGED_SHARE = 10


def main(argv):
    if argv[0] == 'measure':
        return measure(Path(argv[1]), int(argv[2]))
    count, rounds = int(argv[2]), int(argv[3])
    for number in range(1, rounds + 1):
        path = Path(argv[1]) / f'r{number}' / 'spec.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(spec(count, number), ensure_ascii=False), encoding='utf-8')
    return 0


def measure(page, limit):
    size = page.stat().st_size
    print(f'page {size} bytes, limit {limit}: {"under" if size < limit else "over"}')
    return 0 if size < limit else 1


def spec(count, number):
    keys = [f'{SCREENS[index % len(SCREENS)]}Label{index}' for index in range(count)]
    source = {key: f'Підпис екрана номер {index} для перевірки розміру сторінки' for index, key in enumerate(keys)}
    target = {key: target_text(index, number) for index, key in enumerate(keys)}
    base = {key: target_text(index, 1) for index, key in enumerate(keys)}
    return {
        'title': 'Size check', 'lang': 'uk', 'ui': {}, 'product': 'Size check', 'slug': 'size-check',
        'round': number, 'final': False, 'origin': {'branch': 'main', 'commit': f'{number:07d}'},
        'brief': '# Brief\n\n' + 'A line of the brief that stays the same between rounds.\n' * 80,
        'files': {
            'source': {'lang': 'uk', 'path': 'l10n/uk.json', 'values': source, 'base': source},
            'target': {'lang': 'en', 'path': 'l10n/en.json', 'values': target, 'base': base},
        },
        'terms': [{'id': 'підпис', 'source': 'підпис', 'target': 'label', 'meaning': 'a screen label',
                   'variants': [], 'match': {'stems': ['підпис'], 'keys': []}}],
        'questions': [],
        'review': [],
        'projectChanges': [],
        'invalid': [],
        'rejected': [],
        'codeDefects': [],
        'risk': [],
        'identical': [],
        'batches': [{'id': screen, 'label': screen, 'prefixes': [screen],
                     'expected': sum(1 for key in keys if key.startswith(screen))} for screen in SCREENS],
    }


def target_text(index, number):
    revision = number if index % CHANGED_SHARE == number % CHANGED_SHARE else 1
    return f'Screen label number {index} for the page size check, revision {revision}'


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
