#!/usr/bin/env python3
"""Check and render plan.md files per the plan format contract."""
import json
import os
import re
import secrets
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

H2_RE = re.compile(r'^## (.+)$')
STEP_RE = re.compile(r'^### S(\d+)\s*·\s*(.+)$')
VERIFY_RE = re.compile(r'→\s*verify:')
FILE_LINE_RE = re.compile(r'[\w./-]+:\d+')
BACKTICK_RE = re.compile(r'`([^`]+)`')
NOTE_RE = re.compile(r'\(\+[^)]*\)')
S_NUM_RE = re.compile(r'S(\d+)')
STAGE_HEADER = ['stage', 'steps', 'depends on', 'gate', 'lane', 'status']
LANES = {'contained', 'wide', 'closed'}
QUOTE_LIMIT = 120
ANCHOR_RE = re.compile(r'^[\w &-]{1,60}$')
COMMENT_RE = re.compile(r'^- \[ \] \[([^\]]+)\] (?:«([^»]*)» )?(?:@([^:]+): )?(.*)$')
OPEN_PREFIX = '- [ ] '
IMPLEMENT_PROMPT = 'имплементируй план {} используй субагентов'
GHOSTTY_SCRIPT = '''on run argv
    tell application "Ghostty"
        set config to new surface configuration
        set initial working directory of config to item 1 of argv
        set command of config to item 2 of argv
        new window with configuration config
        activate
    end tell
end run'''
TERMINAL_SCRIPT = '''on run argv
    set wasRunning to application "Terminal" is running
    tell application "Terminal"
        if wasRunning then
            do script item 1 of argv
        else
            do script item 1 of argv in window 1
        end if
        activate
    end tell
end run'''
DEFAULT_PORT = 8790
COMMENTS_LOCK = threading.Lock()
IMPLEMENT_LOCK = threading.Lock()
DICTATION_APP = Path.home() / 'Library' / 'Caches' / 'make-plan' / 'PlanDictation.app'
DICTATION_TIMEOUT = 120
DICTATION_ROUTE_RE = re.compile(r'^/dictation/(?:start|([0-9a-f]+)/(audio|stop))$')
DICTATION_CONNECT_TIMEOUT = 10
DICTATION_IDLE_LIMIT = 20
DICTATION_FINAL_WAIT = 10
DICTATION_SESSIONS = {}
DICTATION_ERRORS = {
    3: 'Системное распознавание русской речи недоступно — включи Диктовку в Системных настройках → Клавиатура.',
    4: 'Разреши распознавание речи для PlanDictation: Системные настройки → Конфиденциальность и безопасность → Распознавание речи.',
}
POINT_RE = re.compile(r'^### (\d+)\.\s*(.+)$')
POINT_STEPS_RE = re.compile(r'^<!--\s*((?:S\d+\s*)+)-->$')
CHECK_PREFIX = 'Проверим:'
DECISION_RE = re.compile(r'^### Вопрос (\d+)\s*·\s*(.+)$')
OPTION_RE = re.compile(r'^- (\w)\s*·\s*(.+)$')
RECOMMEND_PREFIX = 'Рекомендую:'
NODE_RE = re.compile(r'^(\w+)\["([^"]*)"\](?::::(\w+))?$')
EDGE_RE = re.compile(r'^(\w+)\s*-->\s*(?:\|([^|]*)\|\s*)?(\w+)$')
NODE_CLASSES = {'new', 'changed', 'same'}
NAME_SPAN_RE = re.compile(r'^[\w.-]+$')
LOCATION_RE = re.compile(r'\w:\d+')
CITATION_RE = re.compile(r'(?<![\w./:~-])([\w.-][\w./-]*):(\d+)(?:-(\d+))?')
VISIBLE_STEP_RE = re.compile(r'\bS\d+\b')
MAX_NODES = 8
MAX_EDGES = 10
MAX_NODE_LABEL = 40
MAX_EDGE_LABEL_WORDS = 3
MAX_POINTS = 5
MAX_POINT_TEXT = 600

def unfenced(lines):
    out = []
    in_fence = False
    for i, line in enumerate(lines, start=1):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((i, line))
    return out

def parse_front_matter(lines):
    if not lines or lines[0].strip() != '---':
        return {}, {}, 0
    data, data_lines = {}, {}
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return data, data_lines, i + 1
        if ':' in lines[i]:
            key, value = lines[i].split(':', 1)
            data[key.strip()] = value.strip()
            data_lines[key.strip()] = i + 1
    return {}, {}, 0

