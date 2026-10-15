#!/usr/bin/env python3
"""Check a round spec, build the approval page with every round, apply a closed round.

Usage:
  approval.py check <spec> [--previous <page.html>]
  approval.py build <spec> [--previous <page.html>] [--template <path>] [-o <page.html>] [--stats]
  approval.py apply <page.html> <log.json> <editors.json> <round.json> --project <root> -o <dir>

check prints `ok` or one `spec:<where>: <problem>` line per problem. build embeds every round
into the template's page-data slot and writes page.html beside the spec. apply takes the latest
answer of each editor in the closed round, settles disputes by the round's priority, reconciles
each key with the project files against `base`, and writes the next round's inputs into <dir>.
Exit: 0 ok, 1 spec problems, 2 usage error, unreadable input or <dir> inside <root>.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

DATA_SLOT = '/*__DATA__*/'
PAGE_DATA_RE = re.compile(r'<script[^>]*\bid="page-data"[^>]*>(.*?)</script>', re.S)
TEMPLATE = Path(__file__).resolve().parent / 'page_template.html'
SPEC_KEYS = ('title', 'lang', 'ui', 'product', 'slug', 'round', 'files')
SIDES = ('source', 'target')
SEVERITIES = ('blocking', 'significant', 'minor')
CHANGE_KINDS = ('project', 'conflict', 'added')
KEYED_SECTIONS = ('review', 'projectChanges', 'invalid')
SOURCE_SECTIONS = ('identical', 'codeDefects')
COLLECTIONS = {'keys': 'key', 'terms': 'id', 'questions': 'id', 'review': 'id', 'batches': 'id'}
ROUND_SCALARS = ('brief', 'origin')
STATS_LIST_LIMIT = 20
DECISIONS_HEADING = '## Decisions'
OPEN_QUESTIONS_HEADING = '## Open questions'


class InputError(Exception):
    pass


def main(argv):
    args = parse_args(argv)
    try:
        return args.run(args)
    except InputError as error:
        print(f'approval: {error}', file=sys.stderr)
        return 2


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    check_parser = commands.add_parser('check')
    check_parser.add_argument('spec', type=Path)
    check_parser.add_argument('--previous', type=Path)
    check_parser.set_defaults(run=run_check)
    build_parser = commands.add_parser('build')
    build_parser.add_argument('spec', type=Path)
    build_parser.add_argument('--previous', type=Path)
    build_parser.add_argument('--template', type=Path, default=TEMPLATE)
    build_parser.add_argument('-o', '--output', type=Path)
    build_parser.add_argument('--stats', action='store_true')
    build_parser.set_defaults(run=run_build)
    apply_parser = commands.add_parser('apply')
    for name in ('page', 'log', 'editors', 'round'):
        apply_parser.add_argument(name, type=Path)
    apply_parser.add_argument('--project', type=Path, required=True)
    apply_parser.add_argument('-o', '--output', type=Path, required=True)
    apply_parser.set_defaults(run=run_apply)
    return parser.parse_args(argv)


# ---------------------------------------------------------------- input

def load_json(path):
    if not path.is_file():
        raise InputError(f'no such file: {path}')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise InputError(f'{path}: invalid JSON: {error}') from None


def read_page(path):
    if not path.is_file():
        raise InputError(f'no such file: {path}')
    match = PAGE_DATA_RE.search(path.read_text(encoding='utf-8'))
    if not match:
        raise InputError(f'{path}: no page-data element')
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise InputError(f'{path}: page-data is not JSON: {error}') from None
    if not isinstance(data, dict) or not data.get('rounds'):
        raise InputError(f'{path}: page-data has no rounds')
    return data


def documents(raw):
    if isinstance(raw, dict) and isinstance(raw.get('data'), dict):
        return [document(raw)]
    if isinstance(raw, dict):
        raw = next((raw[name] for name in ('documents', 'docs', 'items') if isinstance(raw.get(name), list)), raw)
    if isinstance(raw, dict):
        return [(str(doc_id), doc) for doc_id, doc in raw.items() if isinstance(doc, dict)]
    return [document(item) for item in raw if isinstance(item, dict)]


def document(item):
    doc_id = item.get('id')
    body = item['data'] if isinstance(item.get('data'), dict) else item
    return (None if doc_id is None else str(doc_id)), body


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


# ---------------------------------------------------------------- check

def run_check(args):
    spec = load_json(args.spec)
    previous = read_page(args.previous) if args.previous else None
    if report_problems(spec, previous):
        return 1
    print('ok')
    return 0


def report_problems(spec, previous):
    found = problems(spec, previous)
    for problem in found:
        print(f'spec:{problem}', file=sys.stderr)
    return bool(found)


def problems(spec, previous):
    found = head_problems(spec)
    if found:
        return found
    values = values_by_lang(spec)
    found += target_problems(spec)
    found += reference_problems(spec, values)
    found += review_problems(spec, values)
    found += id_problems(spec)
    found += term_problems(spec)
    found += question_problems(spec)
    found += batch_problems(spec)
    found += round_problems(spec, previous)
    return found


def head_problems(spec):
    if not isinstance(spec, dict):
        return ['spec must be a JSON object']
    found = [f'{key}: missing' for key in SPEC_KEYS if key not in spec]
    if not isinstance(spec.get('round'), int) or spec.get('round', 0) < 1:
        found.append('round: must be a positive integer')
    files = spec.get('files') if isinstance(spec.get('files'), dict) else {}
    for side in SIDES:
        found += side_problems(side, files.get(side))
    return found


def side_problems(side, entry):
    if not isinstance(entry, dict):
        return [f'files.{side}: missing']
    found = [f'files.{side}.{key}: missing' for key in ('lang', 'path') if not entry.get(key)]
    return found + [f'files.{side}.{key}: must be an object' for key in ('values', 'base')
                    if not isinstance(entry.get(key), dict)]


def values_by_lang(spec):
    return {spec['files'][side]['lang']: spec['files'][side]['values'] for side in SIDES}


def source_values(spec):
    return spec['files']['source']['values']


def target_problems(spec):
    source = source_values(spec)
    return [f'files.target.values.{key}: not in source values'
            for key in spec['files']['target']['values'] if key not in source]


def reference_problems(spec, values):
    source = source_values(spec)
    found = [f'{section}.{item.get("lang")}.{item.get("key")}: key not in {item.get("lang")} values'
             for section in KEYED_SECTIONS for item in spec.get(section, [])
             if not is_referenced(section, item, values, source)]
    found += [f'{section}.{item.get("key")}: key not in source values'
              for section in SOURCE_SECTIONS for item in spec.get(section, []) if item.get('key') not in source]
    found += [f'risk.{item.get("class")}: key {key} not in source values'
              for item in spec.get('risk', []) for key in item.get('keys', []) if key not in source]
    found += [f'terms.{term.get("id")}: match key {key} not in source values'
              for term in spec.get('terms', []) for key in term.get('match', {}).get('keys', []) if key not in source]
    return found + [f'projectChanges.{item.get("lang")}.{item.get("key")}: kind must be one of {CHANGE_KINDS}'
                    for item in spec.get('projectChanges', []) if item.get('kind') not in CHANGE_KINDS]


def is_referenced(section, item, values, source):
    if section == 'projectChanges' and item.get('value') is None:
        return item.get('key') in source
    return item.get('key') in values.get(item.get('lang'), {})


def review_problems(spec, values):
    rejected = {rejection_key(item) for item in spec.get('rejected', [])}
    found = []
    for row in spec.get('review', []):
        value = values.get(row.get('lang'), {}).get(row.get('key'))
        if value is None:
            continue
        found += row_problems(f'review.{row["lang"]}.{row["key"]}', row, value, rejected)
    return found


def row_problems(where, row, value, rejected):
    found = []
    if str(row.get('severity', '')).lower() not in SEVERITIES:
        found.append(f'{where}: severity must be one of {SEVERITIES}')
    found += was_problems(where, row.get('was'), value)
    proposal = row.get('proposal')
    if is_blank(proposal) and not row.get('why'):
        found.append(f'{where}: empty proposal needs "why"')
    if not is_blank(proposal) and json_type(proposal) != json_type(value):
        found.append(f'{where}: proposal is {json_type(proposal)}, value is {json_type(value)}')
    if rejection_key(row) in rejected:
        found.append(f'{where}: proposal was rejected before')
    return found


def was_problems(where, was, value):
    if json_type(was) != json_type(value):
        return [f'{where}: was is {json_type(was)}, value is {json_type(value)}']
    if isinstance(value, str):
        return [] if unquote(was) == value else [f'{where}: was differs from the value']
    if set(was) != set(value):
        return [f'{where}: was forms {",".join(sorted(was))} differ from value forms {",".join(sorted(value))}']
    return [f'{where}: was form {name} differs from the value' for name in value if unquote(was[name]) != value[name]]


def unquote(text):
    return text.replace('`', '') if isinstance(text, str) else text


def rejection_key(item):
    return item.get('lang'), item.get('key'), canonical(item.get('proposal'))


def id_problems(spec):
    found = duplicate_problems('terms', [term.get('id') for term in spec.get('terms', [])])
    found += duplicate_problems('questions', [question.get('id') for question in spec.get('questions', [])])
    found += duplicate_problems('review', [f'{row.get("lang")}.{row.get("key")}' for row in spec.get('review', [])])
    return found + duplicate_problems('batches', [batch.get('id') for batch in spec.get('batches', [])])


def duplicate_problems(section, ids):
    seen = set()
    duplicates = [name for name in ids if name in seen or seen.add(name)]
    return [f'{section}.{name}: duplicate id' for name in dict.fromkeys(duplicates)]


def term_problems(spec):
    found = []
    for term in spec.get('terms', []):
        where = f'terms.{term.get("id")}'
        expected = slug(str(term.get('source', '')))
        if term.get('id') != expected:
            found.append(f'{where}: id must be "{expected}", the slug of its source')
        found += [f'{where}: stem {stem!r} does not compile: {error}'
                  for stem, error in stem_errors(term.get('match', {}).get('stems', []))]
    return found


def slug(text):
    words = '-'.join(text.lower().split())
    return ''.join(char for char in words if char.isalnum() or char == '-')


def stem_errors(stems):
    errors = []
    for stem in stems:
        try:
            re.compile(stem)
        except re.error as error:
            errors.append((stem, error))
    return errors


def question_problems(spec):
    terms = {term.get('id') for term in spec.get('terms', [])}
    source = source_values(spec)
    found = []
    for question in spec.get('questions', []):
        where = f'questions.{question.get("id")}'
        keys = [option.get('key') for option in question.get('options', [])]
        if len(keys) < 2:
            found.append(f'{where}: needs at least 2 options')
        found += duplicate_problems(f'{where}.options', keys)
        recommended = recommendation_key(question.get('recommendation'))
        if recommended and recommended not in keys:
            found.append(f'{where}: recommendation {recommended} is not an option')
        found += [f'{where}: unknown term {term}' for term in question.get('terms', []) if term not in terms]
        found += [f'{where}: unknown key {key}' for key in question.get('keys', []) if key not in source]
    return found


def recommendation_key(recommendation):
    if isinstance(recommendation, dict):
        return recommendation.get('key')
    return recommendation


def batch_problems(spec):
    batches = spec.get('batches', [])
    if not batches:
        return []
    found = [f'batches.{batch.get("id")}: no prefixes; only the last batch catches the rest'
             for batch in batches[:-1] if not batch.get('prefixes')]
    assigned = {key: batch_of(key, batches) for key in source_values(spec)}
    found += [f'batches: key {key} matches no batch' for key, batch in assigned.items() if batch is None]
    counts = batch_counts(assigned)
    return found + [f'batches.{batch["id"]}: {counts.get(batch["id"], 0)} keys, expected {batch.get("expected")}'
                    for batch in batches if counts.get(batch['id'], 0) != batch.get('expected')]


def batch_of(key, batches):
    return next((batch['id'] for batch in batches
                 if not batch.get('prefixes') or any(key.startswith(prefix) for prefix in batch['prefixes'])), None)


def batch_counts(assigned):
    counts = {}
    for batch in assigned.values():
        counts[batch] = counts.get(batch, 0) + 1
    return counts


def round_problems(spec, previous):
    if previous is None:
        return [] if spec['round'] == 1 else [f'round: {spec["round"]} needs --previous <page.html>']
    history = full_rounds(previous['rounds'])
    last = history[-1]
    found = [f'round: previous page round {last["round"]} is final'] if last.get('final') else []
    if spec['round'] != last['round'] + 1:
        found.append(f'round: {spec["round"]}, expected {last["round"] + 1} after the previous page')
    titles = {question['id']: question.get('title') for entry in history for question in entry['questions']}
    return found + [f'questions.{question.get("id")}: title differs from the previous round'
                    for question in spec.get('questions', [])
                    if question.get('id') in titles and question.get('title') != titles[question['id']]]


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def json_type(value):
    if isinstance(value, str):
        return 'string'
    if isinstance(value, dict):
        return 'object'
    return 'null' if value is None else type(value).__name__


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------- build

def run_build(args):
    spec = load_json(args.spec)
    previous = read_page(args.previous) if args.previous else None
    if report_problems(spec, previous):
        return 1
    if not args.template.is_file():
        raise InputError(f'no such file: {args.template}')
    template = args.template.read_text(encoding='utf-8')
    if DATA_SLOT not in template:
        raise InputError(f'{args.template}: no {DATA_SLOT} slot')
    data = page_data(spec, previous)
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    output = args.output or args.spec.parent / 'page.html'
    output.write_text(template.replace(DATA_SLOT, payload, 1), encoding='utf-8')
    if args.stats:
        print_stats(data)
    print(f'page {output} {output.stat().st_size} bytes')
    return 0


def page_data(spec, previous):
    rounds = previous['rounds'] if previous else []
    history = full_rounds(rounds)
    last = history[-1] if history else None
    current = full_round(spec, last)
    files = spec['files']
    return {
        'title': spec['title'],
        'lang': spec['lang'],
        'product': spec['product'],
        'slug': spec['slug'],
        'ui': spec['ui'],
        'sourceLang': files['source']['lang'],
        'targetLang': files['target']['lang'],
        'files': {side: {'lang': files[side]['lang'], 'path': files[side]['path']} for side in SIDES},
        'rounds': rounds + [current if last is None else delta(last, current)],
    }


def full_rounds(rounds):
    history = []
    for entry in rounds:
        history.append(merge(history[-1], entry) if history else entry)
    return history


def merge(last, entry):
    merged = dict(entry)
    for name in ROUND_SCALARS:
        merged[name] = last[name] if entry.get(name) is None else entry[name]
    removed = entry.get('removed', {})
    for name, id_field in COLLECTIONS.items():
        merged[name] = merge_items(last[name], entry.get(name, []), set(removed.get(name, [])), id_field)
    return merged


def merge_items(before, changed, removed, id_field):
    items = {item[id_field]: item for item in before}
    items.update({item[id_field]: item for item in changed})
    return [item for item_id, item in items.items() if item_id not in removed]


def delta(last, current):
    entry = {'round': current['round'], 'final': current['final']}
    entry.update({name: None if current[name] == last[name] else current[name] for name in ROUND_SCALARS})
    removed = {}
    for name, id_field in COLLECTIONS.items():
        before = {item[id_field]: item for item in last[name]}
        now = {item[id_field] for item in current[name]}
        entry[name] = [item for item in current[name] if before.get(item[id_field]) != item]
        removed[name] = [item_id for item_id in before if item_id not in now]
    entry['rejected'] = current['rejected']
    entry['removed'] = removed
    return entry


def full_round(spec, last):
    previous_values = {entry['key']: entry['values'] for entry in last['keys']} if last else {}
    questions = spec.get('questions', [])
    batches = spec.get('batches', [])
    keys = key_entries(spec, previous_values)
    counts = batch_counts({entry['key']: entry['batch'] for entry in keys})
    return {
        'round': spec['round'],
        'final': bool(spec.get('final')),
        'origin': spec.get('origin') or {'branch': '', 'commit': ''},
        'brief': spec.get('brief', ''),
        'keys': keys,
        'terms': [term_entry(term, questions) for term in spec.get('terms', [])],
        'questions': [question_entry(question) for question in questions],
        'review': [dict(row, id=f'{row["lang"]}.{row["key"]}') for row in spec.get('review', [])],
        'rejected': spec.get('rejected', []),
        'batches': [dict(batch, prefixes=batch.get('prefixes', []), count=counts.get(batch['id'], 0))
                    for batch in batches],
        'removed': {name: [] for name in COLLECTIONS},
    }


def term_entry(term, questions):
    match = term.get('match', {})
    entry = dict(term, target=term.get('target', ''), variants=term.get('variants', []),
                 match={'stems': match.get('stems', []), 'keys': match.get('keys', [])})
    entry['confidence'] = term_confidence(term, questions)
    return entry


def term_confidence(term, questions):
    if any(term.get('id') in question.get('terms', []) for question in questions):
        return 'low'
    return 'medium' if not term.get('target') else 'high'


def question_entry(question):
    return dict(question, recommendation=question.get('recommendation') or '', terms=question.get('terms', []))


def key_entries(spec, previous_values):
    index = key_index(spec)
    return [key_entry(key, spec, index, previous_values) for key in source_values(spec)]


def key_index(spec):
    terms = spec.get('terms', [])
    return {
        'langs': [spec['files'][side]['lang'] for side in SIDES],
        'patterns': [(term, [re.compile(stem, re.I) for stem in term.get('match', {}).get('stems', [])])
                     for term in terms],
        'emptyTerms': {term['id'] for term in terms if not term.get('target')},
        'review': group_by_key(spec.get('review', [])),
        'projectChanges': group_by_key(spec.get('projectChanges', [])),
        'invalid': group_by_key(spec.get('invalid', [])),
        'risk': {key: item['class'] for item in reversed(spec.get('risk', [])) for key in item.get('keys', [])},
        'codeDefects': {item['key']: item.get('text', '') for item in spec.get('codeDefects', [])},
        'identical': {item['key']: item.get('why') for item in spec.get('identical', [])},
    }


def group_by_key(items):
    groups = {}
    for item in items:
        groups.setdefault(item['key'], []).append(item)
    return groups


def key_entry(key, spec, index, previous_values):
    files = spec['files']
    langs = index['langs']
    values = {files[side]['lang']: files[side]['values'][key] for side in SIDES if key in files[side]['values']}
    base = {files[side]['lang']: files[side]['base'][key] for side in SIDES if key in files[side]['base']}
    terms = key_terms(key, text_of(values.get(langs[0])), index['patterns'])
    rows = index['review'].get(key, [])
    entry = {
        'key': key,
        'values': values,
        'base': base,
        'batch': batch_of(key, spec.get('batches', [])),
        'terms': terms,
        'questions': [question['id'] for question in spec.get('questions', [])
                      if set(question.get('terms', [])) & set(terms) or key in question.get('keys', [])],
        'risk': index['risk'].get(key),
        'reviewRows': [f'{row["lang"]}.{key}' for row in rows],
        'codeDefect': index['codeDefects'].get(key),
        'identical': key in index['identical'],
        'identicalWhy': index['identical'].get(key),
        'projectChange': [{'lang': item['lang'], 'kind': item['kind'], 'value': item.get('value')}
                          for item in index['projectChanges'].get(key, [])],
        'invalid': [{'lang': item['lang'], 'reason': item.get('reason', '')} for item in index['invalid'].get(key, [])],
        'changed': changed_langs(key, values, previous_values, langs),
    }
    entry['confidence'], entry['reasons'] = confidence(entry, rows, index['emptyTerms'])
    return entry


def text_of(value):
    if isinstance(value, dict):
        return ' '.join(str(form) for form in value.values())
    return value if isinstance(value, str) else ''


def key_terms(key, text, patterns):
    return [term['id'] for term, stems in patterns
            if key in term.get('match', {}).get('keys', []) or any(stem.search(text) for stem in stems)]


def changed_langs(key, values, previous_values, langs):
    if key not in previous_values:
        return []
    return [lang for lang in langs if previous_values[key].get(lang) != values.get(lang)]


def confidence(entry, rows, empty_terms):
    severities = [str(row.get('severity', '')).lower() for row in rows]
    changes = entry['projectChange']
    low = [f'question:{question}' for question in entry['questions']]
    low += [f'risk:{entry["risk"]}'] if entry['risk'] else []
    low += ['codeDefect'] if entry['codeDefect'] else []
    low += ['review:blocking' for severity in severities if severity == 'blocking']
    low += [f'conflict:{change["lang"]}' for change in changes if change['kind'] == 'conflict']
    low += [f'invalid:{item["lang"]}' for item in entry['invalid']]
    medium = [f'review:{severity}' for severity in severities if severity != 'blocking']
    medium += [f'term:{term}' for term in entry['terms'] if term in empty_terms]
    medium += [f'changed:{lang}' for lang in entry['changed']]
    medium += [f'{change["kind"]}:{change["lang"]}' for change in changes if change['kind'] != 'conflict']
    level = 'low' if low else 'medium' if medium else 'high'
    return level, low + medium


def print_stats(data):
    history = full_rounds(data['rounds'])
    print(f'rounds {len(history)}')
    for entry, full in zip(data['rounds'], history):
        print(round_stats(entry, full))
    last = history[-1]
    print('batches ' + ', '.join(batch_stat(batch) for batch in last['batches']))
    print_key_list('low', [(entry['key'], ', '.join(entry['reasons'])) for entry in last['keys']
                           if entry['confidence'] == 'low'])
    print_key_list('changed', [(entry['key'], ', '.join(entry['changed'])) for entry in last['keys'] if entry['changed']])


def round_stats(entry, full):
    sizes = ', '.join(f'{name} {len(full[name])} (delta {len(entry.get(name, []))})' for name in COLLECTIONS)
    removed = sum(len(ids) for ids in entry.get('removed', {}).values())
    levels = {level: sum(1 for key in full['keys'] if key['confidence'] == level) for level in ('low', 'medium', 'high')}
    kinds = {kind: sum(1 for key in full['keys'] for change in key['projectChange'] if change['kind'] == kind)
             for kind in CHANGE_KINDS}
    changed = sum(1 for key in full['keys'] if key['changed'])
    return (f'round {full["round"]}{" final" if full.get("final") else ""}: {sizes}, removed {removed}; '
            + ', '.join(f'{level} {count}' for level, count in levels.items())
            + f'; changed {changed}; ' + ', '.join(f'{kind} {count}' for kind, count in kinds.items()))


def batch_stat(batch):
    mismatch = '' if batch['count'] == batch.get('expected') else f' (expected {batch.get("expected")})'
    return f'{batch["id"]} {batch["count"]}{mismatch}'


def print_key_list(label, items):
    for key, detail in items[:STATS_LIST_LIMIT]:
        print(f'{label} {key}: {detail}')
    if len(items) > STATS_LIST_LIMIT:
        print(f'{label}: {len(items) - STATS_LIST_LIMIT} more')


# ---------------------------------------------------------------- apply

def run_apply(args):
    root = args.project.resolve()
    output = args.output.resolve()
    if output.is_relative_to(root):
        raise InputError(f'-o {args.output} lies inside --project {args.project}; use a scratch directory')
    data = read_page(args.page)
    last = full_rounds(data['rounds'])[-1]
    if last.get('final'):
        raise InputError(f'{args.page}: round {last["round"]} is final')
    closing = closing_doc(load_json(args.round), last['round'])
    editors = {doc_id: doc for doc_id, doc in documents(load_json(args.editors)) if doc_id is not None}
    events = round_events(load_json(args.log), last['round'], closing.get('closedAt'))
    project = project_values(data, root)
    draft = Draft(data, last, closing, editors)
    apply_answers(draft, events)
    draft.reconcile(project)
    output.mkdir(parents=True, exist_ok=True)
    write_outputs(draft, output, root)
    print(f'wrote {output}')
    return 0


def closing_doc(raw, number):
    if isinstance(raw, dict) and 'priority' in raw:
        return raw
    found = {round_id(doc_id): doc for doc_id, doc in documents(raw)}
    if str(number) not in found:
        listed = ', '.join(f'rounds/{doc_id}' for doc_id in found if doc_id is not None) or 'no numbered document'
        raise InputError(f'round {number} is not closed: no rounds/{number} document in the round file (found: {listed})')
    return found[str(number)]


def round_id(doc_id):
    return None if doc_id is None else doc_id.rsplit('/', 1)[-1]


def round_events(raw, number, closed_at):
    return [doc for _, doc in documents(raw) if is_round_event(doc, number, closed_at)]


def is_round_event(doc, number, closed_at):
    if str(doc.get('round', 1)) != str(number):
        return False
    if closed_at and str(doc.get('at', '')) > str(closed_at):
        return False
    return isinstance(doc.get('object'), str) and bool(doc.get('by'))


def project_values(data, root):
    values = {}
    for side in SIDES:
        entry = data['files'][side]
        path = root / entry['path']
        loaded = load_json(path)
        if not isinstance(loaded, dict):
            raise InputError(f'{path}: must be a JSON object')
        values[entry['lang']] = loaded
    return values


class Draft:
    def __init__(self, data, last, closing, editors):
        self.data = data
        self.last = last
        self.closing = closing
        self.editors = editors
        self.source = data['files']['source']['lang']
        self.target = data['files']['target']['lang']
        self.langs = (self.source, self.target)
        self.keys = {entry['key']: entry for entry in last['keys']}
        self.values = {lang: {key: entry['values'][lang] for key, entry in self.keys.items() if lang in entry['values']}
                       for lang in self.langs}
        self.terms = {term['id']: dict(term) for term in last['terms']}
        self.questions = {question['id']: question for question in last['questions']}
        self.review = {row['id']: row for row in last['review']}
        self.rejected = list(last['rejected'])
        self.decisions = []
        self.free_text = []
        self.ledger = []
        self.disputes = []
        self.touched_terms = set()
        self.answered = set()
        self.order = list(self.keys)
        self.base = {}
        self.changes = []
        self.removed = []

    def name(self, editor):
        doc = self.editors.get(editor, {})
        return doc.get('name') or doc.get('email') or f'editor {self.editor_number(editor)}'

    def editor_number(self, editor):
        seen = sorted(self.editors, key=lambda other: (str(self.editors[other].get('firstSeenAt') or ''), other))
        return seen.index(editor) + 1 if editor in seen else len(seen) + 1

    def set_value(self, lang, key, value):
        previous = self.values[lang].get(key)
        self.values[lang][key] = value
        if lang == self.target and value != previous:
            self.ledger.append({'key': key, 'target': value, 'previous': previous})

    def reconcile(self, project):
        order = list(project[self.source])
        self.removed = [key for key in self.order if key not in project[self.source]]
        counts = {'artifact': 0, 'project': 0, 'conflict': 0, 'added': 0}
        for key in order:
            kind = self.reconcile_key(key, project)
            counts[kind] += 1
        for key in self.removed:
            print(f'removed {key}')
        self.order = order
        print('reconcile: ' + ', '.join(f'{kind} {count}' for kind, count in counts.items()) + f', removed {len(self.removed)}')

    def reconcile_key(self, key, project):
        if key not in self.keys:
            return self.add_key(key, project)
        base = self.keys[key].get('base', {})
        kinds = [self.reconcile_value(key, lang, base.get(lang), project[lang].get(key)) for lang in self.langs]
        self.base[key] = {lang: project[lang][key] for lang in self.langs if key in project[lang]}
        return next((kind for kind in ('conflict', 'project') if kind in kinds), 'artifact')

    def reconcile_value(self, key, lang, base, project_value):
        artifact = self.values[lang].get(key)
        if project_value == artifact:
            return None
        if project_value == base and not self.is_open_conflict(key, lang):
            return None
        if artifact == base:
            self.put(lang, key, project_value)
            self.note(lang, key, 'project', project_value)
            return 'project'
        self.note(lang, key, 'conflict', project_value)
        return 'conflict'

    def is_open_conflict(self, key, lang):
        return key not in self.answered and lang in [change['lang'] for change in conflict_changes(self.keys[key])]

    def add_key(self, key, project):
        for lang in self.langs:
            if key in project[lang]:
                self.put(lang, key, project[lang][key])
                self.note(lang, key, 'added', project[lang][key])
        self.base[key] = {lang: project[lang][key] for lang in self.langs if key in project[lang]}
        return 'added'

    def put(self, lang, key, value):
        if value is None:
            self.values[lang].pop(key, None)
            return
        self.values[lang][key] = value

    def note(self, lang, key, kind, value):
        self.changes.append({'lang': lang, 'key': key, 'kind': kind, 'value': value})
        print(f'{kind} {key} {lang}')


def apply_answers(draft, events):
    answers, withdrawn = latest_answers(events)
    first_answer = first_answers(events)
    priority = draft.closing.get('priority', [])
    rank = lambda editor: (0, priority.index(editor), '') if editor in priority else (1, first_answer[editor], editor)
    for object_id, editor in withdrawn:
        print(f'withdrawn {object_id} by {draft.name(editor)}')
    for slot, events_by_editor in answer_slots(draft, answers).items():
        by_editor = {editor: main_answer(events) for editor, events in events_by_editor.items()}
        winner, losers = resolve(by_editor, rank)
        if losers:
            record_dispute(draft, slot, by_editor, winner, losers)
        apply_answer(draft, by_editor[winner]['object'], by_editor[winner])
        apply_displaced_keeps(draft, events_by_editor[winner], by_editor[winner])
    print(f'answers {len(answers)}, disputes {len(draft.disputes)}, withdrawn {len(withdrawn)}')


def latest_answers(events):
    latest = {}
    for event in events:
        by_editor = latest.setdefault(event['object'], {})
        current = by_editor.get(event['by'])
        if current is None or str(event.get('at')) >= str(current.get('at')):
            by_editor[event['by']] = event
    answers = {object_id: {editor: event for editor, event in by_editor.items() if has_answer(event)}
               for object_id, by_editor in latest.items()}
    withdrawn = [(object_id, editor) for object_id, by_editor in latest.items()
                 for editor, event in by_editor.items() if not has_answer(event)]
    return {object_id: by_editor for object_id, by_editor in answers.items() if by_editor}, withdrawn


def answer_slots(draft, answers):
    slots = {}
    for object_id, by_editor in answers.items():
        for editor, event in by_editor.items():
            slots.setdefault(slot_of(draft, object_id, editor), {}).setdefault(editor, []).append(event)
    return slots


def main_answer(events):
    return max(events, key=lambda event: (sets_value(event), str(event.get('at'))))


def sets_value(event):
    if event['object'].startswith('review.'):
        return True
    if event.get('pick') == 'custom':
        return not is_blank(event.get('text'))
    return event.get('pick') in ('project', 'artifact')


def apply_displaced_keeps(draft, events, applied):
    for event in events:
        if event is not applied and event['object'].startswith('review.') and choice(event)[0] == 'keep':
            apply_answer(draft, event['object'], event)


def slot_of(draft, object_id, editor):
    kind, _, rest = object_id.partition('.')
    if kind == 'key' and rest in draft.keys:
        return f'{edit_lang(draft, rest)}.{rest}'
    if kind == 'source':
        return f'{draft.source}.{rest}'
    if kind == 'comment':
        return f'{object_id}.{editor}'
    return rest if kind == 'review' else object_id


def has_answer(event):
    return bool(event.get('pick')) or not is_blank(event.get('text')) or event.get('reviewed') is True


def first_answers(events):
    first = {}
    for event in events:
        first[event['by']] = min(first.get(event['by'], str(event.get('at'))), str(event.get('at')))
    return first


def choice(event):
    pick = event.get('pick')
    if pick == 'custom':
        return 'custom', canonical(event.get('text'))
    return (pick,) if pick else ('keep',)


def resolve(by_editor, rank):
    winner = min(by_editor, key=rank)
    expected = choice(by_editor[winner])
    return winner, [editor for editor, event in by_editor.items() if choice(event) != expected]


def record_dispute(draft, slot, by_editor, winner, losers):
    draft.disputes.append({'slot': slot, 'winner': winner, 'losers': losers, 'answers': by_editor})
    print(f'dispute {slot}: {draft.name(winner)} over {", ".join(draft.name(editor) for editor in losers)}')


def apply_answer(draft, object_id, event):
    kind, _, rest = object_id.partition('.')
    handler = {'key': apply_key, 'source': apply_source, 'review': apply_review, 'term': apply_term,
               'q': apply_question, 'note': apply_note, 'comment': apply_comment}.get(kind)
    outcome = handler(draft, rest, event) if handler else None
    print(f'answer {object_id}: {outcome or "skipped, unknown object"} ({draft.name(event["by"])})')


def apply_key(draft, key, event):
    if key not in draft.keys:
        return None
    draft.answered.add(key)
    pick = event.get('pick')
    if pick == 'project':
        for change in conflict_changes(draft.keys[key]):
            draft.put(change['lang'], key, change['value'])
        return 'project value'
    if pick != 'custom' or is_blank(event.get('text')):
        return 'kept'
    draft.set_value(edit_lang(draft, key), key, event['text'])
    return 'new value'


def apply_source(draft, key, event):
    if key not in draft.keys:
        return None
    if event.get('pick') != 'custom' or is_blank(event.get('text')):
        return 'kept'
    draft.set_value(draft.source, key, event['text'])
    return 'new value'


def edit_lang(draft, key):
    conflicts = [change['lang'] for change in conflict_changes(draft.keys[key])]
    return draft.source if conflicts == [draft.source] else draft.target


def conflict_changes(entry):
    return [change for change in entry['projectChange'] if change['kind'] == 'conflict']


def apply_review(draft, row_id, event):
    row = draft.review.get(row_id)
    if row is None or row['key'] not in draft.keys:
        return None
    pick = choice(event)[0]
    if pick == 'keep':
        draft.rejected.append({'lang': row['lang'], 'key': row['key'], 'proposal': row.get('proposal')})
        return 'keep, rejected'
    if pick == 'custom':
        draft.set_value(row['lang'], row['key'], event['text'])
        draft.free_text.append((f'review.{row_id}', event['by'], event['text']))
        return 'custom value'
    if pick == 'accept' and not is_blank(row.get('proposal')):
        draft.set_value(row['lang'], row['key'], row['proposal'])
        return 'proposal accepted'
    return 'kept, nothing to accept'


def apply_term(draft, term_id, event):
    term = draft.terms.get(term_id)
    if term is None:
        return None
    pick = choice(event)[0]
    if pick == 'custom':
        draft.free_text.append((f'term.{term_id}', event['by'], event['text']))
    target = event['text'] if pick == 'custom' else term_pick(term, pick)
    if target is None:
        return f'kept, unknown pick {pick}'
    term['approved'] = draft.last['round']
    if target != term.get('target'):
        term['target'] = target
        draft.touched_terms.add(term_id)
    return f'target {target}'


def term_pick(term, pick):
    return pick if pick in [term.get('target', '')] + term.get('variants', []) else None


def apply_question(draft, question_id, event):
    question = draft.questions.get(question_id)
    if question is None:
        return None
    pick = choice(event)[0]
    option = next((option for option in question.get('options', []) if option.get('key') == pick), None)
    if pick == 'custom':
        draft.free_text.append((f'q.{question_id}', event['by'], event['text']))
    decision = event['text'] if pick == 'custom' else option and option.get('text')
    if decision is None:
        return f'kept open, unknown pick {pick}'
    draft.decisions.append((question, decision))
    draft.touched_terms.update(question.get('terms', []))
    return f'decided {decision}'


def apply_note(draft, note_id, event):
    if is_blank(event.get('text')):
        return None
    draft.free_text.append((f'note.{note_id}', event['by'], event['text']))
    return 'comment'


def apply_comment(draft, key, event):
    if is_blank(event.get('text')):
        return None
    draft.free_text.append((f'comment.{key}', event['by'], event['text']))
    return 'comment'


# ---------------------------------------------------------------- apply output

def write_outputs(draft, output, root):
    spec = next_spec(draft, root)
    write_json(output / 'spec-next.json', spec)
    (output / 'brief.md').write_text(spec['brief'], encoding='utf-8')
    for side in SIDES:
        write_json(output / f'{spec["files"][side]["lang"]}.json', spec['files'][side]['values'])
    named = named_keys(draft)
    (output / 'named-keys.txt').write_text(''.join(f'{key}\n' for key in named), encoding='utf-8')
    ledger = ''.join(json.dumps(line, ensure_ascii=False) + '\n' for line in ledger_lines(draft))
    (output / f'changed-{draft.target}.jsonl').write_text(ledger, encoding='utf-8')
    (output / 'conflicts.md').write_text(conflicts_markdown(draft), encoding='utf-8')
    (output / 'free-text.md').write_text(free_text_markdown(draft), encoding='utf-8')
    print(f'named {len(named)}: {", ".join(named)}')


def ledger_lines(draft):
    path = draft.data['files']['target']['path']
    return [{'file': path, 'key': line['key'], 'source': draft.values[draft.source].get(line['key']), **line}
            for line in draft.ledger if line['key'] in draft.order]


def next_spec(draft, root):
    data, last = draft.data, draft.last
    kept = set(draft.order)
    decided = {question['id'] for question, _ in draft.decisions}
    values = {lang: {key: draft.values[lang][key] for key in draft.order if key in draft.values[lang]}
              for lang in draft.langs}
    base = {lang: {key: draft.base[key][lang] for key in draft.order if lang in draft.base.get(key, {})}
            for lang in draft.langs}
    batches = [{name: batch[name] for name in ('id', 'label', 'prefixes')} for batch in last['batches']]
    counts = batch_counts({key: batch_of(key, batches) for key in draft.order})
    return {
        'title': data['title'],
        'lang': data['lang'],
        'ui': data['ui'],
        'product': data['product'],
        'slug': data['slug'],
        'round': last['round'] + 1,
        'final': False,
        'origin': project_origin(root),
        'brief': updated_brief(last.get('brief') or '', draft),
        'files': {side: {'lang': lang, 'path': data['files'][side]['path'], 'values': values[lang], 'base': base[lang]}
                  for side, lang in zip(SIDES, draft.langs)},
        'terms': [next_term(term, kept) for term in draft.terms.values()],
        'questions': [question for question_id, question in draft.questions.items() if question_id not in decided],
        'review': [],
        'projectChanges': draft.changes,
        'invalid': [],
        'rejected': [item for item in draft.rejected if item['key'] in kept],
        'codeDefects': [{'key': entry['key'], 'text': entry['codeDefect']}
                        for entry in last['keys'] if entry['codeDefect'] and entry['key'] in kept],
        'risk': risk_groups(last['keys'], kept),
        'identical': [{'key': entry['key'], 'why': entry['identicalWhy']}
                      for entry in last['keys'] if entry['identical'] and entry['key'] in kept],
        'batches': [dict(batch, expected=counts.get(batch['id'], 0)) for batch in batches],
    }


def next_term(term, kept):
    entry = {name: value for name, value in term.items() if name != 'confidence'}
    entry['match'] = dict(term['match'], keys=[key for key in term['match']['keys'] if key in kept])
    return entry


def risk_groups(entries, kept):
    groups = {}
    for entry in entries:
        if entry['risk'] and entry['key'] in kept:
            groups.setdefault(entry['risk'], []).append(entry['key'])
    return [{'keys': keys, 'class': risk} for risk, keys in groups.items()]


def project_origin(root):
    return {'branch': git(root, '--abbrev-ref', 'HEAD'), 'commit': git(root, 'HEAD')}


def git(root, *revision):
    try:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', *revision], capture_output=True, text=True)
    except OSError:
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def updated_brief(brief, draft):
    titles = [question.get('title', '') for question, _ in draft.decisions]
    lines = []
    section = ''
    for line in brief.splitlines():
        section = line.strip() if line.startswith('## ') else section
        if section == OPEN_QUESTIONS_HEADING and is_decided_bullet(line, titles):
            continue
        lines.append(line)
    when = str(draft.closing.get('closedAt') or date.today().isoformat())[:10]
    rows = [f'| {question["id"]} {question.get("title", "")}: {decision} | {draft.target} | {when} |'.replace('\n', ' ')
            for question, decision in draft.decisions]
    return '\n'.join(insert_rows(lines, rows)) + '\n'


def is_decided_bullet(line, titles):
    return line.lstrip().startswith('- ') and any(title and title in line for title in titles)


def insert_rows(lines, rows):
    if not rows:
        return lines
    if DECISIONS_HEADING not in [line.strip() for line in lines]:
        return lines + ['', DECISIONS_HEADING, '', '| decision | language | date |', '|---|---|---|'] + rows
    start = [line.strip() for line in lines].index(DECISIONS_HEADING)
    table = [index for index in range(start + 1, len(lines)) if lines[index].lstrip().startswith('|')]
    end = table_end(table) if table else start + 1
    return lines[:end] + rows + lines[end:]


def table_end(rows):
    end = rows[0]
    for index in rows:
        if index != end:
            break
        end += 1
    return end


def named_keys(draft):
    previous = {key: entry['values'].get(draft.source) for key, entry in draft.keys.items()}
    marked = {change['key'] for change in draft.changes if change['kind'] in ('project', 'added')}
    touched = {key for key, entry in draft.keys.items() if set(entry['terms']) & draft.touched_terms}
    return [key for key in draft.order
            if key in marked or key in touched or previous.get(key) != draft.values[draft.source].get(key)]


def conflicts_markdown(draft):
    lines = [f'# Disputes, round {draft.last["round"]}', '']
    for dispute in draft.disputes:
        answers = dispute['answers']
        winner = answers[dispute['winner']]
        lines.append(f'- `{dispute["slot"]}` — winner {draft.name(dispute["winner"])} ({winner["object"]}): '
                     f'{answer_text(winner)}')
        lines += [f'  - over {draft.name(editor)} ({answers[editor]["object"]}): {answer_text(answers[editor])}'
                  for editor in dispute['losers']]
    if not draft.disputes:
        lines.append('No disputes.')
    return '\n'.join(lines) + '\n'


def answer_text(event):
    found = choice(event)
    return f'"{text_of(event["text"]) or event["text"]}"' if found[0] == 'custom' else found[0]


def free_text_markdown(draft):
    lines = [f'# Own variants and comments, round {draft.last["round"]}', '']
    lines += [f'- `{object_id}` ({draft.name(editor)}): {text_of(text) or text}' for object_id, editor, text in draft.free_text]
    if not draft.free_text:
        lines.append('No own variants or comments.')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
