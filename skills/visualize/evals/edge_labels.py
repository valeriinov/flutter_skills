#!/usr/bin/env python3
"""Check that edge labels with brackets or pipes reach mermaid as entity codes.

Usage: edge_labels.py [doc.visual.json]   (defaults to edge-label-brackets.visual.json)

Mermaid parses `-->|label|` unquoted, so a raw `(`, `[`, `{` or `|` there fails the whole
diagram with "Syntax error in text" while `check` still prints ok.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import visualize  # noqa: E402

EDGE = re.compile(r'-->\|(.*)\| \S+$')
RAW = re.compile(r'[()\[\]{}|]')


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('edge-label-brackets.visual.json')
    doc = json.loads(path.read_text(encoding='utf-8'))
    sources = [visualize.flow_source(doc, section['flow']) for section in doc['sections'] if section.get('flow')]
    if doc.get('flow'):
        sources.append(visualize.flow_source(doc, doc['flow']))
    entity_ids = {entity['id'] for entity in doc.get('entities', [])}
    sources.append(visualize.mermaid_source(doc, entity_ids, doc.get('links', []), 'LR'))
    labels = [match.group(1) for source in sources for line in source.splitlines()
              if (match := EDGE.search(line))]
    raw = [label for label in labels if RAW.search(label)]
    results = [('check passes', not visualize.problems(doc), '; '.join(visualize.problems(doc)[:3])),
               ('edge labels found', bool(labels), ''),
               ('no raw bracket or pipe in an edge label', not raw, '; '.join(raw[:3]))]
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if detail and not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
