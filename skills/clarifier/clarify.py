#!/usr/bin/env python3
"""Check a reader-facing text: reading budget, structure, facts against a source, stock phrases."""
import json
import re
import sys
from pathlib import Path

RATES = {'ru': 160, 'uk': 160, 'en': 190}
DEFAULT_MINUTES = 5
MAX_SENTENCE_WORDS = 25
MAX_PARAGRAPH_SENTENCES = 5
MAX_LIST_ITEMS = 5
USAGE = 'usage: clarify.py check <file> [--lang ru|uk|en] [--source <src>] [--minutes N]'
KNOWN_ABBREVIATIONS = {'API', 'URL', 'JSON', 'CSV', 'HTML', 'PR', 'UI', 'UX', 'SDK', 'LLM', 'ISO', 'QA'}

SENTENCE_RE = re.compile(r'(?<=[.!?…])\s+')
WORD_CHAR_RE = re.compile(r'\w')
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)
FENCE_RE = re.compile(r'^\s*(?:```|~~~)')
HEADING_RE = re.compile(r'^\s*#')
TAG_LINE_RE = re.compile(r'^\s*</?(?:details|summary)\b')
INLINE_CODE_RE = re.compile(r'`([^`]*)`')
LIST_ITEM_RE = re.compile(r'^(\s*)(?:[-*+]|\d+[.)])\s+')
LABEL_RE = re.compile(r'^\*{0,2}[^\W\d_][\w-]*\*{0,2}:')
ABBR_RE = re.compile(r'(?<!\w)[A-ZА-ЯЁІЇЄҐ]{2,5}(?!\w)')
NUMBER_RE = re.compile(r'(?<![\w.])\d+(?:[.,:/-]\d+)*')
URL_RE = re.compile(r'https?://[^\s)>\]`]+')
GROUPED_NUMBER_RE = re.compile(r'(?<!\d)\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?!\d)')
GROUP_SPACE_RE = re.compile(r'[ \u00a0\u202f]')
DASH_RANGE_RE = re.compile(r'(?<=\d)[–—](?=\d)')

COMMON_PHRASES = [
    (r'если нужно', 'drop the closing offer'),
    (r'если хотите', 'drop the closing offer'),
    (r'в (?:этом|данном) (?:документе|тексте)', 'drop the meta text'),
    (r'якщо потрібно', 'drop the closing offer'),
    (r'у (?:цьому|даному) (?:документі|тексті)', 'drop the meta text'),
    (r'let me know', 'drop the closing offer'),
    (r'hope this helps', 'drop the closing offer'),
    (r'in this (?:document|text|article)', 'drop the meta text'),
]
LANG_PHRASES = {
    'ru': [
        (r'раскры\w* потенциал', 'say what changes'),
        (r'бесшовн\w*', 'say what works without a step'),
        (r'игра\w* ключевую роль', 'say what it does'),
        (r'является неотъемлемой частью', 'say what it is part of'),
        (r'стоит отметить', 'drop it'),
        (r'осуществля\w*', 'a plain verb'),
        (r'следовательно', 'значит'),
        (r'заблаговременно', 'заранее'),
        (r'в настоящее время', 'сейчас'),
        (r'оказа\w* содействие', 'помочь'),
        (r'по-видимому', 'drop the hedge or give the reason'),
        (r'в некоторой степени', 'drop the hedge or give the measure'),
        (r'так сказать', 'drop it'),
        (r'по сути', 'drop it'),
        (r'имплементир\w*', 'внедрить'),
    ],
    'uk': [
        (r'прийма\w* участ\w*', 'брати участь'),
        (r'слідуюч\w*', 'наступні'),
        (r'люб(?:ий|ого|ому|ім|а|у|е|і)', 'будь-який'),
        (r'сам\w* кращ\w*', 'найкращий'),
        (r'получа\w*', 'отримувати'),
        (r'на протязі', 'протягом'),
        (r'здійснення', 'a plain verb'),
        (r'відповідно до вимог', 'за вимогами'),
    ],
    'en': [
        (r'in order to', 'to'),
        (r'it is worth noting', 'drop it'),
        (r'it should be noted', 'drop it'),
        (r'basically', 'drop it'),
        (r'utiliz\w*', 'use'),
        (r'leverag\w*', 'use'),
        (r'seamless\w*', 'say what works without a step'),
        (r'delve\w*', 'look at'),
    ],
}


