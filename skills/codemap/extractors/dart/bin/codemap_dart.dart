// Prints one JSON line per Dart file of a project: its declarations and the
// references it makes to declarations of the same project.
//
// Usage: codemap_dart <root> <sdk> [--cache <dir>] [file...]
//
// The first line names the analyzed directories: `{"roots": [...]}`. Then each
// analyzed file gives `{path, hash, uri, decls, refs}`. A file under those
// directories that the analysis options exclude gives `{path, hash, uri,
// skipped: true}`. A declaration of such a file that a reference resolves to
// comes from the resolved element and closes the output, grouped by file as
// `{path, external: true, decls}`. Without a file list every file is printed.
import 'dart:convert';
import 'dart:io';

import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/token.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/dart/element/element.dart';
import 'package:analyzer/file_system/physical_file_system.dart';
import 'package:analyzer/source/line_info.dart';
import 'package:analyzer/src/dart/analysis/analysis_context_collection.dart';
import 'package:analyzer/src/dart/analysis/byte_store.dart';
import 'package:analyzer/src/dart/analysis/file_byte_store.dart';
import 'package:crypto/crypto.dart';

const _codeDirectories = ['lib', 'test'];
const _signatureLimit = 200;
const _textLimit = 120;

Future<void> main(List<String> arguments) async {
  final options = _Options.parse(arguments);
  final project = _Project(options.root);
  final collection = AnalysisContextCollectionImpl(
    includedPaths: project.includedPaths,
    excludedPaths: project.excludedPaths(),
    sdkPath: options.sdk,
    resourceProvider: PhysicalResourceProvider.INSTANCE,
    byteStore: _byteStore(options.cache),
  );
  final analyzed = {
    for (final context in collection.contexts)
      ...context.contextRoot.analyzedFiles().where((p) => p.endsWith('.dart')),
  };
  final requested = options.files.isEmpty
      ? project.dartFiles()
      : options.files.map(project.absolute).toSet();
  final externals = _Externals(project);
  stdout.writeln(jsonEncode({'roots': project.relativeRoots}));
  for (final path in requested.toList()..sort()) {
    final record = await _record(
      collection,
      project,
      analyzed,
      externals,
      path,
    );
    if (record != null) {
      stdout.writeln(jsonEncode(record));
    }
  }
  for (final record in externals.records()) {
    stdout.writeln(jsonEncode(record));
  }
  await stdout.flush();
}

ByteStore? _byteStore(String? cache) {
  if (cache == null) {
    return null;
  }
  Directory(cache).createSync(recursive: true);
  return MemoryCachingByteStore(FileByteStore(cache), 64 * 1024 * 1024);
}

Future<Map<String, Object?>?> _record(
  AnalysisContextCollectionImpl collection,
  _Project project,
  Set<String> analyzed,
  _Externals externals,
  String path,
) async {
  final file = File(path);
  if (!file.existsSync()) {
    return null;
  }
  final base = {
    'path': project.relative(path),
    'hash': md5.convert(file.readAsBytesSync()).toString(),
  };
  if (!analyzed.contains(path)) {
    final uri = collection.contexts.first.currentSession.uriConverter.pathToUri(
      path,
    );
    return {
      ...base,
      'uri': uri == null ? null : project.libraryId(_libraryUri(file, uri)),
      'skipped': true,
    };
  }
  final result = await collection
      .contextFor(path)
      .currentSession
      .getResolvedUnit(path);
  if (result is! ResolvedUnitResult) {
    return null;
  }
  final visitor = _UnitVisitor(project, analyzed, externals, result);
  result.unit.accept(visitor);
  return {
    ...base,
    'uri': project.libraryId(result.libraryElement.uri),
    'decls': visitor.declarations..sort(_byLineThenId),
    'refs': visitor.sortedReferences(),
  };
}

Uri _libraryUri(File file, Uri uri) {
  final unit = parseString(
    content: file.readAsStringSync(),
    throwIfDiagnostics: false,
  ).unit;
  for (final directive in unit.directives) {
    final owner = directive is PartOfDirective
        ? directive.uri?.stringValue
        : null;
    if (owner != null) {
      return uri.resolve(owner);
    }
  }
  return uri;
}

class _Options {
  final String root;
  final String sdk;
  final String? cache;
  final List<String> files;

