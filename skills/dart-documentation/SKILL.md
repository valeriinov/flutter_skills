---
name: dart-documentation
description: Write or update Dartdoc for public interfaces and extensions, honoring the project AGENTS.md Documentation section. Use for "задокументируй", "напиши Dartdoc", "document the public API".
---

Add or update Dartdoc comments in the user-specified file. If none is given, ask the user which file to
document.

## Workflow

1. Read the target file to understand its public interfaces and extensions.
2. Identify all members that need documentation per the scope rules below.
3. Write Dartdoc comments following the format and templates.
4. Format and analyze the way the project's rules say — its lint skill or `AGENTS.md` command
   when there is one, otherwise `dart format .` then `dart analyze` — and fix all issues before
   finishing.

## Scope

- Document **only** public **interfaces** (`abstract interface class …`) and **extensions**.
- Skip trivial public API and private members; a private member gets a doc
  comment only for what code cannot say (SDK behaviour, an external contract, a
  silent ordering) — the rare case.
- If the project AGENTS.md has a "Documentation" section, it extends and
  overrides these defaults — scope additions (e.g. utilities, reusable
  widgets), the `{@category}` whitelist, and line-length limits come from
  there.

## Format

- Use Dartdoc `///` comments.
- Language: **English**.
- Optional category tag at the top: `/// {@category <Name>}`.
- Order inside a block:
    1. One-sentence summary (what it is).
    2. Details (optional; when it helps understanding).
    3. Parameters: `The [parameterName] parameter is ...`
    4. Returns (if non-void): concise sentence.
    5. Throws (optional).
    6. `Example:` code block.
- The `The [parameterName] parameter is ...` phrasing applies to method and
  constructor doc blocks only. Class fields are documented per-field, with a
  plain `///` comment directly above the field — no "parameter is" phrasing
  there; skip trivial field docs that only restate the name or type.

## Style

- Be concise; avoid redundancy with names/types.
- Prefer present tense ("Returns…", "Provides…").
- Don't restate obvious types or names.
- Use meaningful examples; keep them minimal and runnable.
- **Do:** explain side effects, preconditions, postconditions.
- **Don't:** duplicate information already clear from names or types.
- **Don't:** narrate what changed ("used to", "no longer", "previously"). Doc
  states the current contract; history lives in git.

## Interface Template

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

- New/edited interface and extension members have Dartdoc unless name and type
  already say it.
- Examples compile syntactically and illustrate intended usage.
- Method/constructor parameters follow: `The [parameterName] parameter is …`;
  class fields use a plain per-field `///` above the field.
- Label is `Example:` (not "Example usage:").
- The project's format and analyze commands pass with zero issues.