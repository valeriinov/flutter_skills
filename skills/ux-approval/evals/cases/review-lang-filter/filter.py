"""Run the page's Review language filter over sample rows; print each option's count and what search keeps."""
import json
import re
import subprocess
import sys
from pathlib import Path

skill = Path(sys.argv[1])
html = (skill / 'page_template.html').read_text(encoding='utf-8')
names = ['storedReviewLang', 'inReviewLang', 'matchesReview']
functions = [re.search(rf'  function {name}\(.*?\n  }}\n', html, re.S).group(0) for name in names]
consts = [re.search(rf'  const {name} = .*?;\n', html).group(0) for name in ('REVIEW_LANGS', 'textOf')]
rows = [{'id': 'uk.a', 'lang': 'uk', 'key': 'a', 'was': 'Картка'}, {'id': 'uk.b', 'lang': 'uk', 'key': 'b', 'was': 'Кошик'},
        {'id': 'en.a', 'lang': 'en', 'key': 'a', 'was': 'Card'}]
script = ('const SRC = "uk"; const REVIEW_LANG_STORE = "k"; let reviewQuery = ""; let reviewLang = "all"; let store = {};\n'
          'const localStorage = { getItem: (k) => { if (store.blocked) throw new Error("blocked"); return store[k] ?? null; } };\n'
          'const latest = () => new Map(); const tMap = () => "";\n' + ''.join(consts + functions) + f'const rows = {json.dumps(rows)};\n'
          + r'''
const shown = () => rows.filter(matchesReview).map((r) => r.id).join(',') || '-';
console.log('counts ' + REVIEW_LANGS.map((side) => `${side} ${rows.filter((r) => inReviewLang(r, side)).length}`).join(', '));
for (const side of REVIEW_LANGS) { reviewLang = side; console.log(`shown ${side}: ${shown()}`); }
reviewLang = 'target'; reviewQuery = 'кошик'; console.log(`target + search кошик: ${shown()}`);
reviewLang = 'source'; console.log(`source + search кошик: ${shown()}`);
for (const [label, value] of [['saved source', { k: 'source' }], ['saved bogus', { k: 'bogus' }], ['nothing saved', {}], ['storage blocked', { blocked: true }]]) {
  store = value; console.log(`${label}: ${storedReviewLang()}`);
}
''')
print(subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True).stdout, end='')
print('control ' + ('present' if 'id="review-langs"' in html else 'missing'))
table = (skill / 'SKILL.md').read_text(encoding='utf-8')
print('ui string ' + ('listed' if '| `reviewLangLabel` |' in table else 'missing'))
