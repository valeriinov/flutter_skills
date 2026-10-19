#!/usr/bin/env python3
"""Check a reader-facing text: reading budget, structure, facts against a source, stock phrases.

With --instructions (skill, agent and rule bodies) or --dart (Dartdoc), check writing rules instead."""
import json
import re
import sys
from pathlib import Path

RATES = {'ru': 160, 'uk': 160, 'en': 190}
DEFAULT_MINUTES = 5
MAX_SENTENCE_WORDS = 25
MAX_PARAGRAPH_SENTENCES = 5
MAX_LIST_ITEMS = 5
USAGE = ('usage: clarify.py check <file> [--lang ru|uk|en] [--source <src>] [--minutes N]\n'
         '       clarify.py check <path>... --instructions|--dart [--lang ru|uk|en] [--words <file>] [--unlisted]\n'
         '       [--summary]')
DEFAULT_WORDS = '~/.claude/ste/words.json'
TECHNICAL_WORDS = Path(__file__).with_name('technical.txt')
VALUE_OPTIONS = {'--lang', '--source', '--minutes', '--words'}
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
FRONT_MATTER_RE = re.compile(r'\A\s*---\n.*?\n---[ \t]*(?=\n|\Z)', re.S)
TABLE_ROW_RE = re.compile(r'^\s*\|')
DOC_LINE_RE = re.compile(r'^\s*/// ?(.*)$')
DART_REFERENCE_RE = re.compile(r'\[[^\]]*\](?:\([^)]*\))?|\{@[^}]*\}')
LINK_TARGET_RE = re.compile(r'\]\([^)]*\)')
IDENTIFIER_RE = re.compile(r'[_/\\.=<>@#$%&\d]|[a-z][A-Z]')
WORD_RE = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")
PASSIVE_RE = re.compile(
    r'(?<!\w)(?:is|are|was|were|be|been)\s+(?:not\s+)?(?!indeed\b)(?:[a-z]{2,}ed|written|done|given|taken|made|sent|built|'
    r'shown|known|seen|found|kept|set|put|run|read|left|held|broken|chosen|drawn|driven|hidden|spoken|begun|'
    r'brought|bought|caught|taught|thought|told|sold|paid|laid|meant|lost|won|got|gotten|split|cut|shut|spent|'
    r'understood|rewritten|overridden)(?!\w)', re.I)
GENERATED_DART_SUFFIXES = ('.g.dart', '.freezed.dart', '.gr.dart', '.config.dart')
NAME_THE_ACTION = 'name the specific action (checks, refreshes, returns, sends)'
NON_VERB_ING = {'thing', 'string', 'during', 'nothing', 'something', 'anything', 'everything'}
WEAK_MODALS = {
    'en': [r'should', r'may', r'might', r'try to'],
    'ru': [r'желательно', r'по возможности'],
    'uk': [r'бажано', r'по можливості'],
}

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
        (r'via', 'through'),
        (r'modif(?:y|ies|ied|ying)', 'change'),
        (r'preserv\w*', 'keep'),
        (r'rapid\w*', 'fast'),
        (r'reveal\w*', 'show'),
        (r'exceed\w*', 'is more than'),
        (r'absent', 'missing'),
        (r'ensur(?:e|es|ed|ing)', NAME_THE_ACTION),
        (r'perform(?:s|ed|ing)?', NAME_THE_ACTION),
        (r'provid(?:e|es|ed|ing)', NAME_THE_ACTION),
        (r'determin(?:e|es|ed|ing)', NAME_THE_ACTION),
        (r'detect(?:s|ed|ing)?', NAME_THE_ACTION),
    ],
}


