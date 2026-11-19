#!/usr/bin/env python3
"""Check in headless Chrome that arrow labels never overlap and stand in rows.

Usage: label_rows.py   (uses label-rows.visual.json beside this script)

The fixture has one check with three arrows to one fail node and a fourth arrow elsewhere;
before the row placement its first two labels overlapped.
The page is rendered, a probe reads every label box after placement, and the script asserts:
no two labels overlap, no label covers a node, and the labels of one check stand in two rows or fewer.
Needs Google Chrome and network access for the Mermaid script.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import visualize  # noqa: E402

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FIXTURE = Path(__file__).resolve().parent / 'label-rows.visual.json'
PROBE = """
<script>
(async () => {
  const boxOf = el => { const r = el.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom }; };
  for (let i = 0; i < 100; i += 1) {
    if (document.querySelector('section.overview svg g.edgeLabel')) break;
    await new Promise(done => setTimeout(done, 100));
  }
  await new Promise(done => setTimeout(done, 1500));
  const svgs = [...document.querySelectorAll('.diagram svg')].map(svg => ({
    labels: [...svg.querySelectorAll('g.edgeLabel span.edgeLabel')].filter(s => s.textContent.trim())
      .map(s => ({ text: s.textContent.trim(), ...boxOf(s) })),
    nodes: [...svg.querySelectorAll('g.node')].map(boxOf),
  }));
  const out = document.createElement('pre');
  out.id = 'probe';
  out.textContent = JSON.stringify(svgs);
  document.body.appendChild(out);
})();
</script>
"""
GROUP = ('вариант устарел', 'красная проверка', 'снимок dirtyState', 'все варианты свежие')
ROW_TOLERANCE = 4


def overlap(a, b):
    return a['l'] < b['r'] and b['l'] < a['r'] and a['t'] < b['b'] and b['t'] < a['b']


def probe():
    doc = json.loads(FIXTURE.read_text(encoding='utf-8'))
    page = visualize.render(doc).replace('</body>', PROBE + '</body>')
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'page.html'
        path.write_text(page, encoding='utf-8')
        dom = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--window-size=1280,2400',
                              '--virtual-time-budget=20000', f'--user-data-dir={folder}/profile',
                              '--dump-dom', path.as_uri()], capture_output=True, text=True, timeout=120).stdout
    match = re.search(r'<pre id="probe">(.*?)</pre>', dom, re.S)
    if not match:
        return None
    return json.loads(match.group(1).replace('&quot;', '"').replace('&amp;', '&'))


def problems(svgs):
    found = []
    for index, svg in enumerate(svgs, start=1):
        labels = svg['labels']
        found += [f'diagram {index}: "{a["text"]}" overlaps "{b["text"]}"'
                  for n, a in enumerate(labels) for b in labels[n + 1:] if overlap(a, b)]
        found += [f'diagram {index}: "{label["text"]}" covers a node'
                  for label in labels for node in svg['nodes'] if overlap(label, node)]
    group = [label for label in svgs[0]['labels'] if label['text'] in GROUP]
    if len(group) != len(GROUP):
        found.append(f'overview: found {len(group)} of {len(GROUP)} gate labels')
    rows = []
    for middle in sorted((label['t'] + label['b']) / 2 for label in group):
        if not rows or middle - rows[-1] > ROW_TOLERANCE:
            rows.append(middle)
    if len(rows) > 2:
        found.append(f'overview: gate labels stand in {len(rows)} rows, expected 2 or fewer')
    return found


def main():
    svgs = probe()
    if svgs is None:
        print('FAIL probe: no label data (Chrome or network missing?)')
        sys.exit(1)
    found = problems(svgs)
    for problem in found:
        print(f'FAIL {problem}')
    print('ok' if not found else f'{len(found)} problem(s)')
    sys.exit(1 if found else 0)


if __name__ == '__main__':
    main()
