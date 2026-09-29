#!/usr/bin/env python3
"""Check and render plan.md files per the plan format contract."""
import json
import re
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

H2_RE = re.compile(r'^## (.+)$')
STEP_RE = re.compile(r'^### S(\d+)\s*·\s*(.+)$')
VERIFY_RE = re.compile(r'→\s*verify:')
FILE_LINE_RE = re.compile(r'[\w./-]+:\d+')
BACKTICK_RE = re.compile(r'`([^`]+)`')
NOTE_RE = re.compile(r'\(\+[^)]*\)')
DEP_RE = re.compile(r'(\d+)\s*\(`([^`]+)`\)')
S_NUM_RE = re.compile(r'S(\d+)')
STAGE_HEADER = ['stage', 'steps', 'depends on', 'gate', 'lane', 'status']
LANES = {'contained', 'wide', 'closed'}
QUOTE_LIMIT = 120
ANCHOR_RE = re.compile(r'^[\w &-]{1,60}$')

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
    if 'Assumptions & Evidence' in sections:
        problems += assumption_problems(sections['Assumptions & Evidence'])
    problems += stage_problems(uf, step_ids)
    problems += front_matter_problems(front_matter, fm_lines)
    return sorted(problems, key=lambda p: p[0])

def extract_title(body_lines):
    for line in unfenced(body_lines):
        _, text = line
        if text.startswith('# '):
            return text[2:].strip()
    return None

def build_stages_mermaid(uf):
    tables = find_tables(uf, STAGE_HEADER)
    if not tables:
        return None
    _, rows = tables[0]
    valid_rows = [(ln, cells) for ln, cells in rows if len(cells) == 6]
    if not valid_rows:
        return None
    out = ['flowchart LR']
    for _, cells in valid_rows:
        stage, _, _, _, lane, _ = cells
        out.append(f'    T{stage}["T{stage} · {lane}"]')
    for _, cells in valid_rows:
        stage, _, depends, _, _, _ = cells
        for dep_stage, artifact in DEP_RE.findall(depends):
            out.append(f'    T{dep_stage} -->|{artifact}| T{stage}')
    return '\n'.join(out)

def inject_stages_diagram(body_lines):
    uf = unfenced(body_lines)
    stages_idx = next((i for i, (_, line) in enumerate(uf) if line.strip() == '## Stages'), None)
    if stages_idx is None:
        return '\n'.join(body_lines)
    mermaid = build_stages_mermaid(uf)
    if mermaid is None:
        return '\n'.join(body_lines)
    heading_lineno = uf[stages_idx][0]
    block = ['', '```mermaid', mermaid, '```']
    new_lines = body_lines[:heading_lineno] + block + body_lines[heading_lineno:]
    return '\n'.join(new_lines)

def output_paths(plan_path):
    if plan_path.name == 'plan.md':
        return plan_path.parent / 'comments.md', plan_path.parent / 'plan.html'
    stem = plan_path.stem
    return plan_path.parent / f'{stem}.comments.md', plan_path.parent / f'{stem}.html'

def build_html(plan_path, server):
    lines = plan_path.read_text(encoding='utf-8').splitlines()
    front_matter, _, body_start = parse_front_matter(lines)
    body_lines = lines[body_start:]
    comments_path, _ = output_paths(plan_path)
    comments = comments_path.read_text(encoding='utf-8') if comments_path.exists() else ''
    data = {
        'title': extract_title(body_lines) or plan_path.stem,
        'frontMatter': front_matter,
        'markdown': inject_stages_diagram(body_lines),
        'comments': comments,
        'server': server,
    }
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    template_path = Path(__file__).resolve().parent / 'viewer.html'
    return template_path.read_text(encoding='utf-8').replace('__PLAN_DATA__', payload)

def render_plan(plan_path, out_arg):
    _, default_out = output_paths(plan_path)
    out_path = Path(out_arg) if out_arg else default_out
    out_path.write_text(build_html(plan_path, server=False), encoding='utf-8')
    return out_path

def comment_line(anchor, quote, author, text):
    quote_part = f'«{quote}» ' if quote else ''
    author_part = f'@{author}: ' if author else ''
    return f'- [ ] [{anchor}] {quote_part}{author_part}{text}'

def append_comment(plan_path, payload):
    anchor = str(payload.get('anchor', '')).strip()
    author = ' '.join(str(payload.get('author', '')).replace(':', ' ').split())
    text = ' '.join(str(payload.get('text', '')).split())
    quote = ' '.join(str(payload.get('quote', '')).replace('«', '"').replace('»', '"').split())[:QUOTE_LIMIT + 1]
    if not ANCHOR_RE.match(anchor) or not text:
        return None
    comments_path, _ = output_paths(plan_path)
    existing = comments_path.read_text(encoding='utf-8') if comments_path.exists() else ''
    separator = '' if not existing or existing.endswith('\n') else '\n'
    line = comment_line(anchor, quote, author, text)
    comments_path.write_text(f'{existing}{separator}{line}\n', encoding='utf-8')
    return line

def make_handler(plan_path):
    class PlanHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/', '/index.html'):
                self.send_error(404)
                return
            self.reply(200, 'text/html; charset=utf-8', build_html(plan_path, server=True))

        def do_POST(self):
            if self.path != '/comments':
                self.send_error(404)
                return
            length = int(self.headers.get('Content-Length', 0))
            try:
                payload = json.loads(self.rfile.read(length) or b'{}')
            except json.JSONDecodeError:
                payload = {}
            line = append_comment(plan_path, payload)
            if line is None:
                self.reply(400, 'text/plain; charset=utf-8', 'anchor and text are required')
                return
            self.reply(200, 'application/json', json.dumps({'line': line}, ensure_ascii=False))

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

def cli_check(argv):
    plan_path = Path(argv[0])
    root_arg = argv[argv.index('--root') + 1] if '--root' in argv else None
    root = resolve_root(plan_path, root_arg)
    problems = check_plan(plan_path, root)
    if not problems:
        print('ok')
        return 0
    for ln, msg in problems:
        print(f'{plan_path}:{ln}: {msg}')
    return 1

def cli_render(argv):
    plan_path = Path(argv[0])
    out_arg = argv[argv.index('-o') + 1] if '-o' in argv else None
    out_path = render_plan(plan_path, out_arg)
    print(out_path)
    return 0

def cli_serve(argv):
    plan_path = Path(argv[0]).resolve()
    if plan_path.is_dir():
        plan_path = plan_path / 'plan.md'
    port = int(argv[argv.index('--port') + 1]) if '--port' in argv else 0
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(plan_path))
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(url, flush=True)
    if '--no-open' not in argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

def main(argv):
    if len(argv) < 2:
        print('usage: plan_tool.py check|render|serve <plan.md> [options]', file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == 'check':
        return cli_check(rest)
    if cmd == 'render':
        return cli_render(rest)
    if cmd == 'serve':
        return cli_serve(rest)
    print(f'unknown command: {cmd}', file=sys.stderr)
    return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