class Markdown:
    def __init__(self):
        self.paragraphs = []
        self.headings = []
        self.problems = []
        self.current = None
        self.in_fence = False
        self.in_details = False
        self.list_line = 0
        self.list_items = 0

    def read(self, text):
        visible = COMMENT_RE.sub(lambda match: '\n' * match.group(0).count('\n'), text)
        for number, line in enumerate(visible.split('\n'), start=1):
            self.feed(number, line)
        self.close_paragraph()
        self.close_list()

    def feed(self, number, line):
        if FENCE_RE.match(line):
            self.in_fence = not self.in_fence
            self.close_paragraph()
            return
        if self.in_fence:
            return
        if not line.strip():
            self.close_paragraph()
            return
        if HEADING_RE.match(line):
            self.headings.append((number, line.strip().lstrip('#').strip()))
        if HEADING_RE.match(line) or TAG_LINE_RE.match(line):
            self.track_details(line)
            self.close_paragraph()
            self.close_list()
            return
        item = LIST_ITEM_RE.match(line)
        if item:
            self.add_item(number, line, item)
            return
        if self.current is None or LABEL_RE.match(line):
            self.close_list()
            self.start(number, line)
            return
        self.current['parts'].append(line.strip())

    def track_details(self, line):
        if '<details' in line:
            self.in_details = True
        if '</details>' in line:
            self.in_details = False

    def add_item(self, number, line, item):
        if len(item.group(1)) >= 2:
            self.problems.append((number, 'nested list'))
        elif self.list_items == 0:
            self.list_line, self.list_items = number, 1
        else:
            self.list_items += 1
        self.start(number, line[item.end():])

    def start(self, number, line):
        self.close_paragraph()
        self.current = {'line': number, 'parts': [line.strip()], 'details': self.in_details}

    def close_paragraph(self):
        if self.current is not None:
            self.paragraphs.append(self.current)
        self.current = None

    def close_list(self):
        if self.list_items > MAX_LIST_ITEMS:
            self.problems.append((self.list_line, f'list of {self.list_items} items, limit {MAX_LIST_ITEMS}'))
        self.list_items = 0


def block(where, raw, budget=True, sentences=True, prose=True):
    text = INLINE_CODE_RE.sub(' ', raw)
    return {'where': where, 'raw': raw, 'text': text, 'budget': budget, 'sentences': sentences, 'prose': prose}

def markdown_blocks(path, text):
    reader = Markdown()
    reader.read(text)
    blocks = [block(f'{path}:{paragraph["line"]}', ' '.join(paragraph['parts']), budget=not paragraph['details'])
              for paragraph in reader.paragraphs]
    blocks += [block(f'{path}:{number}', heading, budget=False, sentences=False, prose=False)
               for number, heading in reader.headings]
    problems = [(f'{path}:{number}', msg) for number, msg in reader.problems]
    return blocks, problems

def json_blocks(path, doc):
    fields = [('summary', doc.get('summary', ''), True)]
    for index, section in enumerate(doc.get('sections', [])):
        where = f'sections[{index}]'
        fields.append((f'{where}.takeaway', section.get('takeaway', ''), True))
        fields += [(f'{where}.lines[{number}].text', line.get('text', ''), False)
                   for number, line in enumerate(section.get('lines', []))]
        fields.append((f'{where}.check', section.get('check', ''), True))
    fields += [(f'questions[{index}].gist', question.get('gist', ''), True)
               for index, question in enumerate(doc.get('questions', []))]
    return [block(f'{path}: {name}', text, sentences=sentences) for name, text, sentences in fields if text]

def load_blocks(path):
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.json':
        doc = json.loads(text)
        return json_blocks(path, doc), [], doc.get('lang')
    blocks, problems = markdown_blocks(path, text)
    return blocks, problems, None

def word_count(text):
    return sum(1 for token in text.split() if WORD_CHAR_RE.search(token))

def sentences_of(text):
    return [sentence for sentence in SENTENCE_RE.split(text.strip()) if sentence]

def budget_problems(path, blocks, lang, minutes):
    words = sum(word_count(item['text']) for item in blocks if item['budget'])
    limit = minutes * RATES[lang]
    if words <= limit:
        return []
    return [(f'{path}: budget', f'{words} words, limit {limit} ({minutes} min × {RATES[lang]} words/min)')]

