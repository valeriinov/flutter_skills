---
name: document-code
description: Write or update documentation comments for public interfaces, classes, and extensions. Use when adding documentation to public APIs, abstract interfaces, or extension methods/properties.
---

Add or update documentation comments in `$ARGUMENTS`. If no argument is given, ask the user which file to
document.

## Workflow

1. Read the target file to understand its public interfaces, classes, and extensions.
2. Identify all members that need documentation per the scope rules below.
3. Write documentation comments following the format and templates.
4. If the file is Dart/Flutter: run `dart format .` then `flutter analyze` — fix all issues before finishing.
5. If the file is another language: run the relevant linter/formatter if available.

## Scope

- Document **only** public **interfaces**, **abstract classes**, and **extensions**.
- Document public methods, getters, setters, and properties of those types.
- Skip docs for private members and trivial public API where meaning is obvious.

## Format

- Use the idiomatic documentation comment style for the language (`///` for Dart, `/** */` or `//` for others).
- Language: **English**.
- Optional category tag at the top: `/// {@category <Name>}` (Dart) or equivalent.
- Order inside a block:
    1. One-sentence summary (what it is).
    2. Details (optional; when it helps understanding).
    3. Parameters: `The [parameterName] parameter is ...`
    4. Returns (if non-void): concise sentence.
    5. Throws (optional).
    6. `Example:` code block.

## Style

- Be concise; avoid redundancy with names/types.
- Prefer present tense ("Returns…", "Provides…").
- Don't restate obvious types or names.
- Use meaningful examples; keep them minimal and runnable.
- **Do:** explain side effects, preconditions, postconditions.
- **Don't:** duplicate information already clear from names or types.

## Interface / Abstract Class Template

```dart
/// {@category <Category>}
///
/// <One-sentence summary of the interface purpose.>
/// <Optional details providing context/usage.>
abstract interface class AppRouter {
  /// Provides the root [NavigatorState] key for the application.
  ///
  /// Example:
  /// ```dart
  /// final key = appRouter.rootNavKey;
  /// key.currentState?.pushNamed('/home');
  /// ```
  GlobalKey<NavigatorState> get rootNavKey;

  /// Configures and returns the [RouterConfig] for the application.
  ///
  /// Returns the router configuration used by Navigator 2.0.
  ///
  /// Example:
  /// ```dart
  /// runApp(MaterialApp.router(routerConfig: appRouter.routerConfig));
  /// ```
  RouterConfig<Object> get routerConfig;

  /// Handles navigation bootstrap.
  ///
  /// The [initialRoute] parameter is the route to open first.
  /// Returns a [Future] that completes when navigation is initialized.
  ///
  /// Example:
  /// ```dart
  /// await appRouter.bootstrap(initialRoute: '/');
  /// ```
  Future<void> bootstrap({required String initialRoute});
}
```

## Extension Template

```dart
/// {@category Extensions}
///
/// Extension on [DateTime] with convenience date utilities.
extension DateTimeInfo on DateTime {
  /// The first day of the month.
  ///
  /// Example:
  /// ```dart
  /// DateTime(2024, 5, 15).firstDayOfMonth; // 2024-05-01 00:00:00.000
  /// ```
  DateTime get firstDayOfMonth => DateTime(year, month, 1);

  /// Whether the current date is in the current month.
  ///
  /// Example:
  /// ```dart
  /// DateTime.now().isCurrentMonth; // true
  /// ```
  bool get isCurrentMonth {
    final now = DateTime.now();

    return year == now.year && month == now.month;
  }

  /// Returns the difference in months between this date and [other].
  ///
  /// The [other] parameter is the date to compare against.
  /// Returns a non-negative month count.
  ///
  /// Example:
  /// ```dart
  /// DateTime(2024, 8).differenceInMonths(DateTime(2024, 6)); // 2
  /// ```
  int differenceInMonths(DateTime other) {
    final years = year - other.year;
    final months = month - other.month;

    return (years * 12 + months).abs();
  }
}
```

## Verification Checklist

Before finishing, confirm:

- All new/edited interface, abstract class, and extension members have documentation.
- Examples compile syntactically and illustrate intended usage.
- Parameters follow: `The [parameterName] parameter is …`
- Label is `Example:` (not "Example usage:").
- Language-specific formatters and linters pass with zero issues.