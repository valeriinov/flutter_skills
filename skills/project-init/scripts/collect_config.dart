import 'dart:convert';
import 'dart:io';

void main(List<String> arguments) {
  final args = _Args.parse(arguments);
  final target = Directory(args.value('target') ?? Directory.current.path);

  _validateFlutterProject(target);

  final config = <String, Object>{
    'stateManagement': _readOption(
      args: args,
      key: 'state',
      prompt: 'State management (cubit/riverpod)',
      defaultValue: 'cubit',
      allowedValues: {'cubit', 'riverpod'},
    ),
    'languages': _readList(
      args: args,
      key: 'languages',
      prompt: 'Languages as ISO codes',
      defaultValue: ['en'],
    ),
    'flavors': _readFlavors(args),
    'useDio': _readBool(
      args: args,
      key: 'dio',
      prompt: 'Use Dio network layer',
      defaultValue: true,
    ),
    'setupSplash': _readBool(
      args: args,
      key: 'splash',
      prompt: 'Set up flutter_native_splash',
      defaultValue: true,
    ),
    'setupLauncherIcons': _readBool(
      args: args,
      key: 'icons',
      prompt: 'Set up flutter_launcher_icons',
      defaultValue: true,
    ),
    'initialFeature': _readName(
      args: args,
      key: 'init-feature',
      prompt: 'Initial feature name',
      defaultValue: 'home',
    ),
  };

  final encoded = const JsonEncoder.withIndent('  ').convert(config);
  final output = args.value('output');

  if (output == null) {
    stdout.writeln(encoded);
    return;
  }

  final outputFile = File(output);
  outputFile.parent.createSync(recursive: true);
  outputFile.writeAsStringSync('$encoded\n');
  stdout.writeln('Project init config written to ${outputFile.path}');
}

void _validateFlutterProject(Directory target) {
  if (!target.existsSync()) {
    throw ArgumentError('Target directory does not exist: ${target.path}');
  }

  final pubspec = File('${target.path}/pubspec.yaml');
  final libDir = Directory('${target.path}/lib');

  if (!pubspec.existsSync() || !libDir.existsSync()) {
    throw ArgumentError(
      'project-init must run in an existing Flutter project with pubspec.yaml '
      'and lib/. Target: ${target.path}',
    );
  }
}

List<String> _readFlavors(_Args args) {
  final raw = args.value('flavors') ??
      _prompt('Flavors (standard/none/custom comma list)', 'standard');
  final normalized = raw.trim().toLowerCase();

  if (normalized.isEmpty || normalized == 'standard') {
    return ['dev', 'for_test', 'preprod', 'prod'];
  }

  if (normalized == 'none') {
    return [];
  }

  final values = _splitCsv(normalized);
  _validateNames(values, 'flavor');

  return values;
}

String _readOption({
  required _Args args,
  required String key,
  required String prompt,
  required String defaultValue,
  required Set<String> allowedValues,
}) {
  final value =
      (args.value(key) ?? _prompt(prompt, defaultValue)).trim().toLowerCase();

  if (!allowedValues.contains(value)) {
    throw ArgumentError(
      'Invalid $key "$value". Allowed values: ${allowedValues.join(', ')}.',
    );
  }

  return value;
}

List<String> _readList({
  required _Args args,
  required String key,
  required String prompt,
  required List<String> defaultValue,
}) {
  final raw = args.value(key) ?? _prompt(prompt, defaultValue.join(','));
  final values = _splitCsv(raw.toLowerCase());

  _validateNames(values, key);

  return values.isEmpty ? defaultValue : values;
}

bool _readBool({
  required _Args args,
  required String key,
  required String prompt,
  required bool defaultValue,
}) {
  final raw = args.value(key) ?? _prompt(prompt, defaultValue ? 'yes' : 'no');
  final normalized = raw.trim().toLowerCase();

  if (normalized == 'yes' || normalized == 'y' || normalized == 'true') {
    return true;
  }

  if (normalized == 'no' || normalized == 'n' || normalized == 'false') {
    return false;
  }

  throw ArgumentError('Invalid boolean for $key: "$raw".');
}

String _readName({
  required _Args args,
  required String key,
  required String prompt,
  required String defaultValue,
}) {
  final value =
      (args.value(key) ?? _prompt(prompt, defaultValue)).trim().toLowerCase();

  _validateNames([value], key);

  return value;
}

List<String> _splitCsv(String raw) {
  return raw
      .split(',')
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toList();
}

void _validateNames(List<String> values, String label) {
  final pattern = RegExp(r'^[a-z][a-z0-9_]*$');

  for (final value in values) {
    if (pattern.hasMatch(value)) {
      continue;
    }

    throw ArgumentError(
      'Invalid $label "$value". Use lowercase letters, numbers, and '
      'underscores. The first character must be a letter.',
    );
  }
}

String _prompt(String label, String defaultValue) {
  stdout.write('$label [$defaultValue]: ');
  final value = stdin.readLineSync()?.trim();

  if (value == null || value.isEmpty) {
    return defaultValue;
  }

  return value;
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
