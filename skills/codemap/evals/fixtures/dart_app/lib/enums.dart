part 'enums_labels.dart';

enum Mode {
  light,
  dark;

  bool get isDark => this == Mode.dark;
}