  _Options(this.root, this.sdk, this.cache, this.files);

  factory _Options.parse(List<String> arguments) {
    final rest = [...arguments];
    final root = Directory(rest.removeAt(0)).absolute.path;
    final sdk = rest.removeAt(0);
    String? cache;
    final cacheIndex = rest.indexOf('--cache');
    if (cacheIndex >= 0) {
      cache = rest[cacheIndex + 1];
      rest.removeRange(cacheIndex, cacheIndex + 2);
    }
    return _Options(_trimSlash(root), sdk, cache, rest);
  }
}

String _trimSlash(String path) {
  return path.length > 1 && path.endsWith('/')
      ? path.substring(0, path.length - 1)
      : path;
}

class _Project {
  final String root;
  final String packageName;
  final List<String> includedPaths;

  _Project(this.root)
    : packageName = _packageName(root),
      includedPaths = [
        for (final name in _codeDirectories)
          if (Directory('$root/$name').existsSync()) '$root/$name',
      ];

  List<String> get relativeRoots => includedPaths.map(relative).toList();

  String absolute(String path) {
    return path.startsWith('/') ? path : '$root/$path';
  }

  String relative(String path) {
    return path.startsWith('$root/') ? path.substring(root.length + 1) : path;
  }

  bool ownsLibrary(Uri uri) {
    if (uri.isScheme('package')) {
      return uri.pathSegments.first == packageName;
    }
    if (!uri.isScheme('file')) {
      return false;
    }
    final path = uri.toFilePath();
    return includedPaths.any((directory) => path.startsWith('$directory/'));
  }

  String libraryId(Uri uri) {
    return uri.isScheme('file') ? relative(uri.toFilePath()) : uri.toString();
  }

  List<String> excludedPaths() {
    return [
      for (final directory in includedPaths)
        ..._nestedProjects(Directory(directory)),
    ];
  }

  Set<String> dartFiles() {
    final excluded = excludedPaths();
    return {
      for (final directory in includedPaths)
        for (final entity in Directory(
          directory,
        ).listSync(recursive: true, followLinks: false))
          if (entity is File &&
              entity.path.endsWith('.dart') &&
              !excluded.any((path) => entity.path.startsWith('$path/')))
            entity.path,
    };
  }

  static String _packageName(String root) {
    final pubspec = File('$root/pubspec.yaml');
    if (!pubspec.existsSync()) {
      return '';
    }
    final match = RegExp(
      r'^name:\s*(\S+)',
      multiLine: true,
    ).firstMatch(pubspec.readAsStringSync());
    return match?.group(1) ?? '';
  }

  static Iterable<String> _nestedProjects(Directory directory) sync* {
    for (final entity in directory.listSync(followLinks: false)) {
      if (entity is! Directory) {
        continue;
      }
      if (_isProject(entity)) {
        yield entity.path;
        continue;
      }
      yield* _nestedProjects(entity);
    }
  }

  static bool _isProject(Directory directory) {
    return File('${directory.path}/pubspec.yaml').existsSync() ||
        FileSystemEntity.typeSync('${directory.path}/.git') !=
            FileSystemEntityType.notFound;
  }
}

class _Externals {
  final _Project project;
  final Map<String, Map<String, Map<String, Object?>>> _byFile = {};

  _Externals(this.project);

  void add(Element element, String id) {
    final fragment = element.firstFragment;
    final path = fragment.libraryFragment?.source.fullName;
    if (path == null) {
      return;
    }
    final declarations = _byFile.putIfAbsent(project.relative(path), () => {});
    if (declarations.containsKey(id)) {
      return;
    }
    final lineInfo = fragment.libraryFragment?.lineInfo;
    final offset = fragment.nameOffset ?? fragment.offset;
    declarations[id] = _declaration(
      element,
      project,
      id,
      lineInfo == null ? 0 : lineInfo.getLocation(offset).lineNumber,
      _collapse(element.displayString()),
    );
  }

  Iterable<Map<String, Object?>> records() sync* {
    final files = _byFile.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));
    for (final MapEntry(key: path, value: byId) in files) {
      final declarations = byId.values.toList()..sort(_byLineThenId);
      yield {'path': path, 'external': true, 'decls': declarations};
    }
  }
}

