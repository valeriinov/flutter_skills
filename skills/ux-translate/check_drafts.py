#!/usr/bin/env python3
# Portions derived from crowdin/skills (skills/translate/scripts/check-drafts.sh).
# MIT License, Copyright (c) Crowdin.
"""Check a drafts ledger (JSONL) for placeholder, plural and length problems.

Usage: check_drafts.py <ledger.jsonl> --lang <code> [--ratio <min>,<max>]

One line per problem: file, key, what, then two detail columns, tab-separated. A line
whose what starts with `warning:` does not fail the run.
Exit: 0 clean or warnings only, 1 mismatches, 2 usage error or invalid JSON.
It reads only the ledger; it never opens or rewrites a resource file.
"""

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

CATEGORIES = ('zero', 'one', 'two', 'few', 'many', 'other')
MIN_RATED_LENGTH = 10


class PluralRule(NamedTuple):
    required: tuple
    optional: tuple = ()
    one_is_exact: bool = True


PLURAL_RULES = {
    **dict.fromkeys(
        ['en', 'de', 'nl', 'sv', 'da', 'nb', 'nn', 'no', 'fi', 'et', 'el', 'bg', 'hu', 'tr', 'az',
         'ka', 'kk', 'hi', 'bn', 'sq', 'is', 'ur', 'sw', 'af'],
        PluralRule(('one', 'other'))),
    **dict.fromkeys(['fr', 'es', 'it', 'pt', 'ca'], PluralRule(('one', 'other'), ('many',))),
    **dict.fromkeys(['uk', 'ru', 'be'], PluralRule(('one', 'few', 'many', 'other'), one_is_exact=False)),
    'pl': PluralRule(('one', 'few', 'many', 'other')),
    **dict.fromkeys(['cs', 'sk'], PluralRule(('one', 'few', 'other'), ('many',))),
    'lt': PluralRule(('one', 'few', 'other'), ('many',), one_is_exact=False),
    **dict.fromkeys(['hr', 'sr', 'bs'], PluralRule(('one', 'few', 'other'), one_is_exact=False)),
    'ro': PluralRule(('one', 'few', 'other')),
    'lv': PluralRule(('zero', 'one', 'other'), one_is_exact=False),
    'sl': PluralRule(('one', 'two', 'few', 'other')),
    'he': PluralRule(('one', 'two', 'other')),
    'ga': PluralRule(('one', 'two', 'few', 'many', 'other')),
    'ar': PluralRule(CATEGORIES),
    'cy': PluralRule(CATEGORIES),
    **dict.fromkeys(['ja', 'zh', 'ko', 'vi', 'th', 'id', 'ms', 'lo', 'my', 'km'], PluralRule(('other',))),
}

PRINTF_OR_TAG_RE = re.compile(r'%([0-9]+\$)?[0-9.]*[A-Za-z@]|</?[A-Za-z0-9][^<>]*>')
ICU_RE = re.compile(r'\s*([\w.]+)\s*,\s*(plural|select|selectordinal)\s*,(.*)', re.S)
FORM_RE = re.compile(r'\s*(?:offset:\d+\s*)?(=?[\w-]+)\s*\{')


class UsageError(Exception):
    pass


def main(argv):
    try:
        ledger, lang, ratio = parse_args(argv)
        records = read_ledger(ledger)
    except UsageError as error:
        print(f'check_drafts: {error}', file=sys.stderr)
        return 2
    rules = PLURAL_RULES.get(re.split(r'[-_]', lang)[0].lower())
    if rules is None:
        print(f'check_drafts: no plural table for {lang}; plural categories not checked', file=sys.stderr)
    lines = [line for record in records for line in check_record(record, rules, ratio)]
    for line in lines:
        print(line)
    return 1 if any('\twarning: ' not in line for line in lines) else 0


def parse_args(argv):
    usage = 'usage: check_drafts.py <ledger.jsonl> --lang <code> [--ratio <min>,<max>]'
    if not argv or argv[0].startswith('--'):
        raise UsageError(usage)
    names = argv[1::2]
    options = dict(zip(names, argv[2::2]))
    if len(argv[1:]) % 2 or len(options) != len(names) or set(options) - {'--lang', '--ratio'} \
            or '--lang' not in options:
        raise UsageError(usage)
    return Path(argv[0]), options['--lang'], parse_ratio(options.get('--ratio'), usage)


def parse_ratio(value, usage):
    if value is None:
        return None
    try:
        low, high = (float(part) for part in value.split(','))
    except ValueError:
        raise UsageError(usage) from None
    if not 0 < low <= high:
        raise UsageError(usage)
    return low, high