def h2_sections(uf):
    sections = {}
    current = None
    for ln, line in uf:
        m = H2_RE.match(line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append((ln, line))
    return sections

def find_steps(uf):
    steps = []
    for ln, line in uf:
        m = STEP_RE.match(line)
        if m:
            steps.append((ln, int(m.group(1)), m.group(2).strip()))
    return steps

def split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

def find_tables(uf, header):
    tables = []
    n = len(uf)
    for i in range(n):
        ln, line = uf[i]
        if not line.strip().startswith('|'):
            continue
        if [c.lower() for c in split_row(line)] != header:
            continue
        rows = []
        j = i + 2
        while j < n and uf[j][1].strip().startswith('|'):
            rows.append((uf[j][0], split_row(uf[j][1])))
            j += 1
        tables.append((ln, rows))
    return tables

def resolve_root(plan_path, root_arg):
    if root_arg:
        return Path(root_arg).resolve()
    plan_dir = plan_path.resolve().parent
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=plan_dir, capture_output=True, text=True,
        )
    except OSError:
        return plan_dir
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return plan_dir

def missing_section_problems(sections):
    return [
        (1, f"missing required section '## {name}'")
        for name in ('Context', 'Steps', 'Verification')
        if name not in sections
    ]

def step_verify_problems(steps, uf):
    headings = [ln for ln, line in uf if line.startswith('#')]
    problems = []
    for ln, sid, _ in steps:
        end = next((h for h in headings if h > ln), None)
        limit = end if end is not None else (uf[-1][0] + 1 if uf else ln + 1)
        has_verify = any(VERIFY_RE.search(line) for l2, line in uf if ln < l2 < limit)
        if not has_verify:
            problems.append((ln, f"S{sid} missing '→ verify:' before next heading"))
    return problems

def sequence_problems(steps):
    problems = []
    expected = 1
    for ln, sid, _ in steps:
        if sid != expected:
            problems.append((ln, f"step id S{sid} out of sequence (expected S{expected})"))
        expected = sid + 1
    return problems

def path_problems(uf, root):
    problems = []
    for _, rows in find_tables(uf, ['path', 'change']):
        for ln, cells in rows:
            if len(cells) < 1:
                continue
            cell = NOTE_RE.sub('', cells[0]).strip()
            for part in cell.split(','):
                part = part.strip()
                m = BACKTICK_RE.search(part)
                if not m:
                    continue
                path_str = m.group(1)
                if '(new)' in part:
                    continue
                if not (root / path_str).exists():
                    problems.append((ln, f"path does not exist under root: {path_str}"))
    return problems

def citation_roots(root, front_matter):
    if not (root / '.git').exists():
        return []
    worktree = root / front_matter.get('worktree', '')
    if front_matter.get('worktree') and worktree.is_dir():
        return [worktree, root]
    return [root]

def citation_problems(uf, roots):
    problems = []
    for ln, line in uf:
        for m in CITATION_RE.finditer(line):
            path_str, last = m.group(1), int(m.group(3) or m.group(2))
            if not any((r / path_str.split('/')[0]).exists() for r in roots):
                continue
            target = next((r / path_str for r in roots if (r / path_str).is_file()), None)
            if target is None:
                problems.append((ln, f"cited file does not exist under root: {path_str} (a new file has no lines to cite)"))
                continue
            count = len(target.read_text(encoding='utf-8', errors='replace').splitlines())
            if last > count:
                problems.append((ln, f"citation {m.group(0)} past end of {path_str} ({count} lines)"))
    return problems

def assumption_problems(section_lines):
    problems = []
    bullets = []
    current = None
    for ln, line in section_lines:
        if line.startswith('- '):
            current = [ln, line[2:]]
            bullets.append(current)
        elif current is not None and line.strip():
            current[1] += ' ' + line.strip()
    for ln, text in bullets:
        if not (FILE_LINE_RE.search(text) or 'verify:' in text):
            problems.append((ln, 'assumption bullet missing file:line or verify:'))
    return problems

def stage_problems(uf, step_ids):
    problems = []
    for _, rows in find_tables(uf, STAGE_HEADER):
        for ln, cells in rows:
            if len(cells) != 6:
                problems.append((ln, 'malformed stages row'))
                continue
            stage, steps_cell, depends, gate, lane, status = cells
            if depends not in ('—', '-', '') and '`' not in depends:
                problems.append((ln, f"stage {stage}: dependency without backticked artifact"))
            if not gate:
                problems.append((ln, f"stage {stage}: empty gate"))
            if lane not in LANES:
                problems.append((ln, f"stage {stage}: lane '{lane}' not in contained|wide|closed"))
            for num in S_NUM_RE.findall(steps_cell):
                if int(num) not in step_ids:
                    problems.append((ln, f"stage {stage}: refers to unknown step S{num}"))
    return problems

