#!/usr/bin/env python3
"""Check and render a visualize document (JSON) into a self-contained HTML page."""

import argparse
import html
import json
import re
import sys
from pathlib import Path

STATUSES = ('new', 'changed', 'same')
VIEW_TYPES = ('shape', 'table', 'steps')
MAX_OVERVIEW_NODES = 8
MAX_OVERVIEW_LINKS = 10
MAX_SECTION_NODES = 6
MAX_FLOW_EDGES = 7
MAX_OVERVIEW_FLOW_NODES = 10
MAX_OVERVIEW_FLOW_EDGES = 12
FLOW_KINDS = ('step', 'check', 'result')
MAX_LABEL_CHARS = 40
MAX_LINK_WORDS = 3
MAX_BRANCH_LABEL_WORDS = 6
MAX_SENTENCE_WORDS = 25
MAX_TAKEAWAY_WORDS = 15
MAX_SECTIONS = 6
MAX_OVERVIEW_BRANCHES = 1
VAGUE_VARIANT_RE = re.compile(r'(інакше|решта|і далі|иначе|остальн|и далее|\belse\b|otherwise|the rest|and later)', re.I)
MERMAID_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js'
LATIN_RE = re.compile(r'[A-Za-z]')
SENTENCE_RE = re.compile(r'[.!?;]\s+')
HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
UI_KEYS = ('new', 'changed', 'same', 'context', 'overview', 'files')
QUESTION_UI_KEYS = ('decide', 'question', 'recommend')
CYRILLIC_LANGS = ('ru', 'uk', 'be', 'bg', 'sr', 'mk', 'kk')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'render'))
    parser.add_argument('doc', type=Path)
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()

    doc = json.loads(args.doc.read_text(encoding='utf-8'))
    found = problems(doc)
    for problem in found:
        print(f'{args.doc}: {problem}', file=sys.stderr)
    if found:
        sys.exit(1)
    if args.command == 'check':
        print('ok')
        return

    output = args.output or args.doc.with_suffix('.html')
    output.write_text(render(doc), encoding='utf-8')
    print(output)


# ---------------------------------------------------------------- check

def problems(doc):
    found = []
    entities = {entity['id']: entity for entity in doc.get('entities', [])}
    found += head_problems(doc)
    found += entity_problems(doc.get('entities', []))
    found += link_problems(doc.get('links', []), entities, doc.get('lang', 'ru') in CYRILLIC_LANGS)
    found += section_problems(doc, entities)
    found += overview_flow_problems(doc, entities)
    found += group_problems(doc)
    found += question_problems(doc)
    return found


def head_problems(doc):
    found = [f'missing "{key}"' for key in ('title', 'summary', 'ui', 'sections') if key not in doc]
    ui = doc.get('ui', {})
    found += [f'ui: missing "{key}"' for key in UI_KEYS if key not in ui]
    if doc.get('questions'):
        found += [f'ui: missing "{key}"' for key in QUESTION_UI_KEYS if key not in ui]
    if has_branch(doc) and 'branch' not in ui:
        found.append('ui: missing "branch"')
    return found


def has_branch(doc):
    flows = [doc.get('flow') or {}] + [section.get('flow') or {} for section in doc.get('sections', [])]
    return any(node.get('kind') == 'check' for flow in flows for node in flow.get('nodes', []))


def entity_problems(entities):
    found = []
    seen = set()
    for entity in entities:
        name = entity.get('id', '?')
        if name in seen:
            found.append(f'entity {name}: duplicate id')
        seen.add(name)
        if entity.get('status') not in STATUSES:
            found.append(f'entity {name}: status must be one of {STATUSES}')
        for key in ('name', 'code', 'change'):
            if len(entity.get(key, '')) > MAX_LABEL_CHARS:
                found.append(f'entity {name}: {key} over {MAX_LABEL_CHARS} chars')
        if entity.get('status') != 'same' and not entity.get('change'):
            found.append(f'entity {name}: new or changed entity needs "change"')
        found += file_problems(f'entity {name}', entity.get('files', []))
    if len(entities) > MAX_OVERVIEW_NODES:
        found.append(f'{len(entities)} entities, limit {MAX_OVERVIEW_NODES}')
    return found


def file_problems(owner, files):
    return [f'{owner}: file {file.get("path")} has no valid status'
            for file in files if file.get('status') not in STATUSES]


def link_problems(links, entities, forbid_latin):
    found = []
    if len(links) > MAX_OVERVIEW_LINKS:
        found.append(f'{len(links)} links, limit {MAX_OVERVIEW_LINKS}')
    for link in links:
        label = link.get('label', '')
        where = f'link {link.get("from")} -> {link.get("to")}'
        found += [f'{where}: unknown entity {end}'
                  for end in (link.get('from'), link.get('to')) if end not in entities]
        if len(label.split()) > MAX_LINK_WORDS:
            found.append(f'{where}: label over {MAX_LINK_WORDS} words')
        if forbid_latin and LATIN_RE.search(label):
            found.append(f'{where}: label has Latin letters')
    return found