def structure_problems(blocks):
    problems = []
    for item in blocks:
        sentences = sentences_of(item['text'])
        if len(sentences) > MAX_PARAGRAPH_SENTENCES:
            problems.append((item['where'],
                             f'paragraph of {len(sentences)} sentences, limit {MAX_PARAGRAPH_SENTENCES}'))
        problems += sentence_problems(item, sentences)
    return problems

def sentence_problems(item, sentences):
    if not item['sentences']:
        return []
    counts = [word_count(sentence) for sentence in sentences]
    return [(item['where'], f'sentence of {count} words, limit {MAX_SENTENCE_WORDS}')
            for count in counts if count > MAX_SENTENCE_WORDS]

def abbreviation_hints(blocks):
    seen = set(KNOWN_ABBREVIATIONS)
    hints = []
    for item in blocks:
        for match in ABBR_RE.finditer(item['text']):
            if match.group() in seen:
                continue
            seen.add(match.group())
            if not is_expanded(item['text'], match):
                hints.append((item['where'], f'{match.group()} has no expansion on first use'))
    return hints

def is_expanded(text, match):
    return text[match.end():].lstrip().startswith('(') or text[:match.start()].endswith('(')

def phrase_hints(blocks, lang):
    patterns = [(re.compile(rf'(?<!\w){pattern}(?!\w)', re.I), suggestion)
                for pattern, suggestion in COMMON_PHRASES + LANG_PHRASES[lang]]
    return [(item['where'], f'«{match.group()}» → {suggestion}')
            for item in blocks for pattern, suggestion in patterns for match in pattern.finditer(item['text'])]

def facts(text):
    urls = [url.rstrip('.,;:') for url in URL_RE.findall(text)]
    codes = INLINE_CODE_RE.findall(text)
    prose = INLINE_CODE_RE.sub(' ', URL_RE.sub(' ', text))
    return numbers_of(prose), urls + codes

def numbers_of(text):
    joined = GROUPED_NUMBER_RE.sub(lambda match: GROUP_SPACE_RE.sub('', match.group()), text)
    return NUMBER_RE.findall(DASH_RANGE_RE.sub('-', joined))

def new_number_problems(blocks, source_text):
    known = set(numbers_of(source_text))
    problems, reported = [], set()
    for item in blocks:
        for number in facts(item['raw'])[0]:
            if number in known or number in reported:
                continue
            reported.add(number)
            problems.append((item['where'], f'new: {number}'))
    return problems

def lost_hints(path, blocks, source_blocks):
    result = set()
    for item in blocks:
        numbers, others = facts(item['raw'])
        result.update(numbers + others)
    lost = []
    for item in source_blocks:
        numbers, others = facts(item['raw'])
        lost += [token for token in numbers + others if token not in result and token not in lost]
    return [(str(path), f'lost: {token}') for token in lost]

def option(argv, name):
    if name not in argv:
        return None
    index = argv.index(name) + 1
    return argv[index] if index < len(argv) else ''

def cli_check(argv):
    path = Path(argv[0])
    blocks, problems, doc_lang = load_blocks(path)
    lang = option(argv, '--lang') or doc_lang
    minutes = option(argv, '--minutes') or str(DEFAULT_MINUTES)
    if not is_valid_options(lang, minutes):
        print(USAGE, file=sys.stderr)
        return 2
    prose = [item for item in blocks if item['prose']]
    problems += budget_problems(path, prose, lang, int(minutes))
    problems += structure_problems(prose)
    hints = abbreviation_hints(prose) + phrase_hints(prose, lang)
    source = option(argv, '--source')
    if source:
        source_path = Path(source)
        problems += new_number_problems(blocks, source_path.read_text(encoding='utf-8'))
        hints += lost_hints(path, blocks, load_blocks(source_path)[0])
    for where, msg in problems:
        print(f'{where}: {msg}')
    for where, msg in hints:
        print(f'{where}: hint: {msg}')
    if problems:
        return 1
    print('ok')
    return 0

def is_valid_options(lang, minutes):
    return lang in RATES and minutes.isdigit() and int(minutes) > 0

def main(argv):
    if len(argv) < 2 or argv[0] != 'check':
        print(USAGE, file=sys.stderr)
        return 2
    return cli_check(argv[1:])

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