class _UnitVisitor extends GeneralizingAstVisitor<void> {
  final _Project project;
  final Set<String> analyzed;
  final _Externals externals;
  final ResolvedUnitResult result;
  final List<Map<String, Object?>> declarations = [];
  final Map<String, Map<String, Object?>> _references = {};
  final Set<String> _declaredAt = {};

  _UnitVisitor(this.project, this.analyzed, this.externals, this.result);

  LineInfo get _lineInfo => result.lineInfo;

  @override
  void visitDeclaration(Declaration node) {
    _addDeclaration(node);
    super.visitDeclaration(node);
  }

  @override
  void visitSimpleIdentifier(SimpleIdentifier node) {
    if (node.parent is! ConstructorDeclaration) {
      _addReference(node.element, node.offset);
    }
    super.visitSimpleIdentifier(node);
  }

  @override
  void visitNamedType(NamedType node) {
    _addReference(node.element, node.name.offset);
    super.visitNamedType(node);
  }

  @override
  void visitAssignmentExpression(AssignmentExpression node) {
    _addReference(node.writeElement, node.leftHandSide.end - 1);
    super.visitAssignmentExpression(node);
  }

  List<Map<String, Object?>> sortedReferences() {
    final references = _references.values
        .where(
          (reference) => !_declaredAt.contains(
            '${reference['target']}@${reference['line']}',
          ),
        )
        .toList();
    return references..sort(_byLineThenTarget);
  }

  void _addDeclaration(Declaration node) {
    final element = node.declaredFragment?.element;
    if (element == null || _kind(element) == null) {
      return;
    }
    if (element is ConstructorElement && _isUnnamed(element)) {
      return;
    }
    final id = _id(element, project);
    if (id == null) {
      return;
    }
    final line = _line(node.declaredFragment?.nameOffset ?? node.offset);
    _declaredAt.add('$id@$line');
    declarations.add(
      _declaration(element, project, id, line, _signature(node)),
    );
  }

  void _addReference(Element? element, int offset) {
    final target = element == null ? null : _target(element);
    if (target == null) {
      return;
    }
    final id = _id(target, project);
    if (id == null) {
      return;
    }
    if (_isExternal(target)) {
      externals.add(target, id);
    }
    final line = _line(offset);
    _references.putIfAbsent('$id@$line', () {
      return {'target': id, 'line': line, 'text': _sourceLine(line)};
    });
  }

  Element? _target(Element element) {
    final resolved = _declared(element);
    final library = resolved.library;
    if (library == null ||
        !project.ownsLibrary(library.uri) ||
        _kind(resolved) == null) {
      return null;
    }
    return resolved;
  }

  bool _isExternal(Element element) {
    final path = element.firstFragment.libraryFragment?.source.fullName;
    return path != null && !analyzed.contains(path);
  }

  int _line(int offset) {
    return _lineInfo.getLocation(offset).lineNumber;
  }

  String _sourceLine(int line) {
    final start = _lineInfo.getOffsetOfLine(line - 1);
    final end = line < _lineInfo.lineCount
        ? _lineInfo.getOffsetOfLine(line)
        : result.content.length;
    final text = result.content.substring(start, end).trim();
    return text.length > _textLimit ? text.substring(0, _textLimit) : text;
  }

  String _signature(Declaration node) {
    if (node is VariableDeclaration) {
      return _variableSignature(node);
    }
    if (node is EnumConstantDeclaration) {
      return node.name.lexeme;
    }
    final start = node.firstTokenAfterCommentAndMetadata;
    final stop = _signatureStop(
      start,
      node.endToken,
      node is ConstructorDeclaration,
    );
    return _clip(_collapse(result.content.substring(start.offset, stop)));
  }

  String _variableSignature(VariableDeclaration node) {
    final list = node.parent;
    final owner = list?.parent;
    if (list is! VariableDeclarationList || owner is! AnnotatedNode) {
      return node.name.lexeme;
    }
    final prefixEnd = list.type?.end ?? list.keyword?.end;
    if (prefixEnd == null) {
      return node.name.lexeme;
    }
    final prefix = result.content.substring(
      owner.firstTokenAfterCommentAndMetadata.offset,
      prefixEnd,
    );
    return _clip(_collapse('$prefix ${node.name.lexeme}'));
  }