def section_problems(doc, entities):
    found = []
    covered = set()
    shown = []
    for index, section in enumerate(doc.get('sections', []), start=1):
        where = f'section {index}'
        own = section.get('entities', [])
        unknown = [name for name in own if name not in entities]
        found += [f'{where}: unknown entity {name}' for name in unknown]
        found += takeaway_problems(where, section.get('takeaway', ''))
        if section.get('flow'):
            found += flow_problems(where, section['flow'], entities)
            covered.update(node['entity'] for node in section['flow'].get('nodes', []) if node.get('entity'))
            continue
        if not own:
            found.append(f'{where}: no diagram; give it "entities" or a "flow"')
            continue
        if unknown:
            continue
        covered.update(own)
        if all(entities[name].get('status') == 'same' for name in own):
            found.append(f'{where}: entities are all "same"; a section draws a diagram only for what it creates or changes')
        nodes, _ = section_graph(doc, own)
        if len(nodes) > MAX_SECTION_NODES:
            found.append(f'{where}: diagram shows {len(nodes)} nodes with neighbours, limit {MAX_SECTION_NODES}')
        if frozenset(nodes) in shown:
            found.append(f'{where}: diagram repeats one already shown; drop "entities" or narrow them')
        shown.append(frozenset(nodes))
    for index, section in enumerate(doc.get('sections', []), start=1):
        where = f'section {index}'
        found += [problem for view in section.get('views', []) if view.get('type') == 'shape'
                  for problem in tree_problems(f'{where} · {view.get("title", "shape")}', view.get('root', {}))]
        found += line_problems(where, section.get('lines', []))
        if section.get('flow') and any(view.get('type') == 'steps' for view in section.get('views', [])):
            found.append(f'{where}: a "steps" view repeats the section flow; keep the order in the flow only')
        found += file_problems(where, section.get('files', []))
        found += [f'{where}: view type must be one of {VIEW_TYPES}'
                  for view in section.get('views', []) if view.get('type') not in VIEW_TYPES]
    found += [f'entity {name}: {entity["status"]} but in no section'
              for name, entity in entities.items()
              if entity.get('status') != 'same' and name not in covered]
    return found


def overview_flow_problems(doc, entities):
    flow = doc.get('flow')
    if not flow:
        return []
    found = flow_problems('overview flow', flow, entities, MAX_OVERVIEW_FLOW_NODES, MAX_OVERVIEW_FLOW_EDGES)
    shown = {node.get('entity') for node in flow.get('nodes', [])}
    found += [f'entity {name}: {entity["status"]} but not on the overview flow'
              for name, entity in entities.items() if entity.get('status') != 'same' and name not in shown]
    branches = [node for node in flow.get('nodes', []) if node.get('kind') == 'check']
    if len(branches) > MAX_OVERVIEW_BRANCHES:
        found.append(f'overview flow has {len(branches)} branches, limit {MAX_OVERVIEW_BRANCHES}; '
                     'draw the secondary one in its section and leave a note on the overview node')
    overview_keys = {flow_node_key(node) for node in flow.get('nodes', [])}
    for index, section in enumerate(doc.get('sections', []), start=1):
        section_flow = section.get('flow')
        if section_flow and {flow_node_key(node) for node in section_flow.get('nodes', [])} <= overview_keys:
            found.append(f'section {index}: its flow only repeats overview nodes; zoom in with at least one node of its own')
    overview_notes = {node['note'] for node in flow.get('nodes', []) if node.get('note')}
    for index, section in enumerate(doc.get('sections', []), start=1):
        found += [f'section {index}: node {node["id"]} repeats the overview note "{node["note"]}"; '
                  'a section node adds what the overview does not show'
                  for node in section.get('flow', {}).get('nodes', []) if node.get('note') in overview_notes]
    overview_variants = {edge.get('label') for edge in branch_edges(flow)}
    for index, section in enumerate(doc.get('sections', []), start=1):
        repeated = sorted(overview_variants & {edge.get('label') for edge in branch_edges(section.get('flow', {}))})
        if repeated:
            found.append(f'section {index}: redraws the overview branch ({", ".join(repeated)}); '
                         'start from one overview node and branch on something the overview does not')
        own = section.get('entities', [])
        if not section.get('flow') and own and set(own) <= shown:
            found.append(f'section {index}: its entity diagram only shows overview nodes; give it a "flow" that zooms in')
    for index, section in enumerate(doc.get('sections', []), start=1):
        if not shown & set(section_entities(section)):
            found.append(f'section {index}: none of its entities is on the overview flow; '
                         'the overview must cover every section')
    return found


def branch_edges(flow):
    branches = {node['id'] for node in flow.get('nodes', []) if node.get('kind') == 'check'}
    return [edge for edge in flow.get('edges', []) if edge.get('from') in branches]


def flow_node_key(node):
    return f'{node.get("entity", "")}|{node.get("label", "")}'


def section_entities(section):
    flow_entities = [node['entity'] for node in section.get('flow', {}).get('nodes', []) if node.get('entity')]
    return list(dict.fromkeys(section.get('entities', []) + flow_entities))