def read_ledger(path):
    if not path.is_file():
        raise UsageError(f'no such file: {path}')
    records = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            raise UsageError(f'{path}:{number}: invalid JSON; review the placeholders by hand') from None
        if not isinstance(record, dict):
            raise UsageError(f'{path}:{number}: a ledger line must be a JSON object')
        records.append(record)
    return records


def check_record(record, rules, ratio):
    if 'target' not in record:
        return []
    source, target = record.get('source'), record['target']
    if json_type(source) != json_type(target):
        issues = [('shape mismatch', f'source: {json_type(source)}', f'target: {json_type(target)}')]
    elif isinstance(source, str):
        issues = compare_text(source, target, rules)
    elif isinstance(source, dict):
        issues = compare_forms(source, target, object_kind(source), rules, '', None)
    else:
        issues = []
    issues += limit_issues(record, target) + ratio_issues(source, target, ratio)
    return [f'{record.get("file")}\t{record.get("key")}\t{what}\t{left}\t{right}' for what, left, right in issues]


def object_kind(source):
    return 'plural' if {name for name in source if not name.startswith('=')} <= set(CATEGORIES) else 'select'


def json_type(value):
    if isinstance(value, str):
        return 'string'
    if isinstance(value, dict):
        return 'object'
    return 'null' if value is None else type(value).__name__


def compare_text(source, target, rules):
    source_parts, target_parts = parse(source), parse(target)
    source_set, target_set = placeholders(source_parts), placeholders(target_parts)
    if source_set != target_set:
        return [('placeholders', f'source: {" ".join(source_set)}', f'target: {" ".join(target_set)}')]
    source_percents, target_percents = literal_percents(source_parts), literal_percents(target_parts)
    if source_percents != target_percents:
        return [('placeholders', f'source: %% x{source_percents}', f'target: %% x{target_percents}')]
    pairs = zip(sorted(icu_blocks(source_parts), key=block_key), sorted(icu_blocks(target_parts), key=block_key))
    return [issue
            for (_, var, kind, source_forms), (_, _, _, target_forms) in pairs
            for issue in compare_forms(source_forms, target_forms, kind, rules, f' of {var}', var)]


def compare_forms(source, target, kind, rules, where, var):
    issues = form_placeholder_issues(source, target, where)
    if kind == 'select':
        if sorted(source) == sorted(target):
            return issues
        return issues + [(f'select branches{where}', f'source: {",".join(sorted(source))}',
                          f'target: {",".join(sorted(target))}')]
    issues += hash_issues(source, target, where, var, rules)
    return issues + category_issues(target, rules, where) if kind == 'plural' else issues


def form_placeholder_issues(source, target, where):
    # A target form with a namesake source form must match it exactly (Lingui numbers one expression
    # differently per branch); a form the source lacks may use any placeholder some source form uses
    # and, unless it names one number, must keep every placeholder all source forms share.
    forms = {name: set(placeholders(parse(text_of(text)))) for name, text in source.items()}
    union = set().union(*forms.values())
    shared = set.intersection(*forms.values()) if forms else set()
    issues = []
    for name, text in target.items():
        found = set(placeholders(parse(text_of(text))))
        expected = forms.get(name)
        if expected is not None and expected != found:
            issues.append((f'placeholders in form {name}{where}', f'source: {" ".join(sorted(expected))}',
                           f'target: {" ".join(sorted(found))}'))
        elif expected is None and (found - union or (shared - found and not is_exact_form(name))):
            issues.append((f'placeholders in form {name}{where}', f'source: {" ".join(sorted(union))}',
                           f'target: {" ".join(sorted(found))}'))
    return issues


def hash_issues(source, target, where, var, rules):
    # A form the source lacks follows the source `other` form, whose numbers it carves out;
    # `zero` and `=N` name one number and may spell it out. Where CLDR `one` also covers 21, 31…,
    # the target `one` shows the count whenever the source `other` does.
    counts = {name: count_marks(text_of(text), var) for name, text in source.items()}
    other = counts.get('other', max(counts.values(), default=0))
    return [(f'# missing in form {name}{where}', 'source: #', 'target: ')
            for name, text in target.items()
            if expected_marks(name, counts, other, rules) > 0 and count_marks(text_of(text), var) == 0]


def expected_marks(name, counts, other, rules):
    if name == 'one' and rules is not None and not rules.one_is_exact:
        return max(counts.get('one', 0), other)
    return counts.get(name, 0 if is_exact_form(name) else other)


def count_marks(text, var):
    parts = parse(text)
    return hashes(parts) + sum(1 for part in parts if var is not None and part == ('ph', f'{{{var}}}'))


