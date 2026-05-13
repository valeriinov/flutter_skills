import 'dart:convert';
import 'dart:io';

void main(List<String> arguments) async {
  final args = _Args.parse(arguments);
  final skillRoot = File(Platform.script.toFilePath()).parent.parent;
  final catalogPath = args.value('catalog') ??
      '${skillRoot.path}/references/dependency_catalog.yaml';
  final outdatedPath = args.value('outdated-json');
  final target = Directory(args.value('target') ?? Directory.current.path);

  final catalog = _DependencyCatalog.read(File(catalogPath));
  final outdatedJson = outdatedPath == null
      ? await _runPubOutdated(target)
      : File(outdatedPath).readAsStringSync();
  final packages = _OutdatedPackages.parse(outdatedJson);
  final report = _DependencyAudit(catalog: catalog, packages: packages).build();

  stdout.writeln(report);
}

Future<String> _runPubOutdated(Directory target) async {
  final command = _resolvePubOutdatedCommand(target);
  final result = await Process.run(
    command.executable,
    command.arguments,
    workingDirectory: target.path,
    runInShell: true,
  );

  if (result.exitCode != 0) {
    throw StateError(
      'pub outdated failed with exit code ${result.exitCode}\n'
      '${result.stderr}',
    );
  }

  return result.stdout.toString();
}

_Command _resolvePubOutdatedCommand(Directory target) {
  if (_hasFvmConfig(target) && _commandExists('fvm')) {
    return const _Command('fvm', ['dart', 'pub', 'outdated', '--json']);
  }

  if (_commandExists('flutter')) {
    return const _Command('flutter', ['pub', 'outdated', '--json']);
  }

  return const _Command('dart', ['pub', 'outdated', '--json']);
}

bool _hasFvmConfig(Directory target) {
  return File('${target.path}/.fvmrc').existsSync() ||
      Directory('${target.path}/.fvm').existsSync();
}

bool _commandExists(String command) {
  final result = Process.runSync(
    'sh',
    ['-c', 'command -v $command >/dev/null 2>&1'],
    runInShell: true,
  );

  return result.exitCode == 0;
}

class _DependencyAudit {
  final _DependencyCatalog catalog;
  final List<_OutdatedPackage> packages;

  const _DependencyAudit({required this.catalog, required this.packages});

  String build() {
    final compatible = <String>[];
    final breakingMajor = <String>[];
    final unknown = <String>[];

    for (final package in packages) {
      final constraint = catalog.constraints[package.name];

      if (constraint == null) {
        unknown.add(_formatPackage(package, 'not in catalog'));
        continue;
      }

      final supportedMajor = _majorFromConstraint(constraint);
      final latestMajor = _majorFromVersion(package.latest);

      if (package.resolvable != null &&
          package.current != null &&
          package.resolvable != package.current) {
        compatible.add(_formatPackage(package, 'compatible update available'));
      }

      if (supportedMajor != null &&
          latestMajor != null &&
          latestMajor > supportedMajor) {
        breakingMajor.add(_formatPackage(package, 'new major available'));
      }
    }

    final lines = <String>['# Dependency audit'];

    _appendSection(lines, 'Compatible updates', compatible);
    _appendSection(lines, 'Breaking-major candidates', breakingMajor);
    _appendSection(lines, 'Packages outside catalog', unknown);

    lines.add('');
    lines.add(
      'No constraints were changed. Update the catalog only after validating '
      'template compatibility.',
    );

    return lines.join('\n');
  }

  String _formatPackage(_OutdatedPackage package, String note) {
    return '- ${package.name}: current ${package.current ?? '-'}, '
        'resolvable ${package.resolvable ?? '-'}, latest ${package.latest ?? '-'} '
        '($note)';
  }

  void _appendSection(List<String> lines, String title, List<String> items) {
    lines.add('');
    lines.add('## $title');

    if (items.isEmpty) {
      lines.add('- None');
      return;
    }

    lines.addAll(items);
  }
}

class _DependencyCatalog {
  final Map<String, String> constraints;

  const _DependencyCatalog(this.constraints);

  factory _DependencyCatalog.read(File file) {
    if (!file.existsSync()) {
      throw ArgumentError('Dependency catalog not found: ${file.path}');
    }

    final constraints = <String, String>{};
    String? packageName;
    final packagePattern = RegExp(r'^  ([a-zA-Z0-9_]+):$');
    final constraintPattern = RegExp(r'^\s+constraint:\s*"?([^"\n]+)"?$');

    for (final line in file.readAsLinesSync()) {
      final packageMatch = packagePattern.firstMatch(line);

      if (packageMatch != null) {
        packageName = packageMatch.group(1);
        continue;
      }

      final constraintMatch = constraintPattern.firstMatch(line);

      if (packageName == null || constraintMatch == null) {
        continue;
      }

      constraints[packageName] = constraintMatch.group(1)!.trim();
      packageName = null;
    }

    return _DependencyCatalog(constraints);
  }
}

class _OutdatedPackages {
  static List<_OutdatedPackage> parse(String rawJson) {
    final decoded = jsonDecode(rawJson) as Map<String, Object?>;
    final rawPackages = decoded['packages'];

    if (rawPackages is! List<Object?>) {
      return [];
    }

    return rawPackages
        .whereType<Map<String, Object?>>()
        .map(_OutdatedPackage.fromJson)
        .toList();
  }
}

class _OutdatedPackage {
  final String name;
  final String? current;
  final String? resolvable;
  final String? latest;

  const _OutdatedPackage({
    required this.name,
    required this.current,
    required this.resolvable,
    required this.latest,
  });

  factory _OutdatedPackage.fromJson(Map<String, Object?> json) {
    return _OutdatedPackage(
      name: json['package']?.toString() ?? '',
      current: _versionFrom(json['current']),
      resolvable: _versionFrom(json['resolvable']),
      latest: _versionFrom(json['latest']),
    );
  }

  static String? _versionFrom(Object? value) {
    if (value == null) {
      return null;
    }

    if (value is String) {
      return value;
    }

    if (value is Map<String, Object?>) {
      return value['version']?.toString();
    }

    return null;
  }
}

int? _majorFromConstraint(String constraint) {
  final version = constraint.replaceFirst('^', '').trim();

  return _majorFromVersion(version);
}

int? _majorFromVersion(String? version) {
  if (version == null) {
    return null;
  }

  final match = RegExp(r'^(\d+)').firstMatch(version);

  if (match == null) {
    return null;
  }

  return int.tryParse(match.group(1)!);
}

class _Command {
  final String executable;
  final List<String> arguments;

  const _Command(this.executable, this.arguments);
}

class _Args {
  final Map<String, String> _values;

  const _Args(this._values);

  factory _Args.parse(List<String> arguments) {
    final values = <String, String>{};

    for (var index = 0; index < arguments.length; index++) {
      final argument = arguments[index];

      if (!argument.startsWith('--')) {
        continue;
      }

      final withoutPrefix = argument.substring(2);
      final separatorIndex = withoutPrefix.indexOf('=');

      if (separatorIndex >= 0) {
        values[withoutPrefix.substring(0, separatorIndex)] =
            withoutPrefix.substring(separatorIndex + 1);
        continue;
      }

      final hasNextValue = index + 1 < arguments.length &&
          !arguments[index + 1].startsWith('--');

      values[withoutPrefix] = hasNextValue ? arguments[++index] : 'true';
    }

    return _Args(values);
  }

  String? value(String key) {
    return _values[key];
  }
}