def flow_problems(where, flow, entities, max_nodes=MAX_SECTION_NODES, max_edges=MAX_FLOW_EDGES):
    found = []
    nodes = flow.get('nodes', [])
    ids = [node.get('id') for node in nodes]
    if len(nodes) > max_nodes:
        found.append(f'{where}: flow has {len(nodes)} nodes, limit {max_nodes}')
    if len(flow.get('edges', [])) > max_edges:
        found.append(f'{where}: flow has {len(flow["edges"])} arrows, limit {max_edges}')
    for node in nodes:
        name = node.get('id', '?')
        if node.get('entity') and node['entity'] not in entities:
            found.append(f'{where}: flow node {name} names unknown entity {node["entity"]}')
        if not node.get('entity') and not node.get('label'):
            found.append(f'{where}: flow node {name} needs "label" or "entity"')
        if visible_length(node.get('label', '')) > MAX_LABEL_CHARS or visible_length(node.get('note', '')) > MAX_LABEL_CHARS:
            found.append(f'{where}: flow node {name} label or note over {MAX_LABEL_CHARS} chars')
        if node.get('kind', 'step') not in FLOW_KINDS:
            found.append(f'{where}: flow node {name} kind must be one of {FLOW_KINDS}')
        if node.get('status', 'same') not in STATUSES:
            found.append(f'{where}: flow node {name} status must be one of {STATUSES}')
    branches = {node.get('id') for node in nodes if node.get('kind') == 'check'}
    for edge in flow.get('edges', []):
        found += [f'{where}: flow arrow names unknown node {end}'
                  for end in (edge.get('from'), edge.get('to')) if end not in ids]
        limit = MAX_BRANCH_LABEL_WORDS if edge.get('from') in branches else MAX_LINK_WORDS
        if edge.get('from') in branches and VAGUE_VARIANT_RE.search(edge.get('label', '')):
            found.append(f'{where}: variant "{edge.get("label")}" is vague; name the exact values it covers')
        if len(edge.get('label', '').split()) > limit:
            found.append(f'{where}: flow arrow label "{edge.get("label")}" over {limit} words')
    return found


def visible_length(text):
    return len(text.replace('`', ''))


def tree_problems(where, node):
    found = []
    name = node.get('name', '?')
    if '·' in name and (node.get('status') != 'same' or node.get('example')):
        found.append(f'{where}: "{name}" merges fields that are not all unchanged; one node per field')
    if node.get('status') == 'changed' and not node.get('values') and not node.get('children'):
        found.append(f'{where}: "{name}" is changed but shows no new values or children; list them in "values"')
    for value in node.get('values', []):
        if value.get('status', 'same') not in STATUSES:
            found.append(f'{where}: value {value.get("value")} has no valid status')
    for child in node.get('children', []):
        found += tree_problems(where, child)
    return found


def takeaway_problems(where, takeaway):
    if not takeaway:
        return [f'{where}: missing "takeaway"']
    if len(takeaway.split()) > MAX_TAKEAWAY_WORDS:
        return [f'{where}: takeaway over {MAX_TAKEAWAY_WORDS} words']
    return []


def group_problems(doc):
    sections = doc.get('sections', [])
    groups = doc.get('groups', [])
    if len(sections) > MAX_SECTIONS:
        return [f'{len(sections)} sections, limit {MAX_SECTIONS}; merge sections that share a topic']
    if groups:
        return ['"groups" are not used; at most 6 sections, merge the ones that share a topic']
    return []


def question_problems(doc):
    found = []
    for index, question in enumerate(doc.get('questions', []), start=1):
        where = f'question {index}'
        found += [f'{where}: missing "{key}"' for key in ('title', 'gist', 'options', 'recommendation')
                  if not question.get(key)]
        options = question.get('options', [])
        if len(options) < 2:
            found.append(f'{where}: needs at least 2 options')
        for option in options:
            found += [f'{where}: option {option.get("key")} missing "{key}"'
                      for key in ('key', 'text', 'consequence') if not option.get(key)]
        keys = [option.get('key') for option in options]
        if question.get('recommendation', {}).get('key') not in keys:
            found.append(f'{where}: recommendation key must be one of {keys}')
    return found


def line_problems(where, lines):
    found = []
    for line in lines:
        for sentence in SENTENCE_RE.split(line.get('text', '')):
            if len(sentence.split()) > MAX_SENTENCE_WORDS:
                found.append(f'{where}: "{line.get("label")}" has a sentence over {MAX_SENTENCE_WORDS} words')
    return found


# ---------------------------------------------------------------- graph

def section_graph(doc, own):
    """Own entities plus every entity one link away; links touching an own entity."""
    own = set(own)
    links = [link for link in doc.get('links', []) if link['from'] in own or link['to'] in own]
    nodes = set(own)
    for link in links:
        nodes.update((link['from'], link['to']))
    return nodes, links


def mermaid_source(doc, node_ids, links, direction, own=None, with_files=False):
    entities = [entity for entity in doc.get('entities', []) if entity['id'] in node_ids]
    lines = [f'flowchart {direction}']
    for entity in entities:
        is_context = own is not None and entity['id'] not in own
        css_class = 'context' if is_context else entity['status']
        label = node_label(entity, is_context, with_files)
        lines.append(f'  {node_id(entity["id"])}["{label}"]:::{css_class}')
    for link in links:
        lines.append(f'  {node_id(link["from"])} -->|{mermaid_text(link["label"])}| {node_id(link["to"])}')
    return '\n'.join(lines)


def node_label(entity, is_context, with_files):
    parts = [f'<b>{mermaid_text(entity["name"])}</b>']
    if entity.get('code'):
        parts.append(f"<span class='n-code'>{code_text(entity['code'])}</span>")
    if is_context:
        return '<br/>'.join(parts)
    if entity.get('change'):
        parts.append(f"<span class='n-change'>{mermaid_text(entity['change'])}</span>")
    if with_files:
        parts += [f"<span class='n-file'>{mermaid_text(Path(file['path']).name)}</span>"
                  for file in entity.get('files', [])]
    return '<br/>'.join(parts)


