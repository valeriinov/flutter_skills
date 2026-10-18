import 'enums.dart';

extension StringX on String {
  bool get isBlank => trim().isEmpty;
}

extension on int {
  Mode get mode => isEven ? Mode.light : Mode.dark;
}

Mode modeOf(int value) => value.mode;
