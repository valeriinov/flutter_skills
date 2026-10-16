"""Run cases.json through approval.text_issues and the page's textIssues; print both and whether they agree."""
import json
import re
import subprocess
import sys
from pathlib import Path

skill = Path(sys.argv[1])
sys.path.insert(0, str(skill))
import approval  # noqa: E402

cases = json.loads((Path(__file__).parent / 'cases.json').read_text(encoding='utf-8'))
rules = approval.text_rules()
python = [approval.text_issues(case['lang'], case['text'], case['round'], rules) for case in cases]
html = (skill / 'page_template.html').read_text(encoding='utf-8')
names = ['textIssues', 'placeholderIssues', 'matchesSlot', 'slotPart']
functions = [re.search(rf'  function {name}\(.*?\n  }}\n', html, re.S).group(0) for name in names]
helpers = [re.search(rf'  const {name} = .*?;\n', html).group(0) for name in ('textOf', 'textPresent')]
script = (f'const DATA = {{textRules: {json.dumps(rules)}}};\n' + ''.join(helpers + functions)
          + f'console.log(JSON.stringify({json.dumps(cases)}.map((c) => textIssues(c.lang, c.text, c.round))));')
page = json.loads(subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True).stdout)
for case, mine, theirs in zip(cases, python, page):
    print(f'{json.dumps(case["text"], ensure_ascii=False)}: python {mine} page {theirs}')
print('parity ok' if python == page else 'parity FAIL')