  int _signatureStop(Token start, Token end, bool stopsAtColon) {
    int depth = 0;
    Token token = start;
    while (token != end && !token.isEof) {
      final lexeme = token.lexeme;
      if (depth == 0 && _endsHeader(lexeme, stopsAtColon)) {
        return token.offset;
      }
      if (lexeme == '(' || lexeme == '[' || lexeme == '{') {
        depth++;
      }
      if (lexeme == ')' || lexeme == ']' || lexeme == '}') {
        depth--;
      }
      final next = token.next;
      if (next == null) {
        break;
      }
      token = next;
    }
    return token.offset;
  }

  bool _endsHeader(String lexeme, bool stopsAtColon) {
    return lexeme == '{' ||
        lexeme == '=>' ||
        lexeme == ';' ||
        (stopsAtColon && lexeme == ':');
  }
}

Map<String, Object?> _declaration(
  Element element,
  _Project project,
  String id,
  int line,
  String signature,
) {
  return {
    'id': id,
    'name': _name(element),
    'kind': _kind(element),
    'container': _container(element),
    'line': line,
    'signature': signature,
    'supertypes': _supertypes(element, project),
  };
}

Element _declared(Element element) {
  final base = element.baseElement.nonSynthetic;
  if (base is ConstructorElement && _isUnnamed(base)) {
    return base.enclosingElement;
  }
  return base;
}

bool _isUnnamed(ConstructorElement element) {
  final name = element.name;
  return name == null || name.isEmpty || name == 'new';
}

String? _id(Element element, _Project project) {
  final library = element.library;
  final name = _name(element);
  if (library == null || name == null) {
    return null;
  }
  final container = _container(element);
  final member = container == null ? name : '$container.$name';
  final suffix = switch (element) {
    SetterElement() => '=',
    ConstructorElement() => '()',
    _ => '',
  };
  return '${project.libraryId(library.uri)}#$member$suffix';
}

String? _name(Element element) {
  if (element is ExtensionElement && element.name == null) {
    return 'extension@${element.firstFragment.offset}';
  }
  return element.name;
}

String? _container(Element element) {
  final enclosing = element.enclosingElement;
  return enclosing is InstanceElement ? _name(enclosing) : null;
}

String? _kind(Element element) {
  return switch (element) {
    ClassElement() => 'class',
    MixinElement() => 'mixin',
    EnumElement() => 'enum',
    ExtensionTypeElement() => 'extensionType',
    ExtensionElement() => 'extension',
    TypeAliasElement() => 'typedef',
    TopLevelFunctionElement() => 'function',
    TopLevelVariableElement() => 'variable',
    MethodElement() => 'method',
    GetterElement() => 'getter',
    SetterElement() => 'setter',
    FieldElement(:final isEnumConstant) when isEnumConstant => 'enumConstant',
    FieldElement() => 'field',
    ConstructorElement() => 'constructor',
    _ => null,
  };
}

List<String> _supertypes(Element element, _Project project) {
  final types = switch (element) {
    MixinElement() => [...element.superclassConstraints, ...element.interfaces],
    InterfaceElement() => [
      ?element.supertype,
      ...element.mixins,
      ...element.interfaces,
    ],
    ExtensionElement() => [element.extendedType],
    _ => const [],
  };
  return [
    for (final type in types)
      if (type.element case final typeElement? when !_isImplicit(typeElement))
        if (typeElement.library case final library?)
          '${project.libraryId(library.uri)}#${typeElement.name}',
  ];
}

bool _isImplicit(Element element) {
  final isCore = element.library?.uri.toString() == 'dart:core';
  return isCore && (element.name == 'Object' || element.name == 'Enum');
}

String _collapse(String text) {
  return text.replaceAll(RegExp(r'\s+'), ' ').trim();
}

String _clip(String text) {
  return text.length > _signatureLimit
      ? text.substring(0, _signatureLimit)
      : text;
}

int _byLineThenId(Map<String, Object?> a, Map<String, Object?> b) {
  final line = (a['line'] as int).compareTo(b['line'] as int);
  return line != 0 ? line : (a['id'] as String).compareTo(b['id'] as String);
}

int _byLineThenTarget(Map<String, Object?> a, Map<String, Object?> b) {
  final line = (a['line'] as int).compareTo(b['line'] as int);
  return line != 0
      ? line
      : (a['target'] as String).compareTo(b['target'] as String);
}