def front_matter_problems(front_matter, fm_lines):
    lane = front_matter.get('lane')
    if lane is not None and lane not in LANES:
        return [(fm_lines.get('lane', 1), f"front matter lane '{lane}' not in contained|wide|closed")]
    return []

def check_plan(plan_path, root):
    lines = plan_path.read_text(encoding='utf-8').splitlines()
    front_matter, fm_lines, _ = parse_front_matter(lines)
    uf = unfenced(lines)
    sections = h2_sections(uf)
    steps = find_steps(uf)
    step_ids = {sid for _, sid, _ in steps}
    problems = []
    problems += missing_section_problems(sections)
    problems += step_verify_problems(steps, uf)
    problems += sequence_problems(steps)
    problems += path_problems(uf, root)
    problems += citation_problems(uf, citation_roots(root, front_matter))
    if 'Assumptions & Evidence' in sections:
        problems += assumption_problems(sections['Assumptions & Evidence'])
    problems += stage_problems(uf, step_ids)
    problems += front_matter_problems(front_matter, fm_lines)
    tagged = [(plan_path, ln, msg) for ln, msg in sorted(problems, key=lambda p: p[0])]
    _, _, brief_path = output_paths(plan_path)
    if not brief_path.exists():
        return tagged
    brief_lines = brief_path.read_text(encoding='utf-8').splitlines()
    brief_issues = brief_problems(brief_lines, parse_brief(brief_lines), step_ids)
    return tagged + [(brief_path, ln, msg) for ln, msg in sorted(brief_issues, key=lambda p: p[0])]

def parse_diagram(section_lines):
    fence = [ln for ln, line in section_lines if line.strip().startswith('```')]
    if len(fence) < 2:
        return None
    start, end = fence[0], fence[1]
    body = [(ln, line.strip()) for ln, line in section_lines if start < ln < end and line.strip()]
    return {'line': start, 'source': '\n'.join(line for _, line in body), 'lines': body}

def parse_points(section_lines):
    points = []
    current = None
    for ln, line in section_lines:
        m = POINT_RE.match(line)
        if m:
            current = {'n': int(m.group(1)), 'title': m.group(2).strip(), 'line': ln,
                       'steps': [], 'text': '', 'check': ''}
            points.append(current)
            continue
        if current is None or not line.strip():
            continue
        steps = POINT_STEPS_RE.match(line.strip())
        if steps:
            current['steps'] = [int(s[1:]) for s in steps.group(1).split()]
        elif line.startswith(CHECK_PREFIX):
            current['check'] = line[len(CHECK_PREFIX):].strip()
        else:
            current['text'] = f"{current['text']} {line.strip()}".strip()
    return points

def parse_decisions(section_lines):
    decisions = []
    current = None
    for ln, line in section_lines:
        m = DECISION_RE.match(line)
        if m:
            current = {'n': int(m.group(1)), 'question': m.group(2).strip(), 'line': ln,
                       'options': [], 'recommendation': ''}
            decisions.append(current)
            continue
        if current is None:
            continue
        option = OPTION_RE.match(line)
        if option:
            current['options'].append({'key': option.group(1), 'text': option.group(2).strip()})
        elif line.startswith(RECOMMEND_PREFIX):
            current['recommendation'] = line[len(RECOMMEND_PREFIX):].strip()
    return decisions

def parse_brief(lines):
    sections = h2_sections(list(enumerate(lines, start=1)))
    diagram = parse_diagram(sections['Схема']) if 'Схема' in sections else None
    return {
        'diagram': diagram['source'] if diagram else '',
        'diagramLine': diagram['line'] if diagram else 0,
        'diagramLines': diagram['lines'] if diagram else [],
        'points': parse_points(sections.get('Что сделаем', [])),
        'decisions': parse_decisions(sections.get('Решения', [])),
    }

def brief_problems(lines, brief, plan_step_ids):
    problems = []
    nodes = {}
    problems += diagram_problems(brief, nodes)
    problems += point_problems(brief['points'], plan_step_ids, nodes)
    problems += decision_problems(brief['decisions'])
    problems += plain_word_problems(lines, brief)
    return problems

