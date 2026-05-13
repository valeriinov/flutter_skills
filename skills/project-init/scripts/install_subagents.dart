import 'dart:io';

const _agentPrefix = 'project-init-';

void main(List<String> arguments) {
  final args = _Args.parse(arguments);
  final target = Directory(args.value('target') ?? Directory.current.path);

  _validateTarget(target);

  final skillRoot = File(Platform.script.toFilePath()).parent.parent;
  final result = _InstallResult();

  _installGroup(
    source: Directory('${skillRoot.path}/assets/agents/claude'),
    destination: Directory('${target.path}/.claude/agents'),
    extension: '.md',
    result: result,
  );
  _installGroup(
    source: Directory('${skillRoot.path}/assets/agents/codex'),
    destination: Directory('${target.path}/.codex/agents'),
    extension: '.toml',
    result: result,
  );

  stdout.writeln(result.summary);
}

void _validateTarget(Directory target) {
  if (!target.existsSync()) {
    throw ArgumentError('Target directory does not exist: ${target.path}');
  }

  if (!File('${target.path}/pubspec.yaml').existsSync()) {
    throw ArgumentError(
      'Target must be an existing Flutter project with pubspec.yaml: '
      '${target.path}',
    );
  }
}

void _installGroup({
  required Directory source,
  required Directory destination,
  required String extension,
  required _InstallResult result,
}) {
  if (!source.existsSync()) {
    throw StateError('Missing agent template directory: ${source.path}');
  }

  destination.createSync(recursive: true);

  for (final entity in source.listSync()) {
    if (entity is! File) {
      continue;
    }

    final fileName = _basename(entity.path);

    if (!fileName.startsWith(_agentPrefix) || !fileName.endsWith(extension)) {
      continue;
    }

    final destinationFile = File('${destination.path}/$fileName');
    final sourceContent = entity.readAsStringSync();

    if (destinationFile.existsSync()) {
      final destinationContent = destinationFile.readAsStringSync();

      if (destinationContent == sourceContent) {
        result.unchanged.add(destinationFile.path);
        continue;
      }

      destinationFile.writeAsStringSync(sourceContent);
      result.updated.add(destinationFile.path);
      continue;
    }

    destinationFile.writeAsStringSync(sourceContent);
    result.installed.add(destinationFile.path);
  }
}

String _basename(String path) {
  return path.split(Platform.pathSeparator).last;
}

class _InstallResult {
  final List<String> installed = [];
  final List<String> updated = [];
  final List<String> unchanged = [];

  String get summary {
    final lines = [
      'project-init subagents installed.',
      'Installed: ${installed.length}',
      'Updated: ${updated.length}',
      'Unchanged: ${unchanged.length}',
    ];

    if (installed.isNotEmpty) {
      lines.add('Installed files:');
      lines.addAll(installed.map((path) => '- $path'));
    }

    if (updated.isNotEmpty) {
      lines.add('Updated files:');
      lines.addAll(updated.map((path) => '- $path'));
    }

    return lines.join('\n');
  }
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
