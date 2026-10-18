#!/usr/bin/env python3
"""Index the Dart symbols of a project in SQLite and answer for them.

Usage:
  codemap.py build <root> [--if-missing]
  codemap.py refresh <root>
  codemap.py show <Name|Container.name> [--root <root>]
  codemap.py map <root> [--budget <tokens>]
  codemap.py hook

`build` runs the Dart extractor over the `lib/` and `test/` of the project and
writes `<root>/.codemap/index.sqlite`; the folder carries a `.gitignore` of `*`,
so git and ripgrep skip it. The index holds the declarations of the project and
the package declarations (`package:` libraries, `dart:` excluded) that the
project refers to. The SDK is `<root>/.fvm/flutter_sdk/bin/cache/dart-sdk`
when it exists, else the SDK of `dart` on PATH. The extractor compiles once
per SDK version into `~/.cache/codemap/bin/<version>/`, and again when its
source changes. A root without `.dart_tool/package_config.json` is skipped:
references do not resolve without it. `--if-missing` builds only when no index
exists and no other build runs.

`refresh` compares the modification time, then the hash, of every indexed file
with the disk. It extracts again the changed and new files and every file that
refers to a changed or deleted library, in one extractor run, and drops the
rows of deleted files. A refresh that finds the lock taken marks the index
dirty and exits; the holder runs one more pass before it releases the lock.

`show` prints the declaration, signature, supertypes, subtypes and up to
twelve uses (production lib/ first) with their source line and the member they
stand in. The first three of those members print their head (annotations and
signature) or, at six lines or fewer, their whole body. A method, function,
getter or constructor also prints the declarations it calls and the tree of
production members that call it, up to ten levels and twenty nodes. The answer
for one name holds at most 2500 characters; a longer one ends with a line that
names the `Container.name` to narrow it to. More than three declarations of a
name print only their list, at most 1000 characters. Without `--root`, `show`
uses the nearest folder above the current folder that has
`.dart_tool/package_config.json`.

`map` ranks the files by the references between them (PageRank) and prints the
public types of the top files with the signatures of their public members, in
at most `--budget` tokens (one token is four characters).

`hook` reads a hook payload on stdin:
- UserPromptSubmit: the `show` answer for up to two identifiers the prompt
  names (in backticks, or a class name), without declaration lists.
- PreToolUse of a Grep, or of a Bash command that runs grep, rg or git grep
  inside a Dart project: the `show` answer for up to two searched identifiers,
  at most 5000 characters in all; the search runs as well.
- PreToolUse of a Bash `sed -n A,Bp`, `cat` or `cat | sed -n A,Bp` of a .dart
  file, and PostToolUse of a Read: the declarations of other files that the
  read lines use, with their location.
- PostToolUse of an Edit, Write or MultiEdit of a .dart file: a detached
  refresh.
- SessionStart and SubagentStart: the map when CODEMAP_MAP=1.
A name answered once is not answered again in the same session
(`<root>/.codemap/seen/`, kept for a day). With CODEMAP_AB=1 the hook stays
silent in sessions whose session_id hash is even and logs each decision to
`<root>/.codemap/ab.log`. With CODEMAP_HOOK=off it does nothing. A command that
neither searches nor reads a Dart file exits before any disk access. A missing
index starts a detached build. Any error exits silently with code 0.
"""
import json
import os
import re
import shlex
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRACTOR_DIR = os.path.join(SKILL_DIR, "extractors", "dart")
EXTRACTOR_SOURCES = ("pubspec.yaml", os.path.join("bin", "codemap_dart.dart"))
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "codemap")
INDEX_DIR = ".codemap"
INDEX_FILE = "index.sqlite"
PACKAGE_CONFIG = os.path.join(".dart_tool", "package_config.json")
FVM_SDK = os.path.join(".fvm", "flutter_sdk", "bin", "cache", "dart-sdk")
SYMBOL_LIMIT = 2500
HOOK_LIMIT = 2 * SYMBOL_LIMIT
LIST_LIMIT = 1000
LISTED_DECLARATIONS = 3
USE_LIMIT = 12
ANNOTATION_SPAN = 3
BODY_USES = 3
READ_LINES = 2000
SEEN_MAX_AGE = 24 * 60 * 60
READ_FILE_LIMIT = 3
READ_REF_LIMIT = 12
READ_KINDS = ("class", "mixin", "enum", "extension", "constructor", "method", "getter", "setter", "function")
BODY_LINES = 6
CUT_MARK = "\0"
SUBTYPE_LIMIT = 6
USE_TEXT_LIMIT = 60
HOOK_SYMBOL_LIMIT = 2
HOOK_CANDIDATE_LIMIT = 6
CHAIN_DEPTH = 10
CHAIN_BRANCHES = 4
CHAIN_NODES = 20
CALLEE_LIMIT = 8
MAP_BUDGET = 1500
MAP_MEMBER_LIMIT = 3
MAP_DETAILED_SHARE = 0.5
SUPERTYPE_WEIGHT = 10
PAGERANK_ITERATIONS = 30
PAGERANK_DAMPING = 0.85
TYPE_KINDS = ("class", "mixin", "enum", "extension", "extensionType", "typedef")
MEMBER_KINDS = ("constructor", "method", "getter", "setter", "field")
CALLABLE_KINDS = ("constructor", "method", "getter", "setter", "function")
NON_PRODUCTION = re.compile(r"(^|/)(test|integration_test|mocks?)/")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
SEARCH_TOOLS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "git grep"}
DIRECTORY_SEARCHES = {"rg", "ag", "ack", "git grep"}
COMMAND_WRAPPERS = {"sudo", "env", "xargs", "command", "time", "nice"}
SHELL_KEYWORDS = {"if", "then", "else", "elif", "while", "until", "do", "exec", "!"}
VALUE_OPTIONS = {
    "-e", "-f", "-A", "-B", "-C", "-m", "-g", "-t", "-T", "-M", "-j", "-d", "-D",
    "--regexp", "--file", "--glob", "--iglob", "--type", "--type-not",
    "--max-count", "--context", "--after-context", "--before-context",
    "--include", "--exclude", "--exclude-dir", "--max-depth", "--sort",
}
PATTERN_OPTIONS = {"-e", "-f", "--regexp", "--file"}
HEREDOC_OPEN = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")
SHELL_OPERATOR = re.compile(r"[();<>|&]+")
SHELL_WORD = re.compile(r"[();<>|&]+|[^\s();<>|&]+")
REGEX_ESCAPE = re.compile(r"\\[bBwWsSdD<>]")
CLASS_NAME = re.compile(r"(?<![A-Za-z0-9_$])_?[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+(?![A-Za-z0-9_])")
QUALIFIED_NAME = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\.[A-Za-z_$][A-Za-z0-9_$]*")
GENERATED_FILE = re.compile(r"\.(g|freezed|gr|config|mocks)\.dart$")
SHELL_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=[^=]+")
SHELL_NAME = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
SED_RANGE = re.compile(r"(\d+),(\d+)p")
ANNOTATION_LINE = re.compile(r"@[\w.]+(\(.*\))?")
BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")
MEMBER_NAME = re.compile(r"(?<![A-Za-z0-9_$])_?[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+(?![A-Za-z0-9_])")
CUT_LINE = "    ... cut at {limit} characters"
HOOK_HEADER = "codemap index for {names}; the search runs as well.\n\n"
PROMPT_HEADER = "codemap index for {names} named in the prompt.\n\n"
CURRENT_PROMPT_HEADER = (
    "codemap index for {names} named in the prompt; the Dart analyzer resolved it from the current sources.\n\n"
)
MAP_HEADER = "codemap project map: files ranked by references, public types and members.\n"
SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE files(id INTEGER PRIMARY KEY, path TEXT UNIQUE, hash TEXT, mtime INTEGER,
  uri TEXT, analyzed INTEGER);