def diagram_problems(brief, nodes):
    body = brief['diagramLines']
    if not body:
        return [(1, "missing '## Схема' with a mermaid block")]
    head_ln, head = body[0]
    problems = [] if head == 'flowchart TD' else [(head_ln, "diagram must start with 'flowchart TD'")]
    edges = []
    for ln, line in body[1:]:
        node = NODE_RE.match(line)
        edge = EDGE_RE.match(line)
        if node:
            nodes[node.group(1)] = node.group(2)
            problems += node_problems(ln, node.group(2), node.group(3))
        elif edge:
            edges.append((ln, edge.group(1), edge.group(3)))
            problems += edge_label_problems(ln, edge.group(2))
        else:
            problems.append((ln, 'diagram line is neither a node \'id["label"]:::class\' nor an arrow \'a --> b\''))
    if len(nodes) > MAX_NODES:
        problems.append((head_ln, f'diagram has {len(nodes)} nodes, limit {MAX_NODES}'))
    if len(edges) > MAX_EDGES:
        problems.append((head_ln, f'diagram has {len(edges)} arrows, limit {MAX_EDGES}'))
    for ln, source, target in edges:
        for end in (source, target):
            if end not in nodes:
                problems.append((ln, f"arrow end '{end}' is not a declared node"))
    return problems

def node_problems(ln, label, node_class):
    problems = []
    if node_class not in NODE_CLASSES:
        problems.append((ln, 'node without :::new, :::changed or :::same'))
    parts = label.split('<br/>')
    if len(parts) > 2 or len(''.join(parts)) > MAX_NODE_LABEL:
        problems.append((ln, f'node label over 2 lines or {MAX_NODE_LABEL} chars'))
    return problems

def edge_label_problems(ln, label):
    if label and len(label.split()) > MAX_EDGE_LABEL_WORDS:
        return [(ln, f'arrow label over {MAX_EDGE_LABEL_WORDS} words')]
    return []

def point_problems(points, plan_step_ids, nodes):
    problems = []
    if not points:
        problems.append((1, "missing '## Что сделаем' with '### <n>. <title>' points"))
    if len(points) > MAX_POINTS:
        problems.append((points[MAX_POINTS]['line'], f'more than {MAX_POINTS} points'))
    code_names = {label.split('<br/>')[-1].strip() for label in nodes.values()}
    covered = {}
    for point in points:
        problems += single_point_problems(point, code_names)
        for sid in point['steps']:
            covered.setdefault(sid, []).append(point['line'])
    for sid in sorted(plan_step_ids):
        if len(covered.get(sid, [])) != 1:
            problems.append((1, f'plan step S{sid} must belong to exactly one point'))
    for sid in sorted(set(covered) - plan_step_ids):
        problems.append((covered[sid][0], f'point refers to unknown step S{sid}'))
    return problems

def single_point_problems(point, code_names):
    ln = point['line']
    problems = []
    if not point['steps']:
        problems.append((ln, f"point {point['n']}: missing '<!-- S1 S2 -->' step comment"))
    if not point['check']:
        problems.append((ln, f"point {point['n']}: missing '{CHECK_PREFIX}' line"))
    if len(point['text']) > MAX_POINT_TEXT:
        problems.append((ln, f"point {point['n']}: text over {MAX_POINT_TEXT} chars"))
    names = BACKTICK_RE.findall(point['text'])
    if not code_names.intersection(names):
        problems.append((ln, f"point {point['n']}: names no `entity` shown on the diagram"))
    return problems

def decision_problems(decisions):
    problems = []
    for decision in decisions:
        if len(decision['options']) < 2:
            problems.append((decision['line'], f"question {decision['n']}: fewer than two options"))
        if not decision['recommendation']:
            problems.append((decision['line'], f"question {decision['n']}: missing '{RECOMMEND_PREFIX}'"))
    return problems

def plain_word_problems(lines, brief):
    diagram_lines = {ln for ln, _ in brief['diagramLines']}
    problems = []
    for ln, line in enumerate(lines, start=1):
        if ln in diagram_lines or line.strip().startswith('```') or POINT_STEPS_RE.match(line.strip()):
            continue
        problems += plain_line_problems(ln, line)
    return problems

def plain_line_problems(ln, line):
    problems = []
    if any('/' in token for token in line.split()) or LOCATION_RE.search(line):
        problems.append((ln, 'path or file:line in the brief'))
    if any(not NAME_SPAN_RE.match(span) for span in BACKTICK_RE.findall(line)):
        problems.append((ln, 'backticks hold more than one name'))
    if VISIBLE_STEP_RE.search(line):
        problems.append((ln, 'step id visible to the reader'))
    return problems

def extract_title(body_lines):
    for line in unfenced(body_lines):
        _, text = line
        if text.startswith('# '):
            return text[2:].strip()
    return None

def output_paths(plan_path):
    if plan_path.name == 'plan.md':
        return plan_path.parent / 'comments.md', plan_path.parent / 'plan.html', plan_path.parent / 'brief.md'
    stem = plan_path.stem
    return (plan_path.parent / f'{stem}.comments.md', plan_path.parent / f'{stem}.html',
            plan_path.parent / f'{stem}.brief.md')