def is_exact_form(name):
    return name == 'zero' or name.startswith('=')


def category_issues(target, rules, where):
    if rules is None:
        return []
    required, optional = rules.required, rules.optional
    present = {name for name in target if not name.startswith('=')}
    allowed = set(required) | set(optional) | {'zero'}
    if set(required) <= present <= allowed:
        return []
    return [(f'plural categories{where}', f'expected: {",".join(required)}',
             f'target: {",".join(sorted(present, key=category_order))}')]


def category_order(name):
    return CATEGORIES.index(name) if name in CATEGORIES else len(CATEGORIES)


def limit_issues(record, target):
    limit = record.get('limit')
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        return []
    what = 'over hard limit' if record.get('limit_hard') is True else 'warning: over limit'
    return [(f'{what}{label}', f'limit: {limit}', f'target: {len(text)} chars')
            for label, text in rendered_forms(target) if len(text) > limit]


def ratio_issues(source, target, ratio):
    if ratio is None:
        return []
    source_text, target_text = representative(source), representative(target)
    if len(source_text) < MIN_RATED_LENGTH:
        return []
    value = len(target_text) / len(source_text)
    low, high = ratio
    if low <= value <= high:
        return []
    what = 'warning: much longer' if value > high else 'warning: much shorter'
    return [(what, f'ratio: {value:.2f}', f'corridor: {low:g}-{high:g}')]


def rendered_forms(value):
    if isinstance(value, dict):
        return [(f' in form {name}{label.replace(" in form", ",")}', text)
                for name, form in value.items() for label, text in rendered_forms(text_of(form))]
    if not isinstance(value, str):
        return []
    return [(f' in form {", ".join(labels)}' if labels else '', text) for labels, text in variants(parse(value))]


def representative(value):
    if isinstance(value, dict):
        value = value.get('other', next(iter(value.values()), ''))
    if not isinstance(value, str):
        return ''
    rendered = variants(parse(value))
    return next((text for labels, text in rendered if all(label.endswith(' other') for label in labels)),
                rendered[0][1])


def text_of(value):
    return value if isinstance(value, str) else ''


def parse(text):
    """Split text into plain strings, ('ph', raw) placeholders and ('icu', var, kind, forms) blocks."""
    parts = []
    start = index = 0
    while index < len(text):
        if text[index] != '{':
            index += 1
            continue
        end = text.find('}}', index) + 1 if text.startswith('{{', index) else matching_brace(text, index)
        if end <= index:
            break
        parts.append(text[start:index])
        parts.append(brace_part(text[index:end + 1]))
        start = index = end + 1
    parts.append(text[start:])
    return [part for part in parts if part != '']


def matching_brace(text, start):
    depth = 0
    for index in range(start, len(text)):
        depth += {'{': 1, '}': -1}.get(text[index], 0)
        if depth == 0:
            return index
    return -1


def brace_part(raw):
    icu = ICU_RE.fullmatch(raw[1:-1])
    forms = parse_forms(icu.group(3)) if icu else None
    if forms is None:
        return ('ph', raw)
    return ('icu', icu.group(1), icu.group(2), forms)


def parse_forms(body):
    forms = {}
    index = 0
    while body[index:].strip():
        selector = FORM_RE.match(body, index)
        if not selector:
            return None
        end = matching_brace(body, selector.end() - 1)
        if end < 0:
            return None
        forms[selector.group(1)] = body[selector.end():end]
        index = end + 1
    return forms or None


def placeholders(parts):
    found = []
    for part in parts:
        if isinstance(part, str):
            found += [match.group(0) for match in PRINTF_OR_TAG_RE.finditer(part.replace('%%', ''))]
        elif part[0] == 'ph':
            found.append(part[1])
        else:
            found.append(f'{{{part[1]}, {part[2]}}}')
    return sorted(found)


def literal_percents(parts):
    return sum(part.count('%%') for part in parts if isinstance(part, str))


def hashes(parts):
    return sum(part.count('#') for part in parts if isinstance(part, str))


def icu_blocks(parts):
    return [part for part in parts if isinstance(part, tuple) and part[0] == 'icu']


def block_key(block):
    return block[1], block[2]


def variants(parts):
    """Every rendering of the text, one per combination of ICU forms, labelled `<var> <form>`."""
    results = [((), '')]
    for part in parts:
        if isinstance(part, str):
            options = [((), part)]
        elif part[0] == 'ph':
            options = [((), part[1])]
        else:
            options = [((f'{part[1]} {name}',) + labels, text)
                       for name, form in part[3].items() for labels, text in variants(parse(form))]
        results = [(head + tail, left + right) for head, left in results for tail, right in options]
    return results


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