CREATE TABLE ids(key INTEGER PRIMARY KEY, id TEXT UNIQUE);
CREATE TABLE symbols(key INTEGER PRIMARY KEY, name TEXT, kind TEXT, container TEXT,
  file INTEGER, line INTEGER, signature TEXT, supertypes TEXT);
CREATE TABLE refs(target INTEGER, file INTEGER, line INTEGER, text TEXT);
CREATE INDEX symbols_name ON symbols(name);
CREATE INDEX symbols_file ON symbols(file);
CREATE INDEX refs_target ON refs(target);
CREATE INDEX refs_file ON refs(file);
CREATE VIEW symbol_rows AS
  SELECT i.id AS id, s.name, s.kind, s.container, f.path AS file, s.line, s.signature, s.supertypes
  FROM symbols s JOIN ids i ON i.key = s.key JOIN files f ON f.id = s.file;
CREATE VIEW ref_rows AS
  SELECT i.id AS target, f.path AS file, r.line, r.text
  FROM refs r JOIN ids i ON i.key = r.target JOIN files f ON f.id = r.file;
"""


def main(argv):
    command, arguments = (argv[0], argv[1:]) if argv else ("", [])
    if command == "hook":
        hook(json.load(sys.stdin))
        return 0
    if command == "build" and arguments:
        return build(os.path.abspath(arguments[0]), "--if-missing" in arguments)
    if command == "refresh" and arguments:
        return refresh(os.path.abspath(arguments[0]))
    if command == "show" and arguments:
        root = option(arguments, "--root") or find_root(os.getcwd())
        return print_answer(show_text(index_path(root), arguments[0]) if root else "")
    if command == "map" and arguments:
        budget = int(option(arguments, "--budget") or MAP_BUDGET)
        return print_answer(map_text(index_path(os.path.abspath(arguments[0])), budget))
    print(__doc__.split("\n\n", 2)[1], file=sys.stderr)
    return 2


def option(arguments, name):
    if name not in arguments:
        return None
    position = arguments.index(name) + 1
    return arguments[position] if position < len(arguments) else None


def print_answer(text):
    if not text:
        print("codemap: no symbol", file=sys.stderr)
        return 1
    print(text)
    return 0


def index_dir(root):
    return os.path.join(root, INDEX_DIR)


def index_path(root):
    return os.path.join(index_dir(root), INDEX_FILE)


def find_root(start):
    path = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(path, PACKAGE_CONFIG)):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


# build and refresh


def build(root, if_missing=False):
    if not os.path.isfile(os.path.join(root, PACKAGE_CONFIG)):
        print(f"codemap: skip {root}: no {PACKAGE_CONFIG}", file=sys.stderr)
        return 0
    import time

    started = time.time()
    lock = open_lock(root)
    if not take_lock(lock, blocking=not if_missing):
        return 0
    if if_missing and os.path.isfile(index_path(root)):
        return 0
    sdk = sdk_path(root)
    extractor = extractor_path(sdk)
    temporary = index_path(root) + ".tmp"
    if os.path.exists(temporary):
        os.remove(temporary)
    db = connect(temporary)
    db.executescript(SCHEMA)
    writer = Writer(db, root, source_mtimes(root, ["lib", "test"]))
    for record in extract(extractor, root, sdk, []):
        writer.store(record)
    db.commit()
    counts = [db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("files", "symbols", "refs")]
    db.close()
    os.replace(temporary, index_path(root))
    print(
        f"codemap: {counts[0]} files, {counts[1]} symbols, {counts[2]} refs "
        f"in {time.time() - started:.1f} s -> {index_path(root)}"
    )
    return 0


def refresh(root):
    if not os.path.isfile(index_path(root)):
        return build(root, if_missing=True)
    lock = open_lock(root)
    dirty = os.path.join(index_dir(root), "dirty")
    if not take_lock(lock, blocking=False):
        open(dirty, "w").close()
        return 0
    sdk = sdk_path(root)
    extractor = extractor_path(sdk)
    while True:
        if os.path.exists(dirty):
            os.remove(dirty)
        refresh_pass(root, sdk, extractor)
        if not os.path.exists(dirty):
            return 0


def refresh_pass(root, sdk, extractor):
    db = connect(index_path(root))
    roots = json.loads(meta(db, "roots") or "[]")
    mtimes = source_mtimes(root, roots)
    known = {path: (digest, mtime, uri) for path, digest, mtime, uri in db.execute("SELECT path, hash, mtime, uri FROM files")}
    deleted = [path for path in known if path not in mtimes]
    touched = [path for path, (_, mtime, _) in known.items() if path in mtimes and mtime != mtimes[path]]
    changed = [path for path in touched if is_changed(root, path, known[path][0])]
    created = [path for path in mtimes if path not in known]
    db.executemany("UPDATE files SET mtime = ? WHERE path = ?", [(mtimes[path], path) for path in touched])
    if not (deleted or changed or created):
        db.commit()
        db.close()
        return
    touched_uris = sorted({known[path][2] for path in deleted + changed if known[path][2]})
    marks = ",".join("?" * len(touched_uris))
    dependents = [
        row[0]
        for row in db.execute(
            "SELECT DISTINCT f.path FROM refs r JOIN ids i ON i.key = r.target JOIN files f ON f.id = r.file"
            f" WHERE substr(i.id, 1, instr(i.id, '#') - 1) IN ({marks})",
            touched_uris,
        )
    ]
    targets = sorted((set(changed) | set(created) | set(dependents)) - set(deleted))
    writer = Writer(db, root, mtimes)
    for path in deleted + targets:
        writer.drop(path)
    if targets:
        for record in extract(extractor, root, sdk, targets):
            writer.store(record)
    db.execute(
        "DELETE FROM symbols WHERE file NOT IN (SELECT id FROM files WHERE analyzed = 1)"
        " AND key NOT IN (SELECT target FROM refs)"
    )
    db.execute("DELETE FROM ids WHERE key NOT IN (SELECT key FROM symbols) AND key NOT IN (SELECT target FROM refs)")
    db.commit()
    db.close()


def is_changed(root, path, digest):
    import hashlib

    with open(os.path.join(root, path), "rb") as source:
        return hashlib.md5(source.read()).hexdigest() != digest


def source_mtimes(root, roots):
    mtimes = {}
    for code_dir in roots:
        for directory, names, files in os.walk(os.path.join(root, code_dir)):
            names[:] = [name for name in names if not name.startswith(".")]
            for name in files:
                if name.endswith(".dart"):
                    path = os.path.join(directory, name)
                    mtimes[os.path.relpath(path, root)] = os.stat(path).st_mtime_ns
    return mtimes


class Writer:
    """Writes extractor records, with files and symbol ids kept as integer keys."""

    def __init__(self, db, root, mtimes):
        self.db = db
        self.root = root
        self.mtimes = mtimes
        self.file_keys = {}
        self.id_keys = {}

    def store(self, record):
        if "roots" in record:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES ('roots', ?)", (json.dumps(record["roots"]),))
            return
        path = record["path"]
        if not record.get("external"):
            self.store_file(record)
        file_key = self.file_key(path)
        self.db.executemany(
            "INSERT OR REPLACE INTO symbols VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (self.id_key(d["id"]), d["name"], d["kind"], d["container"], file_key, d["line"], d["signature"], json.dumps(d["supertypes"]))
                for d in record.get("decls", [])
            ],
        )
        self.db.executemany(
            "INSERT INTO refs VALUES (?, ?, ?, ?)",
            [(self.id_key(r["target"]), file_key, r["line"], r["text"]) for r in record.get("refs", [])],
        )

    def store_file(self, record):
        path = record["path"]
        mtime = self.mtimes.get(path) or os.stat(os.path.join(self.root, path)).st_mtime_ns
        self.db.execute(
            "INSERT INTO files(path, hash, mtime, uri, analyzed) VALUES (?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE"
            " SET hash = excluded.hash, mtime = excluded.mtime, uri = excluded.uri, analyzed = excluded.analyzed",
            (path, record["hash"], mtime, record.get("uri"), 0 if record.get("skipped") else 1),
        )

    def file_key(self, path):
        if path not in self.file_keys:
            self.db.execute("INSERT OR IGNORE INTO files(path, analyzed) VALUES (?, 0)", (path,))
            self.file_keys[path] = self.db.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()[0]
        return self.file_keys[path]

    def id_key(self, symbol_id):
        if symbol_id not in self.id_keys:
            self.db.execute("INSERT OR IGNORE INTO ids(id) VALUES (?)", (symbol_id,))
            self.id_keys[symbol_id] = self.db.execute("SELECT key FROM ids WHERE id = ?", (symbol_id,)).fetchone()[0]
        return self.id_keys[symbol_id]

    def drop(self, path):
        row = self.db.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
        self.file_keys.pop(path, None)
        if row is None:
            return
        self.db.execute("DELETE FROM symbols WHERE file = ?", row)
        self.db.execute("DELETE FROM refs WHERE file = ?", row)
        self.db.execute("DELETE FROM files WHERE id = ?", row)


def meta(db, key):
    row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def connect(path):
    import sqlite3

    return sqlite3.connect(path, timeout=10)


def open_lock(root):
    os.makedirs(index_dir(root), exist_ok=True)
    ignore = os.path.join(index_dir(root), ".gitignore")
    if not os.path.isfile(ignore):
        with open(ignore, "w") as handle:
            handle.write("*\n")
    return open(os.path.join(index_dir(root), "lock"), "w")


def take_lock(lock, blocking):
    import fcntl

    try:
        fcntl.flock(lock, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
    except BlockingIOError:
        return False
    return True


def extract(extractor, root, sdk, files):
    import subprocess

    command = [extractor, root, sdk, "--cache", os.path.join(index_dir(root), "cache"), *files]
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
        for line in process.stdout:
            yield json.loads(line)
    if process.returncode:
        raise RuntimeError(f"codemap: extractor exited with {process.returncode}")


def sdk_path(root):
    fvm = os.path.join(root, FVM_SDK)
    if os.path.isfile(os.path.join(fvm, "version")):
        return fvm
    import shutil

    dart = shutil.which("dart")
    if dart is None:
        raise RuntimeError("codemap: no Dart SDK")
    bin_dir = os.path.dirname(os.path.realpath(dart))
    for candidate in (os.path.join(bin_dir, "cache", "dart-sdk"), os.path.dirname(bin_dir)):
        if os.path.isfile(os.path.join(candidate, "version")):
            return candidate
    raise RuntimeError(f"codemap: no SDK next to {dart}")


def extractor_path(sdk):
    import hashlib

    with open(os.path.join(sdk, "version")) as handle:
        version = handle.read().strip()
    source_hash = hashlib.sha1(b"".join(read_bytes(os.path.join(EXTRACTOR_DIR, name)) for name in EXTRACTOR_SOURCES)).hexdigest()
    bin_dir = os.path.join(CACHE_DIR, "bin", version)
    executable = os.path.join(bin_dir, "codemap_dart")
    stamp = os.path.join(bin_dir, "source.sha1")
    if is_current(executable, stamp, source_hash):
        return executable
    os.makedirs(bin_dir, exist_ok=True)
    with open(os.path.join(bin_dir, "lock"), "w") as lock:
        take_lock(lock, blocking=True)
        if not is_current(executable, stamp, source_hash):
            compile_extractor(sdk, version, executable)
            with open(stamp, "w") as handle:
                handle.write(source_hash)
    return executable


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def is_current(executable, stamp, source_hash):
    if not (os.path.isfile(executable) and os.path.isfile(stamp)):
        return False
    with open(stamp) as handle:
        return handle.read().strip() == source_hash


def compile_extractor(sdk, version, executable):
    import shutil
    import subprocess

    source = os.path.join(CACHE_DIR, "src", version)
    os.makedirs(os.path.join(source, "bin"), exist_ok=True)
    for name in EXTRACTOR_SOURCES:
        shutil.copyfile(os.path.join(EXTRACTOR_DIR, name), os.path.join(source, name))
    dart = os.path.join(sdk, "bin", "dart")
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    offline = subprocess.run([dart, "pub", "get", "--offline"], cwd=source, check=False, **quiet)
    if offline.returncode:
        subprocess.run([dart, "pub", "get"], cwd=source, check=True, **quiet)
    temporary = executable + ".tmp"
    subprocess.run(
        [dart, "compile", "exe", os.path.join("bin", "codemap_dart.dart"), "-o", temporary],
        cwd=source,
        check=True,
        **quiet,
    )
    os.replace(temporary, executable)


# show


def show_text(index, name):
    if not os.path.isfile(index):
        return ""
    db = connect(index)
    try:
        return symbol_answer(db, name)
    finally:
        db.close()


def symbol_answer(db, name):
    declarations = find_declarations(db, name)
    if not declarations:
        return ""
    if len(declarations) > LISTED_DECLARATIONS:
        return declaration_list(name, declarations)
    return clip_answer(declarations, without_repeated_chains([declaration_lines(db, row) for row in declarations]))


def without_repeated_chains(blocks):
    shown = set()
    kept_blocks = []
    for lines in blocks:
        kept = [line for line in lines if not (is_chain_line(line) and line.strip() in shown)]
        shown.update(line.strip() for line in kept if is_chain_line(line))
        if kept and kept[-1] == "  called through:":
            kept.pop()
        kept_blocks.append(kept)
    return kept_blocks


def clip_answer(declarations, blocks):
    limit = SYMBOL_LIMIT
    answer = "\n\n".join("\n".join(lines) for lines in blocks)
    if len(answer) <= limit:
        return answer
    kept = []
    for index, lines in enumerate(blocks):
        cut = narrow_line(len(blocks) - index, declarations[index]) if len(blocks) > 1 else CUT_LINE.format(limit=limit)
        for line in ([""] if kept else []) + lines:
            if len("\n".join(kept + [line, cut])) > limit:
                return "\n".join(kept + [cut])
            kept.append(line)
    return answer


def find_declarations(db, name):
    columns = "id, name, kind, container, file, line, signature, supertypes"
    container, _, member = name.rpartition(".")
    if container:
        query = f"SELECT {columns} FROM symbol_rows WHERE name = ? AND container = ? ORDER BY file, line"
        return db.execute(query, (member, container)).fetchall()
    query = f"SELECT {columns} FROM symbol_rows WHERE name = ? ORDER BY file LIKE 'lib/%' DESC, file, line"
    return db.execute(query, (name,)).fetchall()


def declaration_list(name, declarations):
    lines = [f"{name}: {len(declarations)} declarations"]
    for index, row in enumerate(declarations):
        line = f"  {row[2]} {qualified(row)}  {row[4]}:{row[5]}"
        more = narrow_line(len(declarations) - index, row)
        if len("\n".join(lines + [line, more])) > LIST_LIMIT:
            lines.append(more)
            break
        lines.append(line)
    return "\n".join(lines)


def narrow_line(remaining, row):
    if not row[3]:
        return f"  ... {remaining} more"
    return f"  ... {remaining} more, narrow: {script_command()} show {qualified(row)}"


def script_command():
    script = os.path.join(SKILL_DIR, "codemap.py")
    home = os.path.expanduser("~")
    shown = "~" + script[len(home) :] if script.startswith(home + os.sep) else script
    return f"python3 {shown}"


def qualified(row):
    return f"{row[3]}.{row[1]}" if row[3] else row[1]


def declaration_lines(db, row):
    symbol_id, _, kind, _, file, line, signature, supertypes = row
    lines = [f"{kind} {qualified(row)}  {file}:{line}", f"  {signature}"]
    parents = [target.rsplit("#", 1)[-1] for target in json.loads(supertypes or "[]")]
    if parents:
        lines.append("  supertypes: " + ", ".join(parents))
    children = db.execute(
        "SELECT name, file, line FROM symbol_rows WHERE supertypes LIKE ? ORDER BY file, line",
        (f'%"{symbol_id}"%',),
    ).fetchall()
    if children:
        shown = ", ".join(name for name, _, _ in children[:SUBTYPE_LIMIT])
        rest = f" (+{len(children) - SUBTYPE_LIMIT})" if len(children) > SUBTYPE_LIMIT else ""
        lines.append(f"  subtypes: {shown}{rest}")
    overrides = member_overrides(db, symbol_id, row[1], row[3])
    if overrides:
        lines.append("  overridden in: " + ", ".join(f"{owner} {path}:{number}" for owner, path, number in overrides[:3]))
    lines += use_lines(db, symbol_id, {(path, number) for _, path, number in children})
    if kind in CALLABLE_KINDS:
        lines += callee_lines(db, row) + caller_chain_lines(db, row)
    return lines


def callee_lines(db, row):
    file, line = row[4], row[5]
    end = db.execute(
        f"SELECT MIN(line) FROM symbol_rows WHERE file = ? AND line > ? AND kind IN ({marks(CALLABLE_KINDS + ('field',))})",
        (file, line, *CALLABLE_KINDS, "field"),
    ).fetchone()[0]
    rows = db.execute(
        f"SELECT s.id, s.name, s.container, s.file, s.line, r.text FROM ref_rows r JOIN symbol_rows s ON s.id = r.target"
        f" WHERE r.file = ? AND r.line > ? AND r.line < ? AND s.kind IN ({marks(CALLABLE_KINDS)}) ORDER BY r.line",
        (file, line, end or 1 << 30, *CALLABLE_KINDS),
    ).fetchall()
    callees = list(
        dict.fromkeys(
            (f"{container}.{name}" if container else name, f"{path}:{number}")
            for symbol_id, name, container, path, number, text in rows
            if symbol_id != row[0] and not is_comment(text) and not (container or "").startswith("_$")
        )
    )
    if not callees:
        return []
    lines = ["  calls:"] + [f"    {name}  {location}" for name, location in callees[:CALLEE_LIMIT]]
    if len(callees) > CALLEE_LIMIT:
        lines.append(f"    ... {len(callees) - CALLEE_LIMIT} more")
    return lines


def caller_chain_lines(db, row):
    lines = []
    append_callers(db, row, 0, {row[0]}, lines)
    return ["  called through:"] + lines if lines else []


def append_callers(db, row, depth, seen, lines):
    callers = [(caller, number) for caller, number in production_callers(db, row) if caller[0] not in seen]
    for index, (caller, number) in enumerate(callers):
        indent = "    " + " " * depth
        if index == CHAIN_BRANCHES or len(lines) == CHAIN_NODES:
            lines.append(f"{indent}<- ... {len(callers) - index} more")
            return
        seen.add(caller[0])
        lines.append(f"{indent}<- {qualified(caller)}  {caller[4]}:{number}")
        if depth + 1 < CHAIN_DEPTH:
            append_callers(db, caller, depth + 1, seen, lines)


def production_callers(db, row):
    targets = [row[0]] + interface_member_ids(db, row)
    rows = db.execute(
        f"SELECT file, line, text FROM ref_rows WHERE target IN ({marks(targets)}) ORDER BY file, line",
        targets,
    ).fetchall()
    callers = {}
    for path, number, text in rows:
        if NON_PRODUCTION.search(path) or is_comment(text):
            continue
        caller = enclosing_member(db, path, number)
        if caller is not None and caller[0] != row[0]:
            callers.setdefault(caller[0], (caller, number))
    return list(callers.values())


def interface_member_ids(db, row):
    if not row[3]:
        return []
    container_id = row[0].rsplit(".", 1)[0]
    found = db.execute("SELECT supertypes FROM symbol_rows WHERE id = ?", (container_id,)).fetchone()
    candidates = [f"{parent}.{row[1]}" for parent in json.loads((found or ["[]"])[0] or "[]")]
    if not candidates:
        return []
    return [r[0] for r in db.execute(f"SELECT id FROM ids WHERE id IN ({marks(candidates)})", candidates)]


def enclosing_member(db, path, number):
    return db.execute(
        "SELECT id, name, kind, container, file, line, signature, supertypes FROM symbol_rows"
        f" WHERE file = ? AND line <= ? AND kind IN ({marks(CALLABLE_KINDS)}) ORDER BY line DESC LIMIT 1",
        (path, number, *CALLABLE_KINDS),
    ).fetchone()


def use_owner(db, path, number, text):
    caller = annotated_member(db, path, number) if ANNOTATION_LINE.fullmatch(text.strip()) else None
    return caller or enclosing_member(db, path, number)


def short_body_lines(db, member):
    path, start = member[4], member[5]
    end = db.execute("SELECT MIN(line) FROM symbol_rows WHERE file = ? AND line > ?", (path, start)).fetchone()[0]
    root = os.path.dirname(os.path.dirname(db.execute("PRAGMA database_list").fetchone()[2]))
    try:
        with open(os.path.join(root, path)) as source:
            text = source.read().split("\n")
    except OSError:
        return []
    first = start - 1
    while first > 0 and text[first - 1].strip().startswith("@"):
        first -= 1
    body = text[first : (end - 1 if end else len(text))]
    while body and not body[-1].strip():
        body.pop()
    if len(body) > BODY_LINES:
        body = declaration_head(body)
    shown = body[:BODY_LINES] + ([CUT_MARK] if len(body) > BODY_LINES and body[BODY_LINES - 1] != CUT_MARK else [])
    return ["      ..." if line == CUT_MARK else f"      {first + 1 + offset}| {line.strip()}" for offset, line in enumerate(shown)]


def declaration_head(body):
    for index, line in enumerate(body):
        if line.rstrip().endswith(("{", "=>", ";")) and not line.strip().startswith("@"):
            return body[: index + 1] + [CUT_MARK]
    return []


def annotated_member(db, path, number):
    return db.execute(
        "SELECT id, name, kind, container, file, line, signature, supertypes FROM symbol_rows"
        f" WHERE file = ? AND line > ? AND line <= ? AND kind IN ({marks(CALLABLE_KINDS)}) ORDER BY line LIMIT 1",
        (path, number, number + ANNOTATION_SPAN, *CALLABLE_KINDS),
    ).fetchone()


def is_chain_line(line):
    return line.lstrip().startswith("<- ")


def is_comment(text):
    return text.lstrip().startswith("//")


def marks(values):
    return ",".join("?" * len(values))


def member_overrides(db, symbol_id, name, container):
    if not container:
        return []
    container_id = symbol_id.rsplit(".", 1)[0]
    return db.execute(
        "SELECT container, file, line FROM symbol_rows WHERE name = ? AND container IN"
        " (SELECT name FROM symbol_rows WHERE supertypes LIKE ?) ORDER BY file, line",
        (name, f'%"{container_id}"%'),
    ).fetchall()


def use_lines(db, symbol_id, subtype_lines):
    rows = db.execute(
        "SELECT file, line, text FROM ref_rows WHERE target = ? ORDER BY file LIKE 'lib/%' DESC, file, line",
        (symbol_id,),
    ).fetchall()
    rows = [row for row in rows if row[:2] not in subtype_lines and not is_comment(row[2])]
    rows.sort(key=lambda row: (not row[0].startswith("lib/"), bool(NON_PRODUCTION.search(row[0]))))
    label = "other uses" if subtype_lines else "uses"
    if not rows:
        return [f"  {label}: none"]
    files = len({path for path, _, _ in rows})
    count = f"all {len(rows)} shown" if len(rows) <= USE_LIMIT else f"{len(rows)} in {files} files"
    lines = [f"  {label}: {count}"]
    bodies = 0
    for path, number, text in rows[:USE_LIMIT]:
        caller = use_owner(db, path, number, text)
        label_text = f" in {qualified(caller)}" if caller else ""
        lines.append(f"    {path}:{number}{label_text}  {text[:USE_TEXT_LIMIT]}")
        if caller and bodies < BODY_USES:
            body = short_body_lines(db, caller)
            bodies += 1 if body else 0
            lines += body
    if len(rows) > USE_LIMIT:
        lines.append(f"    ... {len(rows) - USE_LIMIT} more")
    return lines


# map


def map_text(index, budget):
    if not os.path.isfile(index):
        return ""
    db = connect(index)
    try:
        return project_map(db, budget * 4)
    finally:
        db.close()


def project_map(db, limit):
    files = [
        row[0]
        for row in db.execute("SELECT path FROM files WHERE analyzed = 1 AND path NOT LIKE 'test/%' ORDER BY path")
    ]
    ranks = pagerank(files, file_edges(db))
    text = MAP_HEADER
    for path in sorted(files, key=lambda path: (-round(ranks[path], 12), path)):
        blocks = file_blocks(db, path)
        if not blocks:
            continue
        full, short = blocks
        block = full if len(text) + len(full) <= limit * MAP_DETAILED_SHARE else short
        if len(text) + len(block) > limit:
            break
        text += block
    return text.rstrip("\n")


def file_edges(db):
    weights = {
        (source, target): count
        for source, target, count in db.execute(
            "SELECT source.path, target.path, COUNT(*) FROM refs r JOIN symbols s ON s.key = r.target"
            " JOIN files source ON source.id = r.file JOIN files target ON target.id = s.file"
            " WHERE r.file != s.file GROUP BY r.file, s.file"
        )
    }
    files_by_id = dict(db.execute("SELECT id, file FROM symbol_rows"))
    for path, supertypes in db.execute("SELECT file, supertypes FROM symbol_rows WHERE supertypes != '[]'"):
        for target in json.loads(supertypes):
            target_path = files_by_id.get(target)
            if target_path and target_path != path:
                weights[(path, target_path)] = weights.get((path, target_path), 0) + SUPERTYPE_WEIGHT
    return [(source, target, weight) for (source, target), weight in sorted(weights.items())]


def pagerank(files, edges):
    nodes = set(files)
    outgoing = {}
    for source, target, weight in edges:
        if source in nodes and target in nodes:
            outgoing.setdefault(source, []).append((target, weight))
    count = len(files)
    rank = {path: 1.0 / count for path in files}
    for _ in range(PAGERANK_ITERATIONS):
        dangling = sum(rank[path] for path in files if path not in outgoing)
        base = (1 - PAGERANK_DAMPING) / count + PAGERANK_DAMPING * dangling / count
        following = {path: base for path in files}
        for source, targets in outgoing.items():
            total = sum(weight for _, weight in targets)
            for target, weight in targets:
                following[target] += PAGERANK_DAMPING * rank[source] * weight / total
        rank = following
    return rank


def file_blocks(db, path):
    marks = ",".join("?" * len(TYPE_KINDS))
    types = db.execute(
        f"SELECT name, signature FROM symbol_rows WHERE file = ? AND kind IN ({marks})"
        " AND name NOT LIKE '\\_%' ESCAPE '\\' ORDER BY line",
        (path, *TYPE_KINDS),
    ).fetchall()
    if not types:
        return []
    full = [path]
    short = [path]
    for name, signature in types:
        full.append(f"  {signature}")
        short.append(f"  {signature}")
        full += [f"    {member}" for member in public_members(db, path, name)]
    return ["\n".join(full) + "\n", "\n".join(short) + "\n"]


def public_members(db, path, container):
    marks = ",".join("?" * len(MEMBER_KINDS))
    rows = db.execute(
        "SELECT s.signature FROM symbols s JOIN files f ON f.id = s.file"
        f" WHERE f.path = ? AND s.container = ? AND s.kind IN ({marks}) AND s.name NOT LIKE '\\_%' ESCAPE '\\'"
        " ORDER BY (SELECT COUNT(*) FROM refs r WHERE r.target = s.key) DESC, s.line LIMIT ?",
        (path, container, *MEMBER_KINDS, MAP_MEMBER_LIMIT),
    ).fetchall()
    return [row[0] for row in rows]


# hook


def hook(payload):
    if os.environ.get("CODEMAP_HOOK") == "off":
        return
    event = payload.get("hook_event_name")
    if event in ("SessionStart", "SubagentStart"):
        start_session(payload, event)
        return
    if event == "PostToolUse":
        after_edit(payload)
        after_read(payload)
        return
    if event == "UserPromptSubmit":
        answer_prompt(payload)
        return
    if event != "PreToolUse":
        return
    search = searched(payload)
    if search is None:
        answer_reads(payload, "PreToolUse", sed_reads(payload))
        return
    names, path = search
    root = find_root(path)
    if root is None:
        return
    if not os.path.isfile(index_path(root)):
        spawn("build", root, "--if-missing")
        return
    if is_silent_session(payload):
        log_decision(root, payload, names, [], "silent")
        return
    answer_search(payload, root, names)


def start_session(payload, event):
    if os.environ.get("CODEMAP_MAP") != "1":
        return
    root = find_root(str(payload.get("cwd") or os.getcwd()))
    if root is None:
        return
    text = map_text(index_path(root), MAP_BUDGET)
    if text:
        emit(event, text)


def after_edit(payload):
    if payload.get("tool_name") not in EDIT_TOOLS:
        return
    path = str(payload.get("tool_input", {}).get("file_path") or "")
    if not path.endswith(".dart"):
        return
    root = find_root(os.path.dirname(os.path.join(str(payload.get("cwd") or ""), path)))
    if root is not None and os.path.isfile(index_path(root)):
        spawn("refresh", root)


def answer_search(payload, root, names):
    import sqlite3

    db = sqlite3.connect(f"file:{index_path(root)}?mode=ro", uri=True, timeout=0.2)
    try:
        if is_stale(db, root):
            spawn("refresh", root)
        seen = seen_names(root, payload)
        answers = symbol_answers(db, [name for name in names if name not in seen], keeps_lists=True)
    finally:
        db.close()
    log_decision(root, payload, names, list(answers), "hook")
    text = ""
    if answers:
        remember_names(root, payload, seen, answers)
        header = HOOK_HEADER.format(names=", ".join(f"`{name}`" for name in answers))
        text = clip_lines(header + "\n\n".join(answers.values()), HOOK_LIMIT)
    reads = read_context_text(sed_reads(payload))
    if text or reads:
        emit("PreToolUse", "\n\n".join(part for part in (text, reads) if part))


def after_read(payload):
    if payload.get("tool_name") != "Read":
        return
    tool_input = payload.get("tool_input", {})
    path = absolute(str(payload.get("cwd") or os.getcwd()), str(tool_input.get("file_path") or ""))
    start = int(tool_input.get("offset") or 1)
    answer_reads(payload, "PostToolUse", [(path, start, start + int(tool_input.get("limit") or READ_LINES) - 1)])


def answer_reads(payload, event, reads):
    text = read_context_text(reads)
    if text:
        emit(event, text)


def sed_reads(payload):
    if payload.get("tool_name") != "Bash":
        return []
    cwd = str(payload.get("cwd") or os.getcwd())
    names = {}
    reads = []
    segments = raw_segments(str(payload.get("tool_input", {}).get("command") or ""))
    for index, (operator, tokens) in enumerate(segments):
        tokens = [expand_names(token, names) for token in tokens]
        files = [absolute(cwd, token) for token in tokens[1:] if token.endswith(".dart")]
        is_piped_out = index + 1 < len(segments) and segments[index + 1][0] == "|"
        if SHELL_ASSIGNMENT.fullmatch(tokens[0]) and len(tokens) == 1:
            name, _, value = tokens[0].partition("=")
            names[name] = value
        elif tokens[0] == "cd" and len(tokens) > 1:
            cwd = absolute(cwd, tokens[1])
        elif tokens[0] == "cat" and not is_piped_out:
            reads += [(path, 1, READ_LINES) for path in files]
        elif tokens[0] == "sed" and "-n" in tokens:
            ranges = [match for match in map(SED_RANGE.fullmatch, tokens[1:]) if match]
            sources = files or (piped_files(segments[index - 1][1], names, cwd) if operator == "|" else [])
            reads += [(path, int(match.group(1)), int(match.group(2))) for match in ranges[:1] for path in sources]
    return reads


def piped_files(tokens, names, cwd):
    if tokens[0] != "cat":
        return []
    return [absolute(cwd, expand_names(token, names)) for token in tokens[1:] if token.endswith(".dart")]


def expand_names(token, names):
    return SHELL_NAME.sub(lambda match: names.get(match.group(1) or match.group(2), match.group(0)), token)


def read_context_text(reads):
    import sqlite3

    blocks = []
    for path, start, end in reads[:READ_FILE_LIMIT]:
        root = find_root(os.path.dirname(path)) if path.endswith(".dart") else None
        if root is None or not os.path.isfile(index_path(root)):
            continue
        db = sqlite3.connect(f"file:{index_path(root)}?mode=ro", uri=True, timeout=0.2)
        try:
            block = used_declarations(db, os.path.relpath(path, root), start, end)
        finally:
            db.close()
        if block:
            blocks.append(block)
    return "\n\n".join(blocks)


def used_declarations(db, path, start, end):
    rows = db.execute(
        "SELECT s.name, s.container, s.file, s.line FROM ref_rows r JOIN symbol_rows s ON s.id = r.target"
        f" WHERE r.file = ? AND r.line BETWEEN ? AND ? AND s.file != ? AND s.file NOT LIKE 'package:%'"
        f" AND s.kind IN ({marks(READ_KINDS)}) ORDER BY r.line",
        (path, start, end, path, *READ_KINDS),
    ).fetchall()
    used = list(
        dict.fromkeys(
            (f"{container}.{name}" if container else name, f"{file}:{line}")
            for name, container, file, line in rows
            if not (container or name).startswith("_$") and not GENERATED_FILE.search(file)
        )
    )
    if not used:
        return ""
    lines = [f"codemap: lines {start}-{end} of {path} use these declarations of other files:"]
    lines += [f"  {name}  {location}" for name, location in used[:READ_REF_LIMIT]]
    if len(used) > READ_REF_LIMIT:
        lines.append(f"  ... {len(used) - READ_REF_LIMIT} more")
    return "\n".join(lines)


def answer_prompt(payload):
    names = prompt_identifiers(str(payload.get("prompt") or ""))
    root = find_root(str(payload.get("cwd") or os.getcwd()))
    if not names or root is None or not os.path.isfile(index_path(root)):
        return
    if is_silent_session(payload):
        return
    import sqlite3

    db = sqlite3.connect(f"file:{index_path(root)}?mode=ro", uri=True, timeout=0.2)
    try:
        is_current = not is_stale(db, root)
        seen = seen_names(root, payload)
        answers = symbol_answers(db, [name for name in names if name not in seen], keeps_lists=False)
    finally:
        db.close()
    if answers:
        remember_names(root, payload, seen, answers)
        header = (CURRENT_PROMPT_HEADER if is_current else PROMPT_HEADER).format(names=", ".join(f"`{name}`" for name in answers))
        emit("UserPromptSubmit", clip_lines(header + "\n\n".join(answers.values()), HOOK_LIMIT))


def symbol_answers(db, names, keeps_lists):
    answers = {}
    for name in names[:HOOK_CANDIDATE_LIMIT]:
        answer = symbol_answer(db, name)
        if answer and (keeps_lists or not answer.startswith(f"{name}: ")):
            answers[name] = answer
        if len(answers) == HOOK_SYMBOL_LIMIT:
            break
    return answers


def prompt_identifiers(prompt):
    quoted = []
    for span in BACKTICK_SPAN.findall(prompt):
        span = span.strip().rstrip("()")
        quoted += [span] if QUALIFIED_NAME.fullmatch(span) else identifiers([span])
    plain = [match.group(0) for match in CLASS_NAME.finditer(BACKTICK_SPAN.sub(" ", prompt))]
    return list(dict.fromkeys(quoted + plain))


def seen_names(root, payload):
    try:
        with open(seen_path(root, payload)) as file:
            return set(json.load(file))
    except (OSError, ValueError):
        return set()


def remember_names(root, payload, seen, answers):
    path = seen_path(root, payload)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    drop_old_sessions(os.path.dirname(path))
    with open(path, "w") as file:
        json.dump(sorted(seen | set(answers) | {name.rpartition(".")[2] for name in answers}), file)


def drop_old_sessions(directory):
    import time

    for entry in os.scandir(directory):
        if entry.stat().st_mtime < time.time() - SEEN_MAX_AGE:
            os.remove(entry.path)


def seen_path(root, payload):
    session = re.sub(r"[^A-Za-z0-9_-]", "_", str(payload.get("session_id") or "none"))
    return os.path.join(index_dir(root), "seen", session)


def clip_lines(text, limit):
    kept = []
    for line in text.split("\n"):
        if len("\n".join(kept + [line])) > limit:
            break
        kept.append(line)
    return "\n".join(kept)


def is_stale(db, root):
    for path, mtime in db.execute("SELECT path, mtime FROM files WHERE mtime IS NOT NULL"):
        try:
            if os.stat(os.path.join(root, path)).st_mtime_ns != mtime:
                return True
        except FileNotFoundError:
            return True
    return False


def emit(event, context):
    json.dump({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}, sys.stdout)


def spawn(*arguments):
    import subprocess

    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def is_silent_session(payload):
    if os.environ.get("CODEMAP_AB") != "1":
        return False
    import zlib

    return zlib.crc32(str(payload.get("session_id") or "").encode()) % 2 == 0


def log_decision(root, payload, names, answered, group):
    if os.environ.get("CODEMAP_AB") != "1":
        return
    import time

    entry = {
        "time": int(time.time()),
        "session_id": payload.get("session_id"),
        "agent": "codex" if is_codex(payload) else "claude",
        "group": group,
        "names": names,
        "answered": answered,
    }
    with open(os.path.join(index_dir(root), "ab.log"), "a") as log:
        log.write(json.dumps(entry) + "\n")


def is_codex(payload):
    return "turn_id" in payload


def searched(payload):
    tool_input = payload.get("tool_input", {})
    cwd = str(payload.get("cwd") or os.getcwd())
    tool_name = payload.get("tool_name")
    if tool_name == "Grep":
        names = identifiers([str(tool_input.get("pattern") or "")])
        path = str(tool_input.get("path") or "")
        return (names, absolute(cwd, path)) if names else None
    if tool_name != "Bash":
        return None
    for operator, tokens in raw_segments(str(tool_input.get("command") or "")):
        search = searched_in_segment(operator, tokens, cwd)
        if search is not None:
            return search
    return None


def searched_in_segment(operator, tokens, cwd):
    name, arguments = search_arguments(tokens)
    if name not in SEARCH_TOOLS:
        return None
    patterns, paths = split_arguments(arguments)
    if not paths and (operator == "|" or name not in DIRECTORY_SEARCHES):
        return None
    names = identifiers(patterns)
    if not names:
        return None
    return names, absolute(cwd, paths[0] if paths else "")


def absolute(cwd, path):
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))


def identifiers(patterns):
    text = " ".join(REGEX_ESCAPE.sub(" ", pattern) for pattern in patterns)
    found = [match.group(0) for regex in (CLASS_NAME, MEMBER_NAME) for match in regex.finditer(text)]
    return list(dict.fromkeys(found))


def search_arguments(tokens):
    for index, token in enumerate(tokens):
        name = token.rsplit("/", 1)[-1]
        if is_prefix_token(token, name):
            continue
        if name == "git":
            is_grep = tokens[index + 1 : index + 2] == ["grep"]
            return ("git grep", tokens[index + 2 :]) if is_grep else (None, [])
        return name, tokens[index + 1 :]
    return None, []


def is_prefix_token(token, name):
    is_assignment = "=" in token and not token.startswith("-")
    is_prefix = name in COMMAND_WRAPPERS or name in SHELL_KEYWORDS
    return is_assignment or is_prefix or token.startswith("-")


def split_arguments(arguments):
    patterns = []
    positional = []
    expects_value = None
    for token in arguments:
        if expects_value is not None:
            if expects_value in PATTERN_OPTIONS:
                patterns.append(token)
            expects_value = None
            continue
        if token in VALUE_OPTIONS:
            expects_value = token
            continue
        if token.startswith("-"):
            continue
        positional.append(token)
    if not patterns and positional:
        patterns.append(positional.pop(0))
    return patterns, positional


def raw_segments(command):
    lines = drop_heredoc_bodies(command).split("\n")
    tokens = [token for line in lines for token in shell_tokens(line) + [";"]]
    segments = [(None, [])]
    for token in tokens:
        if SHELL_OPERATOR.fullmatch(token):
            segments.append((token, []))
            continue
        segments[-1][1].append(token)
    return [(operator, tokens) for operator, tokens in segments if tokens]


def drop_heredoc_bodies(command):
    kept = []
    terminator = None
    for line in command.split("\n"):
        if terminator is not None:
            terminator = None if line.strip() == terminator else terminator
            continue
        kept.append(line)
        opener = HEREDOC_OPEN.search(line)
        terminator = opener.group(1) if opener else None
    return "\n".join(kept)


def shell_tokens(line):
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return SHELL_WORD.findall(line)


if __name__ == "__main__":
    if sys.argv[1:2] == ["hook"]:
        try:
            main(sys.argv[1:])
        except Exception:
            pass
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