def plan_version(plan_path):
    comments_path, _, brief_path = output_paths(plan_path)
    stats = [path.stat() for path in (plan_path, brief_path, comments_path) if path.exists()]
    return '-'.join(f'{stat.st_mtime_ns}.{stat.st_size}' for stat in stats)

def build_html(plan_path, server, revising=False):
    lines = plan_path.read_text(encoding='utf-8').splitlines()
    front_matter, _, body_start = parse_front_matter(lines)
    body_lines = lines[body_start:]
    comments_path, _, brief_path = output_paths(plan_path)
    comments = comments_path.read_text(encoding='utf-8') if comments_path.exists() else ''
    brief = parse_brief(brief_path.read_text(encoding='utf-8').splitlines()) if brief_path.exists() else None
    data = {
        'title': extract_title(body_lines) or plan_path.stem,
        'frontMatter': front_matter,
        'markdown': '\n'.join(body_lines),
        'brief': brief,
        'comments': comments,
        'server': server,
        'planId': str(plan_path.resolve()) if server else '',
        'version': plan_version(plan_path) if server else '',
        'revising': revising,
    }
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    template_path = Path(__file__).resolve().parent / 'viewer.html'
    return template_path.read_text(encoding='utf-8').replace('__PLAN_DATA__', payload)

def render_plan(plan_path, out_arg):
    _, default_out, _ = output_paths(plan_path)
    out_path = Path(out_arg) if out_arg else default_out
    out_path.write_text(build_html(plan_path, server=False), encoding='utf-8')
    write_launcher(plan_path)
    return out_path

def write_launcher(plan_path):
    launcher = plan_path.parent / f'open-{plan_path.stem}.command'
    tool = Path(__file__).resolve()
    launcher.write_text(
        '#!/bin/sh\n'
        'cd "$(dirname "$0")"\n'
        f'python3 "{tool}" serve "{plan_path.name}"\n',
        encoding='utf-8',
    )
    launcher.chmod(0o755)

def comment_line(anchor, quote, author, text):
    quote_part = f'«{quote}» ' if quote else ''
    author_part = f'@{author}: ' if author else ''
    return f'- [ ] [{anchor}] {quote_part}{author_part}{text}'

def append_comment(plan_path, payload):
    with COMMENTS_LOCK:
        return append_comment_locked(plan_path, payload)

def append_comment_locked(plan_path, payload):
    anchor = str(payload.get('anchor', '')).strip()
    author = ' '.join(str(payload.get('author', '')).replace(':', ' ').split())
    text = ' '.join(str(payload.get('text', '')).split())
    quote = ' '.join(str(payload.get('quote', '')).replace('«', '"').replace('»', '"').split())[:QUOTE_LIMIT + 1]
    if not ANCHOR_RE.match(anchor) or not text:
        return None
    comments_path, _, _ = output_paths(plan_path)
    existing = comments_path.read_text(encoding='utf-8') if comments_path.exists() else ''
    separator = '' if not existing or existing.endswith('\n') else '\n'
    line = comment_line(anchor, quote, author, text)
    comments_path.write_text(f'{existing}{separator}{line}\n', encoding='utf-8')
    return line

def edit_comment(plan_path, payload):
    with COMMENTS_LOCK:
        return edit_comment_locked(plan_path, payload)

def edit_comment_locked(plan_path, payload):
    text = ' '.join(str(payload.get('text', '')).split())
    if not text:
        return None
    comments_path, lines, index = find_open_comment(plan_path, payload)
    if index is None:
        return None
    anchor, quote, author, _ = COMMENT_RE.match(lines[index]).groups()
    lines[index] = comment_line(anchor, quote, author, text)
    comments_path.write_text(''.join(f'{line}\n' for line in lines), encoding='utf-8')
    return lines[index]

def delete_comment(plan_path, payload):
    with COMMENTS_LOCK:
        return delete_comment_locked(plan_path, payload)

def delete_comment_locked(plan_path, payload):
    comments_path, lines, index = find_open_comment(plan_path, payload)
    if index is None:
        return False
    end = index + 1
    while end < len(lines) and lines[end].startswith('  '):
        end += 1
    del lines[index:end]
    comments_path.write_text(''.join(f'{line}\n' for line in lines), encoding='utf-8')
    return True

def find_open_comment(plan_path, payload):
    comments_path, _, _ = output_paths(plan_path)
    target = str(payload.get('line', ''))
    lines = comments_path.read_text(encoding='utf-8').splitlines() if comments_path.exists() else []
    if not COMMENT_RE.match(target) or target not in lines:
        return comments_path, lines, None
    return comments_path, lines, lines.index(target)

