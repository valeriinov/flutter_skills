"""Extract the ASD-STE100 dictionary from the licensed PDF into a local word list.

Run: uv run --with pdfplumber python3 ste_extract.py <pdf> [--out <json>]
"""

import argparse
import bisect
import json
import re
from pathlib import Path

import pdfplumber

DEFAULT_OUT = Path.home() / '.claude' / 'ste' / 'words.json'

# The PDF layout is the contract. The margin alternates by page, so columns start at the
# header labels. A thin rule ends each row. Keywords are bold.
DICTIONARY_PAGE = re.compile(r'Page 2-1-[A-Z]\d+')
HEADER_BOTTOM = 88
FOOTER_TOP = 715
MEANING_HEADER = 'ALTERNATIVES'
EXAMPLE_HEADER = 'STE'
COLUMN_MARGIN = 4
LINE_TOLERANCE = 3
RULE_HEIGHT = 2
RULE_MIN_WIDTH = 50

KEYWORD = re.compile(r'^([^()]+?)\s*(\([^)]*\)\s*)?\(([a-z]+(?:,\s*[a-z]+)*)\)')
WORD = re.compile(r'^[a-z]+(?:-[a-z]+)*$')
BRACKETED = re.compile(r'\([^)]*\)|\[[^\]]*\]')
SENSE_NUMBER = re.compile(r'\b\d+\.\s*')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    approved, forms, unapproved = collect(read_entries(args.pdf))
    words = {'approved': approved, 'forms': forms, 'unapproved': unapproved}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(words, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'approved headwords: {len(approved)}')
    print(f'approved headword and part-of-speech pairs: {sum(len(parts) for parts in approved.values())}')
    print(f'forms: {len(forms)}')
    print(f'unapproved: {len(unapproved)}')
    print(f'written: {args.out}')


def read_entries(pdf_path):
    entries = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=['fontname'])
            if not is_dictionary_page(words):
                continue
            add_rows(entries, page_rows(page, words))
    return entries


def is_dictionary_page(words):
    footer = ' '.join(w['text'] for w in words if w['top'] > FOOTER_TOP)
    return bool(DICTIONARY_PAGE.search(footer))


def page_rows(page, words):
    header = {w['text']: w['x0'] - COLUMN_MARGIN for w in words if w['top'] < HEADER_BOTTOM}
    meaning_left, example_left = header[MEANING_HEADER], header[EXAMPLE_HEADER]
    rule_tops = sorted(r['top'] for r in page.rects if is_row_rule(r))
    rows = [{'keyword': [], 'meaning': []} for _ in range(len(rule_tops) + 1)]
    for line in body_lines(words):
        row = rows[bisect.bisect_left(rule_tops, line[0]['top'])]
        keyword = line_text(w for w in line if is_keyword(w, meaning_left))
        meaning = line_text(w for w in line if w['x0'] < example_left and not is_keyword(w, meaning_left))
        if keyword:
            row['keyword'].append(keyword)
        if meaning:
            row['meaning'].append(meaning)
    return rows


def is_keyword(word, meaning_left):
    return word['x0'] < meaning_left and 'Bold' in word['fontname']


def is_row_rule(rect):
    return HEADER_BOTTOM < rect['top'] < FOOTER_TOP and rect['height'] < RULE_HEIGHT and rect['width'] > RULE_MIN_WIDTH


def body_lines(words):
    body = sorted((w for w in words if HEADER_BOTTOM < w['top'] < FOOTER_TOP), key=lambda w: (w['top'], w['x0']))
    lines = []
    for word in body:
        if lines and word['top'] - lines[-1][0]['top'] <= LINE_TOLERANCE:
            lines[-1].append(word)
            continue
        lines.append([word])
    return lines


def line_text(words):
    return ' '.join(w['text'] for w in sorted(words, key=lambda w: w['x0']))


def add_rows(entries, rows):
    for row in rows:
        if entries and not row['keyword']:
            entries[-1]['meaning'] += row['meaning']
            continue
        entries.append(row)


def keyword_text(entry):
    return re.sub(r'-\s+', '', ' '.join(entry['keyword']))


def collect(entries):
    approved = {}
    forms = {}
    unapproved = {}
    for entry in entries:
        match = KEYWORD.match(keyword_text(entry))
        if not match:
            continue
        keyword = match.group(1).strip()
        word = keyword.lower()
        if not WORD.match(word) or is_phrase(match):
            continue
        if keyword.isupper():
            add_parts(approved, word, match.group(3))
            for form in keyword_forms(keyword_text(entry)[match.end(1):]):
                if form != word:
                    forms.setdefault(form, word)
            continue
        add_replacement(unapproved, word, ' '.join(entry['meaning']))
    return approved, forms, unapproved


def is_phrase(match):
    return match.group(2) is not None and not match.group(1).isupper()


def keyword_forms(text):
    tokens = (t.strip('(),.;:') for t in text.split())
    return [t.lower() for t in tokens if t.isupper() and WORD.match(t.lower())]


def add_parts(approved, word, parts):
    known = approved.setdefault(word, [])
    for part in (p.strip() for p in parts.split(',')):
        if part and part not in known:
            known.append(part)


def add_replacement(unapproved, word, meaning):
    alternatives = replacement_words(BRACKETED.sub(',', meaning))
    if not alternatives:
        alternatives = [re.sub(r'\s+', ' ', SENSE_NUMBER.sub('', BRACKETED.sub('', meaning))).strip(' ,').lower()]
    known = unapproved[word].split(', ') if word in unapproved else []
    merged = known + [a for a in alternatives if a and a not in known]
    if merged:
        unapproved[word] = ', '.join(merged)


def replacement_words(text):
    alternatives = []
    run = []
    for token in text.replace(',', ', ').split() + ['']:
        core = token.strip(',.;:')
        if core.isupper():
            run.append(core)
        if run and (not core.isupper() or token.endswith(',')):
            alternative = ' '.join(run).lower()
            if alternative not in alternatives:
                alternatives.append(alternative)
            run = []
    return alternatives


if __name__ == '__main__':
    main()
