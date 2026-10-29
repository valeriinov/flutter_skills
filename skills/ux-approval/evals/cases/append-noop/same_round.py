#!/usr/bin/env python3
"""Compare the latest round of two approval pages, apart from releases and stages.

Usage: same_round.py <approval.py> <page.html> <other page.html>

Prints `same round <n>`, or one `differs <field>` line per field that differs. Exit 0 same, 1 differs.
"""

import importlib.util
import sys
from pathlib import Path

SKIPPED = ('releases',)
SKIPPED_KEY_FIELDS = ('stage', 'approved')


def main(argv):
    spec = importlib.util.spec_from_file_location('approval', argv[0])
    approval = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(approval)
    first, second = (latest_round(approval, Path(path)) for path in argv[1:3])
    fields = sorted(set(first) | set(second))
    differs = [name for name in fields if first.get(name) != second.get(name)]
    differs += [f'keys.{one["key"]}.{name}' for one, other in zip(first['keys'], second['keys'])
                for name in sorted(set(one) | set(other)) if one.get(name) != other.get(name)]
    for name in differs:
        print(f'differs {name}')
    if not differs:
        print(f'same round {first["round"]}')
    return 1 if differs else 0


def latest_round(approval, path):
    entry = approval.full_rounds(approval.read_page(path)['rounds'])[-1]
    keys = [{name: value for name, value in key.items() if name not in SKIPPED_KEY_FIELDS} for key in entry['keys']]
    return dict({name: value for name, value in entry.items() if name not in SKIPPED}, keys=keys)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