def implement_session(plan_path):
    plan_dir = plan_path.resolve().parent
    in_plan_folder = plan_dir.parent.name == 'plan'
    root = plan_dir.parent.parent if in_plan_folder else plan_dir
    target = plan_dir.relative_to(root) if in_plan_folder else plan_path.name
    return root, f'claude {shlex.quote(IMPLEMENT_PROMPT.format(target))}'

def launch_implement(plan_path):
    root, session = implement_session(plan_path)
    if launch_ghostty(root, session):
        return None
    if run_osascript(TERMINAL_SCRIPT, f'cd {shlex.quote(str(root))} && {session}'):
        return None
    return 'не удалось открыть терминал — запусти implement-plan сам'

def launch_ghostty(root, session):
    if subprocess.run(['open', '-Ra', 'Ghostty'], capture_output=True).returncode != 0:
        return False
    command = shlex.join(['/bin/zsh', '-ilc', f'{session}; exec /bin/zsh -il'])
    return run_osascript(GHOSTTY_SCRIPT, str(root), command)

def run_osascript(script, *args):
    # A cold-started terminal app inherits this env; Claude's CLAUDE_CODE_CHILD_SESSION marker
    # would then disable transcript saving for every claude launched in it.
    env = {key: value for key, value in os.environ.items() if not key.startswith('CLAUDE')}
    return subprocess.run(['osascript', '-e', script, *args], capture_output=True, env=env).returncode == 0

def make_handler(plan_path):
    class PlanHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/alive':
                state = {'plan': str(plan_path.resolve()), 'version': plan_version(plan_path),
                         'revising': self.server.revising}
                self.reply(200, 'application/json', json.dumps(state))
                return
            if self.path not in ('/', '/index.html'):
                self.send_error(404)
                return
            self.reply(200, 'text/html; charset=utf-8', build_html(plan_path, server=True, revising=self.server.revising))

        def do_POST(self):
            if self.path == '/submit':
                self.server.submitted = open_comment_count(plan_path)
                self.reply(200, 'application/json', json.dumps({'open': self.server.submitted}))
                threading.Thread(target=self.server.shutdown).start()
                return
            if self.path == '/revised':
                self.server.revising = False
                self.reply(200, 'application/json', json.dumps({'ok': True}))
                return
            if self.path == '/transcribe':
                length = int(self.headers.get('Content-Length', 0))
                result = transcribe(self.rfile.read(length))
                self.reply(200 if 'text' in result else 500, 'application/json', json.dumps(result, ensure_ascii=False))
                return
            if DICTATION_ROUTE_RE.match(self.path):
                self.dictation()
                return
            if self.path == '/implement':
                self.implement()
                return
            if self.path == '/comments/edit':
                line = edit_comment(plan_path, self.read_payload())
                if line is None:
                    self.reply(400, 'text/plain; charset=utf-8', 'comment not found')
                    return
                self.reply(200, 'application/json', json.dumps({'line': line}, ensure_ascii=False))
                return
            if self.path == '/comments/delete':
                if not delete_comment(plan_path, self.read_payload()):
                    self.reply(400, 'text/plain; charset=utf-8', 'comment not found')
                    return
                self.reply(200, 'application/json', json.dumps({'ok': True}))
                return
            if self.path != '/comments':
                self.send_error(404)
                return
            line = append_comment(plan_path, self.read_payload())
            if line is None:
                self.reply(400, 'text/plain; charset=utf-8', 'anchor and text are required')
                return
            self.reply(200, 'application/json', json.dumps({'line': line}, ensure_ascii=False))

        def dictation(self):
            session_id, action = DICTATION_ROUTE_RE.match(self.path).groups()
            if session_id is None:
                result = start_dictation()
            elif action == 'audio':
                result = feed_dictation(session_id, self.rfile.read(int(self.headers.get('Content-Length', 0))))
            else:
                result = stop_dictation(session_id)
            self.reply(500 if 'error' in result else 200, 'application/json', json.dumps(result, ensure_ascii=False))

        def implement(self):
            with IMPLEMENT_LOCK:
                self.implement_once()

        def implement_once(self):
            if self.server.implementing:
                self.reply(409, 'application/json', json.dumps({'open': 0}))
                return
            count = open_comment_count(plan_path)
            if count > 0:
                self.reply(409, 'application/json', json.dumps({'open': count}))
                return
            error = launch_implement(plan_path)
            if error:
                self.reply(500, 'application/json', json.dumps({'error': error}, ensure_ascii=False))
                return
            self.server.implementing = True
            self.reply(200, 'application/json', json.dumps({'started': True}))
            threading.Thread(target=self.server.shutdown).start()

        def read_payload(self):
            length = int(self.headers.get('Content-Length', 0))
            try:
                return json.loads(self.rfile.read(length) or b'{}')
            except json.JSONDecodeError:
                return {}

        def reply(self, status, content_type, body):
            data = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return PlanHandler

