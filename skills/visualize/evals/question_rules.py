#!/usr/bin/env python3
"""Check the question shape: short layer first, details and pros/cons collapsed.

Usage: question_rules.py   (uses the question of edge-label-brackets.visual.json beside this script)

The fixture passes `check`; each case breaks one rule in a copy and expects its message.
The render must collapse the details and each option's pros and cons, and mark the recommended option.
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import visualize  # noqa: E402


def drop_details(doc):
    del doc['questions'][0]['details']


def drop_the_problem(doc):
    del doc['questions'][0]['details']['problem']


def lengthen_the_gist(doc):
    doc['questions'][0]['gist'] = 'The source does not say. A cancelled order has no total. Accounting asked twice.'


def drop_the_pros(doc):
    del doc['questions'][0]['options'][1]['pros']


def pad_the_cons(doc):
    doc['questions'][0]['options'][0]['cons'] = ['One.', 'Two.', 'Three.', 'Four.']


CASES = [
    ('a question without details', drop_details, 'missing "details"'),
    ('details without the problem', drop_the_problem, '"details" missing "problem"'),
    ('a gist of three sentences', lengthen_the_gist, '"gist" has 3 sentences'),
    ('an option without pros', drop_the_pros, 'option B has no "pros"'),
    ('four cons on one option', pad_the_cons, '4 "cons", limit 3'),
]


def main():
    base = json.loads(Path(__file__).with_name('edge-label-brackets.visual.json').read_text(encoding='utf-8'))
    results = [('fixture passes check', not visualize.problems(base), '; '.join(visualize.problems(base)[:3]))]
    for name, breaks, expected in CASES:
        doc = copy.deepcopy(base)
        breaks(doc)
        found = visualize.problems(doc)
        results.append((f'rejects {name}', any(expected in problem for problem in found), '; '.join(found[:3])))
    results += render_results(base)
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if detail and not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    sys.exit(1 if failed else 0)


def render_results(doc):
    page = visualize.render(copy.deepcopy(doc))
    return [
        ('details are collapsed', '<details class="q-more">' in page, ''),
        ('pros and cons are collapsed per option', page.count('<details class="pc">') == 2, ''),
        ('an option without cons shows no cons list', page.count('+1 / −0') == 1, ''),
        ('the recommended option has a badge', page.count('class="badge-rec"') == 1, ''),
    ]


if __name__ == '__main__':
    main()