FLOW_SHAPES = {'step': ('["', '"]'), 'check': ('{{"', '"}}'), 'result': ('(["', '"])')}


def flow_source(doc, flow):
    by_id = {entity['id']: entity for entity in doc.get('entities', [])}
    lines = ['flowchart TD']
    for node in flow['nodes']:
        entity = by_id.get(node.get('entity'))
        status = node.get('status') or (entity or {}).get('status', 'same')
        parts = [f'<b>{flow_text(node.get("label") or entity["name"])}</b>']
        if entity and entity.get('code'):
            parts.append(f"<span class='n-code'>{code_text(entity['code'])}</span>")
        if node.get('note'):
            parts.append(f"<span class='n-change'>{flow_text(node['note'])}</span>")
        kind = node.get('kind', 'step')
        css_class = 'branch' if kind == 'check' else status
        open_shape, close_shape = FLOW_SHAPES[kind]
        lines.append(f'  {node_id(node["id"])}{open_shape}{"<br/>".join(parts)}{close_shape}:::{css_class}')
    branches = {node['id'] for node in flow['nodes'] if node.get('kind') == 'check'}
    branch_edges = []
    for index, edge in enumerate(flow.get('edges', [])):
        if edge.get('hidden'):
            lines.append(f'  {node_id(edge["from"])} ~~~ {node_id(edge["to"])}')
            continue
        from_branch = edge['from'] in branches
        if from_branch:
            branch_edges.append(str(index))
        text = flow_text(edge.get('label', ''))
        if text and from_branch:
            text = f"<span class='n-branch'>{text}</span>"
        label = f'|{text}|' if text else ''
        lines.append(f'  {node_id(edge["from"])} -->{label} {node_id(edge["to"])}')
    if branch_edges:
        lines.append(f'  linkStyle {",".join(branch_edges)} stroke:BRANCH_STROKE,stroke-width:1.8px')
    return '\n'.join(lines)


def node_id(name):
    return f'n_{name}'


def flow_text(value):
    return re.sub(r'`([^`]+)`', r"<span class='n-code'>\1</span>", mermaid_text(value))


def code_text(value):
    return re.sub(r'([./])', '\\1\u200b', mermaid_text(value))


def mermaid_text(value):
    return value.replace('"', '#quot;').replace('<', '#lt;').replace('>', '#gt;')


# ---------------------------------------------------------------- html

def render(doc):
    body = [
        f'<header><h1>{inline(doc["title"])}</h1><p class="summary">{inline(doc["summary"])}</p></header>',
        questions_html(doc),
        overview(doc),
        sections_html(doc),
    ]
    return PAGE.format(
        lang=html.escape(doc.get('lang', 'ru')),
        title=html.escape(doc['title']),
        body='\n'.join(body),
        sections_by_entity=json.dumps(sections_by_overview_node(doc)).replace('<', '\\u003c'),
        mermaid_url=MERMAID_URL,
    )


def questions_html(doc):
    questions = doc.get('questions', [])
    if not questions:
        return ''
    ui = doc['ui']
    cards = [question_card(ui, index, question) for index, question in enumerate(questions, start=1)]
    return f'<section id="decide"><h2>{html.escape(ui["decide"])}</h2>{"".join(cards)}</section>'


def question_card(ui, index, question):
    recommended = question['recommendation']['key']
    options = ''.join(
        f'<li class="{"recommended" if option["key"] == recommended else ""}">'
        f'<b>{html.escape(option["key"])} · {inline(option["text"])}</b>'
        f'<span class="consequence">{inline(option["consequence"])}</span></li>'
        for option in question['options'])
    return (f'<div class="h2-block decision"><h3>{html.escape(ui["question"])} {index} · {inline(question["title"])}</h3>'
            f'<p>{inline(question["gist"])}</p><ul class="options">{options}</ul>'
            f'<p class="recommendation"><span class="point-label">{html.escape(ui["recommend"])}:</span>'
            f'{html.escape(recommended)} — {inline(question["recommendation"].get("why", ""))}</p></div>')


def sections_html(doc):
    return ''.join(section_html(doc, index, section) for index, section in enumerate(doc['sections'], start=1))


def sections_by_overview_node(doc):
    by_entity = sections_by_entity(doc)
    if not doc.get('flow'):
        return by_entity
    return {node['id']: by_entity.get(node.get('entity'), []) for node in doc['flow']['nodes']}


def sections_by_entity(doc):
    mapping = {}
    for index, section in enumerate(doc['sections'], start=1):
        for name in section_entities(section):
            mapping.setdefault(name, []).append(f's-{index}')
    return mapping


def legend(ui, with_branch=False):
    keys = ('new', 'changed', 'branch') if with_branch else ('new', 'changed')
    items = [f'<span class="{key}">{html.escape(ui[key])}</span>' for key in keys]
    return f'<div class="legend">{"".join(items)}</div>'


def overview(doc):
    if not doc.get('entities'):
        return ''
    if doc.get('flow'):
        source = flow_source(doc, doc['flow'])
    else:
        node_ids = {entity['id'] for entity in doc['entities']}
        source = mermaid_source(doc, node_ids, doc.get('links', []), 'TD')
    ui = doc['ui']
    return (f'<section class="overview"><h2>{html.escape(ui["overview"])}</h2>'
            f'{diagram(source)}{legend(ui, has_branch(doc))}</section>'
            '<div id="zoom" hidden><button type="button" class="zoom-close" aria-label="close">×</button>'
            '<div class="zoom-body"></div></div>')