def dictation_binary():
    source_dir = Path(__file__).resolve().parent
    source = source_dir / 'dictation.swift'
    binary = DICTATION_APP / 'Contents' / 'MacOS' / 'PlanDictation'
    if binary.exists() and binary.stat().st_mtime >= source.stat().st_mtime:
        return binary
    binary.parent.mkdir(parents=True, exist_ok=True)
    (DICTATION_APP / 'Contents' / 'Info.plist').write_bytes((source_dir / 'dictation.plist').read_bytes())
    subprocess.run(['swiftc', '-O', str(source), '-o', str(binary)], check=True, capture_output=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(DICTATION_APP)], check=True, capture_output=True)
    return binary

def transcribe(audio):
    try:
        dictation_binary()
    except (OSError, subprocess.CalledProcessError):
        return {'error': 'Не удалось собрать распознаватель: нужен macOS с Xcode Command Line Tools (swiftc).'}
    with tempfile.TemporaryDirectory() as tmp:
        wav, out, err = Path(tmp, 'speech.wav'), Path(tmp, 'out.txt'), Path(tmp, 'err.txt')
        wav.write_bytes(audio)
        # `open` makes PlanDictation its own TCC-responsible process, so macOS asks it for speech permission.
        command = ['open', '-W', '-n', str(DICTATION_APP), '--stdout', str(out), '--stderr', str(err), '--args', str(wav)]
        try:
            subprocess.run(command, timeout=DICTATION_TIMEOUT, check=False)
        except subprocess.TimeoutExpired:
            return {'error': 'Распознавание не ответило — проверь системный запрос разрешения.'}
        text = out.read_text(encoding='utf-8').strip() if out.exists() else ''
        if text:
            return {'text': text}
        message = err.read_text(encoding='utf-8').strip() if err.exists() else ''
        return {'error': dictation_error_text(message or 'No speech')}

def dictation_error_text(message):
    if 'not authorized' in message:
        return DICTATION_ERRORS[4]
    if 'unavailable' in message:
        return DICTATION_ERRORS[3]
    if 'No speech' in message:
        return 'Речь не распознана — говори чуть громче и ближе к микрофону.'
    return f'Распознавание не удалось: {message or "пустой результат"}'