class Markdown:
    def __init__(self, skip_meta=False):
        self.skip_meta = skip_meta
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
        if self.skip_meta:
            visible = FRONT_MATTER_RE.sub(lambda match: '\n' * match.group(0).count('\n'), visible)
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
        if self.is_break(line):
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

    def is_break(self, line):
        return not line.strip() or (self.skip_meta and TABLE_ROW_RE.match(line))

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
    fields = [('summary', doc.get('summary', ''), True), ('concept', doc.get('concept', ''), True)]
    for index, section in enumerate(doc.get('sections', [])):
        where = f'sections[{index}]'
        fields.append((f'{where}.takeaway', section.get('takeaway', ''), True))
        fields += [(f'{where}.lines[{number}].text', line.get('text', ''), False)
                   for number, line in enumerate(section.get('lines', []))]
        fields.append((f'{where}.check', section.get('check', ''), True))
    owners = [(f'entities[{index}]', entity) for index, entity in enumerate(doc.get('entities', []))]
    owners += [(f'sections[{index}]', section) for index, section in enumerate(doc.get('sections', []))]
    fields += [(f'{where}.files[{file_index}].edits[{edit_index}].text', edit.get('text', ''), False)
               for where, owner in owners
               for file_index, file in enumerate(owner.get('files', []))
               for edit_index, edit in enumerate(file.get('edits', []))]
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
    return [(item['where'], f'consider: «{match.group()}» → {suggestion}')
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

def rule_check(argv):
    lang = option(argv, '--lang')
    lang = 'en' if lang is None else lang
    paths = [Path(arg) for arg in positionals(argv)]
    if not is_valid_rule_options(lang, paths):
        print(USAGE, file=sys.stderr)
        return 2
    dart = '--dart' in argv
    rules = {'lang': lang, 'modals': not dart, 'technical': technical_words(), 'unlisted': '--unlisted' in argv,
             'words': ste_words(Path(option(argv, '--words') or DEFAULT_WORDS).expanduser())}
    findings = []
    for path in files_of(paths, dart):
        findings += rule_findings(rule_blocks(path, dart), rules)
    print_findings(findings, '--summary' in argv)
    print('ok')
    return 0

def is_valid_rule_options(lang, paths):
    return lang in RATES and paths and all(path.exists() for path in paths)

def positionals(argv):
    result = []
    for index, arg in enumerate(argv):
        if arg.startswith('--') or (index > 0 and argv[index - 1] in VALUE_OPTIONS):
            continue
        result.append(arg)
    return result

def technical_words():
    if not TECHNICAL_WORDS.exists():
        return set()
    lines = TECHNICAL_WORDS.read_text(encoding='utf-8').split('\n')
    return {line.split('#', 1)[0].strip().lower() for line in lines} - {''}

def ste_words(path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding='utf-8'))

def files_of(paths, dart):
    for path in paths:
        yield from folder_files(path, dart) if path.is_dir() else [path]

def folder_files(folder, dart):
    if not dart:
        return sorted(path for path in folder.rglob('*.md') if path.is_file())
    return sorted(path for path in folder.rglob('*.dart') if is_hand_written_dart(path))

def is_hand_written_dart(path):
    return path.is_file() and not path.name.endswith(GENERATED_DART_SUFFIXES)

def rule_blocks(path, dart):
    text = path.read_text(encoding='utf-8')
    if dart:
        text = '\n'.join(doc_line(line) for line in text.split('\n'))
    reader = Markdown(skip_meta=True)
    reader.read(text)
    return [block(f'{path}:{paragraph["line"]}', rule_text(' '.join(paragraph['parts']), dart))
            for paragraph in reader.paragraphs]

def doc_line(line):
    match = DOC_LINE_RE.match(line)
    return match.group(1) if match else ''

def rule_text(raw, dart):
    text = LINK_TARGET_RE.sub(']', URL_RE.sub(' ', raw))
    return DART_REFERENCE_RE.sub(' ', text) if dart else text

