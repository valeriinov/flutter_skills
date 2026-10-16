#!/usr/bin/env python3
"""Warn about keys in an approval queue that still wait for team approval.

Usage: pending.py <approval-queue.md>

A missing file or an empty table prints nothing. Otherwise one line, tab-separated like
check_drafts.py: queue path, empty key, a `warning:` naming the next step, key count, and
the `Approval:` line when the queue is still open.
Exit: 0 silent or warning, 2 usage error, unreadable or malformed queue.
It reads only the queue; it never runs git or opens a locale file.
"""

import re
import sys
from pathlib import Path

APPROVAL_RE = re.compile(r'Approval: \S+, round \d+, (open|final|applied)')
WARNINGS = {
    'open': 'warning: awaiting approval',
    'final': 'warning: run ux-translate Apply approved',
    'applied': 'warning: start a new artifact (ux-approval Create)',
}


class UsageError(Exception):
    pass


def main(argv):
    try:
        queue = parse_args(argv)
        approval, keys = read_queue(queue)
    except UsageError as error:
        print(f'pending: {error}', file=sys.stderr)
        return 2
    if not keys:
        return 0
    state = APPROVAL_RE.fullmatch(approval).group(1) if approval else 'open'
    shown = approval if state == 'open' else ''
    print(f'{queue}\t\t{WARNINGS[state]}\t{len(keys)} keys\t{shown}')
    return 0


def parse_args(argv):
    if len(argv) != 1 or argv[0].startswith('--'):
        raise UsageError('usage: pending.py <approval-queue.md>')
    return Path(argv[0])


def read_queue(queue):
    if not queue.exists():
        return '', []
    try:
        lines = [line.strip() for line in queue.read_text(encoding='utf-8').splitlines()]
    except (OSError, UnicodeDecodeError) as error:
        raise UsageError(f'cannot read {queue}: {error}')
    approvals = [line for line in lines if line.startswith('Approval:')]
    if len(approvals) > 1 or any(not APPROVAL_RE.fullmatch(line) for line in approvals):
        raise UsageError(f'{queue}: expected one line "Approval: <url>, round <n>, <open | final | applied>"')
    return (approvals[0] if approvals else ''), table_keys(queue, [line for line in lines if line.startswith('|')])


def table_keys(queue, rows):
    if not rows:
        return []
    cells = [[cell.strip() for cell in row.strip('|').split('|')] for row in rows]
    if cells[0] != ['key', 'date'] or len(cells) < 2 or any(len(row) != 2 for row in cells):
        raise UsageError(f'{queue}: expected a table "| key | date |"')
    return [row[0] for row in cells[2:] if row[0]]


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