class DictationSession:
    """One streaming PlanDictation run: PCM goes in through a FIFO, JSON events come back through another."""

    def __init__(self):
        self.id = secrets.token_hex(8)
        self.dir = Path(tempfile.mkdtemp(prefix='plan-dictation-'))
        self.audio_fifo, self.events_fifo, self.stderr_path = self.dir / 'audio', self.dir / 'events', self.dir / 'stderr'
        os.mkfifo(self.audio_fifo)
        os.mkfifo(self.events_fifo)
        self.text, self.final, self.error, self.pid, self.writer = '', None, None, None, None
        self.closed = False
        self.last_audio = time.monotonic()
        self.changed = threading.Condition()
        command = ['open', '-W', '-n', str(DICTATION_APP), '--stdin', str(self.audio_fifo),
                   '--stdout', str(self.events_fifo), '--stderr', str(self.stderr_path), '--args', '--stream']
        self.launcher = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        threading.Thread(target=self.read_events, daemon=True).start()

    def connect(self):
        deadline = time.monotonic() + DICTATION_CONNECT_TIMEOUT
        while time.monotonic() < deadline:
            try:
                fd = os.open(self.audio_fifo, os.O_WRONLY | os.O_NONBLOCK)
            except OSError:
                time.sleep(0.05)
                continue
            os.set_blocking(fd, True)
            self.writer = os.fdopen(fd, 'wb', buffering=0)
            threading.Thread(target=self.watch_idle, daemon=True).start()
            return True
        return False

    def read_events(self):
        with open(self.events_fifo, encoding='utf-8') as events:
            for line in events:
                try:
                    self.apply(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if self.final is None and self.error is None:
            message = self.stderr_path.read_text(encoding='utf-8').strip() if self.stderr_path.exists() else ''
            self.apply({'error': message})

    def apply(self, event):
        with self.changed:
            self.pid = int(event['pid']) if 'pid' in event else self.pid
            self.text = event.get('partial', self.text)
            if 'final' in event:
                self.text = self.final = event['final']
            if 'error' in event:
                self.error = event['error']
            self.changed.notify_all()

    def feed(self, audio):
        try:
            self.writer.write(audio)
        except (OSError, ValueError):
            return False
        self.last_audio = time.monotonic()
        return True

    def end_audio(self):
        if self.writer and not self.writer.closed:
            self.writer.close()

    def wait_result(self):
        with self.changed:
            self.changed.wait_for(lambda: self.final is not None or self.error is not None, DICTATION_FINAL_WAIT)
        return self.final, self.error

    def watch_idle(self):
        while self.final is None and self.error is None:
            time.sleep(1)
            if time.monotonic() - self.last_audio > DICTATION_IDLE_LIMIT:
                self.close()
                return

    def close(self):
        with self.changed:
            if self.closed:
                return
            self.closed = True
        DICTATION_SESSIONS.pop(self.id, None)
        self.end_audio()
        if self.pid and self.final is None:
            try:
                os.kill(self.pid, 15)
            except OSError:
                pass
        self.unblock_reader()
        self.launcher.kill()
        shutil.rmtree(self.dir, ignore_errors=True)

    def unblock_reader(self):
        try:
            os.close(os.open(self.events_fifo, os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass

def start_dictation():
    try:
        dictation_binary()
    except (OSError, subprocess.CalledProcessError):
        return {'error': 'Не удалось собрать распознаватель: нужен macOS с Xcode Command Line Tools (swiftc).'}
    session = DictationSession()
    if not session.connect():
        session.close()
        return {'error': 'Распознаватель не запустился — проверь системный запрос разрешения.'}
    DICTATION_SESSIONS[session.id] = session
    return {'id': session.id}

def feed_dictation(session_id, audio):
    session = DICTATION_SESSIONS.get(session_id)
    if session is None or not session.feed(audio):
        return {'error': 'Поток распознавания прервался.'}
    if session.error is not None:
        return {'error': dictation_error_text(session.error)}
    return {'text': session.text}

def stop_dictation(session_id):
    session = DICTATION_SESSIONS.get(session_id)
    if session is None:
        return {'error': 'Поток распознавания прервался.'}
    session.end_audio()
    final, error = session.wait_result()
    session.close()
    if final is not None:
        return {'text': final}
    return {'error': dictation_error_text(error or '')}

def open_comment_count(plan_path):
    comments_path, _, _ = output_paths(plan_path)
    if not comments_path.exists():
        return 0
    return sum(1 for line in comments_path.read_text(encoding='utf-8').splitlines() if line.startswith(OPEN_PREFIX))

def cli_check(argv):
    plan_path = Path(argv[0])
    root_arg = argv[argv.index('--root') + 1] if '--root' in argv else None
    root = resolve_root(plan_path, root_arg)
    problems = check_plan(plan_path, root)
    if not problems:
        print('ok')
        return 0
    for path, ln, msg in problems:
        print(f'{path}:{ln}: {msg}')
    return 1

def cli_render(argv):
    plan_path = Path(argv[0])
    out_arg = argv[argv.index('-o') + 1] if '-o' in argv else None
    out_path = render_plan(plan_path, out_arg)
    print(out_path)
    return 0

def port_answers(port):
    # macOS lets 127.0.0.1 bind next to a wildcard listener on the same port, so bind alone misses it.
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.3):
            return True
    except OSError:
        return False

def cli_serve(argv):
    plan_path = Path(argv[0]).resolve()
    if plan_path.is_dir():
        plan_path = plan_path / 'plan.md'
    port = int(argv[argv.index('--port') + 1]) if '--port' in argv else DEFAULT_PORT
    try:
        if port_answers(port):
            raise OSError(port)
        server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(plan_path))
    except OSError:
        print(f'port {port} busy — stop the other serve or pass --port', file=sys.stderr)
        return 2
    server.submitted = None
    server.implementing = False
    server.revising = '--revising' in argv
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(url, flush=True)
    if '--no-open' not in argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    if server.implementing:
        print('implementation started', flush=True)
    elif server.submitted is not None:
        print(f'review submitted: {server.submitted} open comments', flush=True)
        print('Если агент не подхватил ревью сам, напиши ему: доработай план по комментариям', flush=True)
    return 0

def cli_revised(argv):
    port = int(argv[argv.index('--port') + 1]) if '--port' in argv else DEFAULT_PORT
    request = urllib.request.Request(f'http://127.0.0.1:{port}/revised', method='POST')
    try:
        urllib.request.urlopen(request, timeout=2).close()
    except OSError:
        print(f'no serve on port {port} — start it again: serve <plan.md> --no-open', file=sys.stderr)
        return 1
    print('ok')
    return 0

def main(argv):
    if len(argv) < 2:
        print('usage: plan_tool.py check|render|serve|revised <plan.md> [options]', file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == 'check':
        return cli_check(rest)
    if cmd == 'render':
        return cli_render(rest)
    if cmd == 'serve':
        return cli_serve(rest)
    if cmd == 'revised':
        return cli_revised(rest)
    print(f'unknown command: {cmd}', file=sys.stderr)
    return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