def section_html(doc, index, section):
    own = section.get('entities', [])
    parts = []
    top = []
    if section.get('flow'):
        top.append(diagram(flow_source(doc, section['flow'])))
    elif own:
        nodes, links = section_graph(doc, own)
        top.append(diagram(mermaid_source(doc, nodes, links, 'TD', own=set(own), with_files=True)))
    if section.get('lines'):
        top.append(lines_html(section['lines']))
    parts.append(''.join(top))
    files = section_files(doc, section)
    if files:
        parts.append(files_html(doc['ui']['files'], files))
    parts += [view_html(view) for view in section.get('views', [])]
    summary = (f'<summary><span class="sec-head"><span class="sec-title">{index}. {inline(section["title"])}</span>'
               f'<span class="takeaway">{inline(section["takeaway"])}</span></span></summary>')
    return f'<details class="sec" id="s-{index}">{summary}<div class="sec-body">{"".join(parts)}</div></details>'


def diagram(source):
    return f'<div class="diagram"><pre class="mermaid-src">{html.escape(source)}</pre></div>'


def lines_html(lines):
    rows = [f'<p><span class="point-label">{inline(line["label"])}:</span>{inline(line["text"])}</p>'
            for line in lines]
    return f'<div class="lines">{"".join(rows)}</div>'


def section_files(doc, section):
    by_id = {entity['id']: entity for entity in doc.get('entities', [])}
    files = [file for name in section.get('entities', []) for file in by_id[name].get('files', [])]
    return files + section.get('files', [])


def files_html(title, files):
    rows = [f'<li class="{file["status"]}"><span class="dot"></span><code>{html.escape(file["path"])}</code></li>'
            for file in files]
    return f'<div class="files"><div class="eyebrow">{html.escape(title)}</div><ul>{"".join(rows)}</ul></div>'


def view_html(view):
    title = f'<div class="eyebrow">{inline(view["title"])}</div>' if view.get('title') else ''
    body = {'shape': shape_html, 'table': table_html, 'steps': steps_html}[view['type']](view)
    return f'<div class="view {view["type"]}">{title}{body}</div>'


def shape_html(view):
    return f'<ul class="tree">{tree_node(view["root"])}</ul>'


def tree_node(node):
    status = node.get('status', 'same')
    parts = [f'<span class="mark {status}"></span><code class="field">{html.escape(node["name"])}</code>']
    if node.get('type'):
        parts.append(f'<span class="type">{html.escape(node["type"])}</span>')
    if node.get('example'):
        parts.append(f'<span class="example">{value_html(node["example"])}</span>')
    if node.get('note'):
        parts.append(f'<span class="note">{inline(node["note"])}</span>')
    if node.get('values'):
        chips = ''.join(f'<span class="value {value.get("status", "same")}"><code>{html.escape(value["value"])}</code>'
                        + (f'<span class="value-note">{inline(value["note"])}</span>' if value.get('note') else '')
                        + '</span>' for value in node['values'])
        parts.append(f'<div class="values">{chips}</div>')
    children = ''.join(tree_node(child) for child in node.get('children', []))
    nested = f'<ul>{children}</ul>' if children else ''
    return f'<li class="{status}"><div class="row">{"".join(parts)}</div>{nested}</li>'


def table_html(view):
    head = ''.join(f'<th>{inline(column)}</th>' for column in view['columns'])
    rows = ''.join('<tr>' + ''.join(f'<td>{value_html(cell)}</td>' for cell in row) + '</tr>'
                   for row in view['rows'])
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def steps_html(view):
    items = []
    for item in view['items']:
        tag = f'<span class="tag">{html.escape(item["tag"])}</span>' if item.get('tag') else ''
        note = f'<div class="note">{inline(item["note"])}</div>' if item.get('note') else ''
        items.append(f'<li><div class="row">{inline(item["text"])}{tag}</div>{note}</li>')
    return f'<ol class="steps">{"".join(items)}</ol>'


def value_html(value):
    if HEX_RE.match(value):
        return f'<span class="swatch" style="background:{value}"></span><code>{value}</code>'
    return inline(value)


def inline(text):
    escaped = html.escape(text)
    escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', escaped)


