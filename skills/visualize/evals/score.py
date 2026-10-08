#!/usr/bin/env python3
"""Score a visualize JSON against the agreed page format and a fixture's expectations.

Usage: score.py <doc.visual.json> <expect.json>

expect.json keys, all optional:
  overall          "flow" (behaviour source) or "entities" (a set of code changes)
  sections         [min, max] number of sections
  overview_variants   strings each found in a variant label on the overall flow
  section_branches    strings each found in a branch question or variant label of some section flow
  branches            strings each found in a branch question or variant label anywhere on the page
  overview_text       strings each found in an overall-flow node label or note
  changed_codes       strings each found in the code of a new or changed entity
  new_values          enum values each marked new in some shape view
  files               paths each listed under an entity or a section
  questions_min       minimum number of open questions
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import visualize  # noqa: E402


def main():
    doc = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    expect = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    results = [('check passes', not visualize.problems(doc), '; '.join(visualize.problems(doc)[:3]))]
    results += format_results(doc, expect)
    results += expectation_results(doc, expect)
    for name, passed, detail in results:
        print(f'{"PASS" if passed else "FAIL"}  {name}' + (f' — {detail}' if detail and not passed else ''))
    failed = sum(1 for _, passed, _ in results if not passed)
    print(f'{len(results) - failed}/{len(results)} passed')
    sys.exit(1 if failed else 0)


def format_results(doc, expect):
    sections = doc.get('sections', [])
    low, high = expect.get('sections', [1, 6])
    results = [(f'{low}–{high} sections', low <= len(sections) <= high, f'{len(sections)} sections')]
    if expect.get('overall') == 'flow':
        branches = [node for node in doc.get('flow', {}).get('nodes', []) if node.get('kind') == 'check']
        results.append(('overall diagram is a flow with one branch', len(branches) == 1, f'{len(branches)} branches'))
    if expect.get('overall') == 'entities':
        results.append(('overall diagram is the entity graph', not doc.get('flow') and bool(doc.get('links')), ''))
    results.append(('every section has a diagram',
                    all(section.get('flow') or section.get('entities') for section in sections), ''))
    return results


def expectation_results(doc, expect):
    texts = {
        'overview_variants': variant_labels(doc.get('flow', {})),
        'section_branches': [text for section in doc.get('sections', [])
                             for text in branch_texts(section.get('flow', {}))],
        'branches': branch_texts(doc.get('flow', {})) + [text for section in doc.get('sections', [])
                                                         for text in branch_texts(section.get('flow', {}))],
        'overview_text': [node.get(key, '') for node in doc.get('flow', {}).get('nodes', [])
                          for key in ('label', 'note')],
        'changed_codes': [entity.get('code', '') for entity in doc.get('entities', [])
                          if entity.get('status') in ('new', 'changed')],
        'new_values': new_values(doc),
        'files': all_files(doc),
    }
    results = []
    for key, haystack in texts.items():
        for needle in expect.get(key, []):
            results.append((f'{key}: {needle}', any(needle in text for text in haystack), ''))
    if 'questions_min' in expect:
        count = len(doc.get('questions', []))
        results.append((f'≥{expect["questions_min"]} open questions', count >= expect['questions_min'], f'{count}'))
    return results


def variant_labels(flow):
    branches = {node['id'] for node in flow.get('nodes', []) if node.get('kind') == 'check'}
    return [edge.get('label', '') for edge in flow.get('edges', []) if edge.get('from') in branches]


def branch_texts(flow):
    questions = [node.get('label', '') for node in flow.get('nodes', []) if node.get('kind') == 'check']
    return questions + variant_labels(flow)


def new_values(doc):
    found = []
    for section in doc.get('sections', []):
        for view in section.get('views', []):
            if view.get('type') == 'shape':
                collect_new_values(view.get('root', {}), found)
    return found


def collect_new_values(node, found):
    found += [value['value'] for value in node.get('values', []) if value.get('status') == 'new']
    for child in node.get('children', []):
        collect_new_values(child, found)


def all_files(doc):
    files = [file['path'] for entity in doc.get('entities', []) for file in entity.get('files', [])]
    return files + [file['path'] for section in doc.get('sections', []) for file in section.get('files', [])]


if __name__ == '__main__':
    main()
