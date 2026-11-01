#!/usr/bin/env python3
"""Check the flow grammar: entries, arrow labels, outcomes, artifacts and file paths.

Usage: flow_rules.py   (uses flow-rules.visual.json beside this script)

The fixture passes `check`; each case breaks one rule in a copy and expects its message.
The render of the fixture must carry the entry row, the outcome glyphs and the dashed arrows.
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import visualize  # noqa: E402


def label_plain_arrow(doc):
    doc['flow']['edges'][0]['label'] = 'checks'


def name_a_folder(doc):
    doc['entities'][1]['files'][0]['path'] = 'lib/export/'


def drop_every_start(doc):
    for node in doc['flow']['nodes']:
        if node.get('kind') == 'start':
            node['kind'] = 'step'


def feed_without_start(doc):
    doc['flow']['nodes'].append({'id': 'ci', 'label': 'CI reports the version'})
    doc['flow']['edges'].append({'from': 'ci', 'to': 'csv'})


def enter_a_start(doc):
    doc['flow']['edges'].append({'from': 'pick', 'to': 'menu', 'back': True})


def draw_an_artifact(doc):
    doc['flow']['nodes'].append({'id': 'doc', 'entity': 'notes'})
    doc['flow']['edges'].append({'from': 'done', 'to': 'doc'})


CASES = [
    ('a plain arrow with a label', label_plain_arrow, 'has label "checks"'),
    ('a folder as a file path', name_a_folder, 'name the files, not the folder'),
    ('an overall flow with no start', drop_every_start, 'has no "start" node'),
    ('a node nothing leads to', feed_without_start, 'node ci has no incoming arrow'),
    ('an arrow into a start', enter_a_start, 'start menu has an incoming arrow'),
    ('an artifact drawn as a step', draw_an_artifact, 'is an artifact'),
]


def main():
    base = json.loads(Path(__file__).with_name('flow-rules.visual.json').read_text(encoding='utf-8'))
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
    source = visualize.flow_source(doc, doc['flow'], with_code=False)
    page = visualize.render(copy.deepcopy(doc))
    return [
        ('entries share the top row', 'subgraph starts' in source, ''),
        ('outcomes carry ▸ ✓ ✕', all(glyph in source for glyph in '▸✓✕'), ''),
        ('fail and back arrows are dashed', source.count('-.->') == 2, source),
        ('plain arrows carry no label', ' --> n_' in source, ''),
        ('the overall diagram hides the code', 'OrderExport' not in source, ''),
        ('the legend shows the grey status', 'class="same"' in page, ''),
        ('the artifact is listed under the diagram', 'Export notes' in page and 'art-row' in page, ''),
    ]


if __name__ == '__main__':
    main()