def rule_findings(blocks, rules):
    prose_blocks = [dict(item, text=without_identifiers(item['text'])) for item in blocks]
    findings = [(where, msg, msg.lower()) for where, msg in phrase_hints(prose_blocks, rules['lang'])]
    modals = [re.compile(rf'(?<!\w){pattern}(?!\w)', re.I) for pattern in WEAK_MODALS[rules['lang']]]
    for item in blocks:
        for sentence in sentences_of(item['text']):
            findings += sentence_findings(item['where'], sentence, rules, modals)
    return findings

def without_identifiers(text):
    return ' '.join(token for token in text.split() if not is_identifier(token))

def is_identifier(token):
    return bool(IDENTIFIER_RE.search(token.strip('.,;:!?()[]{}"\'«»*')))

def sentence_findings(where, sentence, rules, modals):
    findings = []
    count = word_count(sentence)
    if count > MAX_SENTENCE_WORDS:
        findings.append((where, f'sentence of {count} words, limit {MAX_SENTENCE_WORDS}',
                         f'sentence over {MAX_SENTENCE_WORDS} words'))
    if rules['modals']:
        findings += [labelled(where, f'weak modal: {match.group().lower()}')
                     for pattern in modals for match in pattern.finditer(sentence)]
    if rules['lang'] == 'en':
        findings += english_findings(where, sentence, rules)
    return findings

def labelled(where, msg):
    return where, msg, msg

def english_findings(where, sentence, rules):
    findings = [labelled(where, f'passive: {match.group().lower()}') for match in PASSIVE_RE.finditer(sentence)]
    words = prose_words(sentence)
    if not sentence.lstrip().startswith('Whether'):
        findings += [labelled(where, f'-ing form: {word}') for word in words if is_ing_form(word, rules)]
    if rules['words'] is not None:
        hints = [ste_hint(word, rules) for word in words]
        findings += [labelled(where, hint) for hint in hints if hint]
    return findings

def prose_words(sentence):
    words = []
    for token in sentence.split():
        if is_identifier(token):
            continue
        words += [word.lower() for word in WORD_RE.findall(token) if not is_abbreviation(word)]
    return [word[:-2] if word.endswith("'s") else word for word in words]

def is_abbreviation(word):
    return len(word) > 1 and word.isupper()

def is_ing_form(word, rules):
    if len(word) <= 4 or not word.endswith('ing'):
        return False
    approved = rules['words']['approved'] if rules['words'] else {}
    return word not in NON_VERB_ING and word not in approved and word not in rules['technical']

def ste_hint(word, rules):
    for form in word_forms(word):
        if is_known_word(form, rules):
            return None
        if form in rules['words']['unapproved']:
            return f'STE: {word} → {rules["words"]["unapproved"][form]}'
    return f'STE: not in list: {word}' if rules['unlisted'] else None

def is_known_word(form, rules):
    words = rules['words']
    return form in words['approved'] or form in words.get('forms', {}) or form in rules['technical']

def word_forms(word):
    forms = [word]
    for ending, base in (('ies', 'y'), ('ied', 'y'), ('es', ''), ('s', ''), ('ed', ''), ('ed', 'e'),
                         ('ing', ''), ('ing', 'e')):
        if word.endswith(ending) and len(word) > len(ending) + 1:
            forms.append(word[:-len(ending)] + base)
    bases = sorted(dict.fromkeys(forms[1:]), key=len, reverse=True)
    return forms[:1] + bases + [base[:-1] for base in bases if is_doubled(base)]

def is_doubled(form):
    return len(form) > 2 and form[-1] == form[-2] and form[-1] not in 'aeiouls'

def print_findings(findings, summary):
    if not summary:
        for where, msg, _ in findings:
            print(f'{where}: hint: {msg}')
        return
    counts = {}
    for _, _, key in findings:
        counts[key] = counts.get(key, 0) + 1
    for key, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        print(f'hint: {count}× {key}')

def option(argv, name):
    if name not in argv:
        return None
    index = argv.index(name) + 1
    return argv[index] if index < len(argv) else ''

def cli_check(argv):
    if '--instructions' in argv or '--dart' in argv:
        return rule_check(argv)
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