PAGE = '''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --ink: #151823; --ink-2: #5B6173; --ink-3: #3E4456;
  --blue: #3F5FD8; --blue-d: #2C47B3; --blue-l: #5577EE; --blue-bg: #E6ECFF; --blue-bg2: #F7F9FF; --blue-line: #C9D4FA;
  --line: #E3E6EE; --line-2: #D5D9E3; --section: #F4F5F9; --card: #FFFFFF; --badge: #E8EAF1;
  --node-new-bg: #DAFBE1; --node-new-border: #1A7F37; --node-new-fg: #116329;
  --node-changed-bg: #DDF4FF; --node-changed-border: #0969DA; --node-changed-fg: #0550AE;
  --node-same-bg: #F6F8FA; --node-same-border: #D0D7DE; --node-same-fg: #57606A;
  --node-branch-bg: #EDE4FF; --node-branch-border: #7A4FD6; --node-branch-fg: #4A2696;
  --node-context-bg: #FFFFFF; --node-context-border: #D5D9E3; --node-context-fg: #8A90A2;
  --f-display: 'Unbounded', system-ui, sans-serif;
  --f-body: 'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --f-mono: 'JetBrains Mono', ui-monospace, Menlo, monospace;
  color-scheme: light;
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  background: var(--section); color: var(--ink); font-family: var(--f-body); font-size: 16px; line-height: 1.55;
  max-width: 792px; margin: 0 auto; padding: 24px 16px 48px; overflow-wrap: anywhere;
}}
h1, h2, h3 {{ line-height: 1.25; }}
h1 {{ font-family: var(--f-display); font-weight: 700; font-size: clamp(28px, 7.4vw, 40px); line-height: 1.15; margin: 0 0 14px; }}
h2 {{ font-family: var(--f-display); font-weight: 700; font-size: clamp(20px, 5.4vw, 24px); margin: 32px 0 14px; }}
h3 {{ font-family: var(--f-body); font-weight: 700; font-size: 18px; margin: 16px 0 8px; }}
.summary {{ color: var(--ink-2); font-size: 17px; margin: 0 0 8px; }}
code {{ font-family: var(--f-mono); font-size: max(12px, .86em); background: var(--badge); color: var(--ink-3); padding: 1px 5px; border-radius: 6px; }}
.eyebrow {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--blue); margin: 18px 0 8px; }}
.diagram {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; overflow-x: auto; text-align: center; }}
.h2-block .diagram {{ background: var(--blue-bg2); border-color: var(--line); padding: 12px; margin: 4px 0 12px; }}
.diagram svg {{ max-width: 100%; height: auto; }}
section > .diagram {{ width: min(1100px, calc(100vw - 32px)); position: relative; left: 50%; transform: translateX(-50%); }}
.diagram .node rect {{ rx: 10px; ry: 10px; }}
.mermaid-src {{ display: none; }}
.n-code {{ font-family: var(--f-mono); font-size: 14px; opacity: .8; }}
.n-change {{ font-size: 15px; font-style: italic; }}
.n-file {{ font-family: var(--f-mono); font-size: 13px; opacity: .7; }}
.legend {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; font-weight: 600; color: var(--ink-2); margin: 10px 0 28px; }}
.legend span::before {{ content: ""; display: inline-block; width: 12px; height: 12px; border-radius: 4px; margin-right: 6px; vertical-align: -1px; border: 1.5px solid; }}
.legend .new::before, .mark.new, li.new .dot {{ background: var(--node-new-bg); border-color: var(--node-new-border); }}
.legend .changed::before, .mark.changed, li.changed .dot {{ background: var(--node-changed-bg); border-color: var(--node-changed-border); }}
.legend .same::before, .mark.same, li.same .dot {{ background: var(--node-same-bg); border-color: var(--node-same-border); }}
.legend .branch::before {{ background: var(--node-branch-bg); border-color: var(--node-branch-border); }}
:is(.diagram, .zoom-body) .edgeLabel span.edgeLabel:has(.n-branch) {{
  background: var(--node-branch-bg) !important; border: 1.5px solid var(--node-branch-border); border-radius: 999px;
  padding: 1px 10px; font-style: normal; font-weight: 700; color: var(--node-branch-fg);
}}
:is(.diagram, .zoom-body) .edgeLabel .n-branch, :is(.diagram, .zoom-body) .edgeLabel .n-branch .n-code {{ color: var(--node-branch-fg); }}
.legend .context::before {{ background: var(--node-context-bg); border-color: var(--node-context-border); border-style: dashed; }}
.sec {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; margin: 0 0 12px; transition: box-shadow .3s, border-color .3s; }}
.sec[open] {{ border-color: var(--blue-line); }}
.sec.flash {{ border-color: var(--blue-l); box-shadow: 0 0 0 3px var(--blue-bg); }}
.sec summary {{ display: flex; align-items: center; gap: 12px; padding: 14px 20px; cursor: pointer; list-style: none; }}
.sec summary::-webkit-details-marker {{ display: none; }}
.sec summary::after {{ content: ""; flex: none; width: 8px; height: 8px; margin-left: auto; border-right: 2px solid var(--ink-2); border-bottom: 2px solid var(--ink-2); transform: rotate(45deg); transition: transform .15s; }}
.sec[open] summary::after {{ transform: rotate(-135deg); }}
.sec-head {{ display: flex; flex-direction: column; }}
.sec-title {{ font-weight: 700; font-size: 17px; }}
.takeaway {{ color: var(--ink-2); font-size: 15px; }}
.sec summary .sec-title + .takeaway {{ margin-top: 2px; }}
.sec-body {{ padding: 0 20px 16px; }}
#decide h2 {{ color: #9A4312; }}
.decision {{ border-color: #E08A4F; background: #FFF8F3; }}
.options {{ list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 8px; }}
.options li {{ background: var(--card); border: 1px solid var(--line-2); border-radius: 14px; padding: 10px 14px; display: flex; flex-direction: column; }}
.options li.recommended {{ border-color: var(--blue-l); box-shadow: inset 0 0 0 1px var(--blue-l); }}
.consequence {{ color: var(--ink-2); font-size: 15px; }}
.recommendation {{ font-size: 15px; }}
.diagram g.node {{ cursor: pointer; }}
section.overview > .diagram {{ cursor: zoom-in; transition: border-color .15s, box-shadow .15s; }}
section.overview > .diagram:hover {{ border-color: var(--blue-line); box-shadow: 0 4px 18px rgba(21, 24, 35, .06); }}
:is(.diagram, .zoom-body) .edgeLabel {{ background: transparent !important; }}
:is(.diagram, .zoom-body) .edgeLabel rect {{ fill: transparent !important; }}
:is(.diagram, .zoom-body) .edgeLabel .labelBkg {{ background: transparent !important; max-width: none !important; display: flex !important; justify-content: center; width: 100%; }}
:is(.diagram, .zoom-body) .edgeLabel foreignObject {{ overflow: visible; }}
:is(.diagram, .zoom-body) .edgeLabel p {{ margin: 0; display: inline; background: transparent !important; }}
:is(.diagram, .zoom-body) .edgeLabel span.edgeLabel {{
  display: inline-block; background: var(--card) !important; padding: 0 4px; font-size: 13px; font-weight: 500;
  font-style: italic; color: var(--ink-2); line-height: 1.5; white-space: nowrap;
}}
:is(.diagram, .zoom-body) .edgeLabel span.edgeLabel:empty {{ display: none; }}
:is(.diagram, .zoom-body) .edgeLabel .n-code {{ font-family: var(--f-body); font-size: 13px; opacity: 1; color: var(--blue-d); }}
#zoom {{ position: fixed; inset: 0; z-index: 20; background: var(--section); overflow: auto; padding: 56px 24px 24px; }}
#zoom[hidden] {{ display: none; }}
.zoom-body {{ width: max-content; min-width: 100%; display: flex; justify-content: center; }}
.zoom-body svg {{ max-width: none !important; height: auto; }}
.zoom-body g.node {{ cursor: pointer; }}
.zoom-close {{ position: fixed; top: 12px; right: 16px; width: 40px; height: 40px; border-radius: 999px; border: 1px solid var(--line-2); background: var(--card); font-size: 22px; line-height: 1; cursor: pointer; color: var(--ink-3); }}
.h2-block {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 4px 20px 16px; margin: 0 0 16px; }}
.lines p {{ margin: 0 0 8px; }}
.point-label {{ font-weight: 600; margin-right: 6px; }}
.files ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }}
.files li {{ display: flex; align-items: center; gap: 8px; font-size: 14px; }}
.files code {{ background: none; padding: 0; }}
.dot, .mark {{ width: 12px; height: 12px; border-radius: 4px; border: 1.5px solid; flex: none; display: inline-block; }}
.tree, .tree ul {{ list-style: none; margin: 0; padding: 0; }}
.tree ul {{ margin-left: 6px; padding-left: 18px; border-left: 1.5px solid var(--line-2); }}
.tree .row {{ display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; padding: 4px 0; }}
.tree li.same > .row .field {{ color: var(--ink-2); background: none; padding: 0; }}
.tree li.new > .row .field {{ background: var(--node-new-bg); color: var(--node-new-fg); font-weight: 600; }}
.tree li.changed > .row .field {{ background: var(--node-changed-bg); color: var(--node-changed-fg); font-weight: 600; }}
.values {{ flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 6px; padding: 2px 0 4px; }}
.value {{ display: inline-flex; align-items: center; gap: 6px; border: 1.5px solid var(--node-same-border); background: var(--node-same-bg); border-radius: 8px; padding: 2px 8px; font-size: 13px; }}
.value code {{ background: none; padding: 0; color: var(--node-same-fg); }}
.value.new {{ border-color: var(--node-new-border); background: var(--node-new-bg); }}
.value.new code {{ color: var(--node-new-fg); font-weight: 600; }}
.value.changed {{ border-color: var(--node-changed-border); background: var(--node-changed-bg); }}
.value.changed code {{ color: var(--node-changed-fg); font-weight: 600; }}
.value-note {{ color: var(--ink-2); }}
.type {{ font-size: 13px; color: var(--ink-2); }}
.note {{ font-size: 14px; color: var(--ink-2); }}
.example {{ display: inline-flex; align-items: center; }}
.swatch {{ width: 16px; height: 16px; border-radius: 5px; border: 1px solid var(--line-2); display: inline-block; vertical-align: -3px; margin-right: 6px; }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; margin: 4px 0; font-size: 14px; width: 100%; }}
th, td {{ padding: 10px 12px 10px 0; text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }}
th {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--ink-2); }}
tbody tr:last-child td {{ border-bottom: none; }}
.steps {{ margin: 0; padding-left: 22px; display: grid; gap: 8px; }}
.steps .row {{ display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; }}
.tag {{ font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 999px; background: var(--blue-bg); color: var(--blue-d); }}
</style>
</head>
<body>
{body}
<script src="{mermaid_url}"></script>
<script>
const SECTIONS_BY_ENTITY = {sections_by_entity};
const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const classDefs = () => ['new', 'changed', 'same', 'context', 'branch'].map(name =>
  `  classDef ${{name}} fill:${{cssVar(`--node-${{name}}-bg`)}},stroke:${{cssVar(`--node-${{name}}-border`)}},` +
  `color:${{cssVar(`--node-${{name}}-fg`)}},stroke-width:1.5px` + (name === 'context' ? ',stroke-dasharray:4 3' : ''));
mermaid.initialize({{
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'base',
  themeVariables: {{
    background: cssVar('--card'), primaryColor: cssVar('--section'), primaryTextColor: cssVar('--ink'),
    primaryBorderColor: cssVar('--line-2'), lineColor: cssVar('--ink-2'), textColor: cssVar('--ink'),
    edgeLabelBackground: cssVar('--card'), fontFamily: cssVar('--f-body'), fontSize: '17px',
  }},
  flowchart: {{ curve: 'basis', nodeSpacing: 28, rankSpacing: 48, padding: 12, wrappingWidth: 200, htmlLabels: true, useMaxWidth: true }},
}});
const LABEL_STOPS = [0.5, 0.62, 0.38, 0.72, 0.28, 0.8, 0.2];
const LABEL_GAP = 6;
const boxesOverlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
function labelShape(svg, label) {{
  const rect = (label.querySelector('span.edgeLabel') || label).getBoundingClientRect();
  if (!rect.width) return null;
  const toSvg = svg.getScreenCTM().inverse();
  const topLeft = new DOMPoint(rect.left, rect.top).matrixTransform(toSvg);
  const bottomRight = new DOMPoint(rect.right, rect.bottom).matrixTransform(toSvg);
  const anchor = label.transform.baseVal.consolidate().matrix;
  return {{
    dx: (topLeft.x + bottomRight.x) / 2 - anchor.e, dy: (topLeft.y + bottomRight.y) / 2 - anchor.f,
    width: bottomRight.x - topLeft.x + LABEL_GAP, height: bottomRight.y - topLeft.y + LABEL_GAP,
  }};
}}
function labelBox(shape, point) {{
  const x = point.x + shape.dx;
  const y = point.y + shape.dy;
  return {{ left: x - shape.width / 2, right: x + shape.width / 2, top: y - shape.height / 2, bottom: y + shape.height / 2 }};
}}
const pointInBox = (point, box) => point.x > box.left && point.x < box.right && point.y > box.top && point.y < box.bottom;
function pathSamples(path) {{
  const length = path.getTotalLength();
  return Array.from({{ length: Math.ceil(length / 4) + 1 }}, (_, step) => path.getPointAtLength(Math.min(step * 4, length)));
}}
function placeLabelsOnCurves(svg) {{
  const paths = [...svg.querySelectorAll('.edgePaths path')];
  const placed = [];
  [...svg.querySelectorAll('g.edgeLabel')].forEach((label, index) => {{
    const path = paths[index];
    if (!path || !label.getAttribute('transform')) return;
    const shape = labelShape(svg, label);
    if (!shape) return;
    const length = path.getTotalLength();
    const candidates = LABEL_STOPS.map(stop => path.getPointAtLength(length * stop));
    const others = paths.filter(other => other !== path).flatMap(pathSamples);
    const clearOfLabels = candidate => !placed.some(box => boxesOverlap(box, labelBox(shape, candidate)));
    const clearOfPaths = candidate => !others.some(sample => pointInBox(sample, labelBox(shape, candidate)));
    const point = candidates.find(candidate => clearOfLabels(candidate) && clearOfPaths(candidate))
      || candidates.find(clearOfLabels) || candidates[0];
    placed.push(labelBox(shape, point));
    label.setAttribute('transform', `translate(${{point.x}}, ${{point.y}})`);
  }});
}}
document.querySelectorAll('details.sec').forEach(card => card.addEventListener('toggle', () => {{
  if (card.open) card.querySelectorAll('.diagram svg').forEach(placeLabelsOnCurves);
}}));
(async () => {{
  await document.fonts.ready;
  let count = 0;
  for (const pre of document.querySelectorAll('.mermaid-src')) {{
    count += 1;
    const source = [pre.textContent.replaceAll('BRANCH_STROKE', cssVar('--node-branch-border')), ...classDefs()].join('\\n');
    const {{ svg }} = await mermaid.render(`diagram-${{count}}`, source);
    pre.insertAdjacentHTML('afterend', svg);
    placeLabelsOnCurves(pre.nextElementSibling);
  }}
  const overview = document.querySelector('section.overview > .diagram svg');
  if (!overview) return;
  const zoom = document.getElementById('zoom');
  const closeZoom = () => {{ zoom.hidden = true; zoom.querySelector('.zoom-body').innerHTML = ''; }};
  const openSections = targets => targets.forEach((id, i) => {{
    const card = document.getElementById(id);
    card.open = true;
    card.classList.add('flash');
    setTimeout(() => card.classList.remove('flash'), 1600);
    if (i === 0) card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }});
  const bindNodes = svg => svg.querySelectorAll('g.node').forEach(node => {{
    const match = /^flowchart-n_(.+)-\\d+$/.exec(node.id);
    const targets = match ? SECTIONS_BY_ENTITY[match[1]] || [] : [];
    node.addEventListener('click', event => {{
      event.stopPropagation();
      closeZoom();
      openSections(targets);
    }});
  }});
  const openZoom = () => {{
    const copy = overview.cloneNode(true);
    const natural = overview.viewBox.baseVal.width;
    copy.style.width = `${{Math.round(Math.max(natural, Math.min(natural * 1.35, innerWidth - 48)))}}px`;
    zoom.querySelector('.zoom-body').append(copy);
    bindNodes(copy);
    zoom.hidden = false;
  }};
  bindNodes(overview);
  overview.parentElement.addEventListener('click', openZoom);
  zoom.querySelector('.zoom-close').addEventListener('click', closeZoom);
  document.addEventListener('keydown', event => {{ if (event.key === 'Escape') closeZoom(); }});
}})();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
