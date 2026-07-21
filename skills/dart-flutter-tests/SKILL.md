---
name: dart-flutter-tests
description: Create, update, or refactor Dart and Flutter tests. Use when adding new tests, fixing broken tests, or improving test structure and coverage.
argument-hint: [ file or feature to test ]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Generate or update Dart/Flutter tests for `$ARGUMENTS` (if the placeholder is not expanded, take the
target from the user's request). If no target is given, ask the user what to test.

## Workflow

1. Read the source file(s) under test to understand the code.
2. Check if a test file already exists — if yes, read it before making changes.
3. Write or update the test file following the rules below.
4. Run `dart format .` then `flutter analyze` — fix all issues before finishing.
5. Run the full test suite and ensure all tests pass.

## Structure Rules

- `main()` must call `_setup()` first, then one or more `group(...)` blocks.
- Inside each `group`, call private test functions — never inline `test()` or `testWidgets()`
  directly.
- Private test function naming: `_featureName_should_expectedBehavior()`.
- Test description string must match the function name: `'FeatureName should expectedBehavior'`.
- Group labels: `'<Feature> Tests'`, `'<Feature> Widget Tests'`, or `'<Feature> Extension Tests'`.
- Never use `late` (DCL `avoid-late-keyword` is enforced): declare mocks and the SUT as
  top-level `final`, constructed once, and `reset()` every mock in `tearDown`.
  Use `setUpAll` for `registerFallbackValue`. Do not recreate mocks in `setUp`.
- Wrap `setUpAll`/`tearDown` in `_setup()` and call it at the top of `main()`;
  omit `_setup()` entirely when there is nothing to register or reset.
- Separate Arrange / Act / Assert blocks with blank lines inside each test.
- Put reusable helpers below the tests that use them.
- Use `const` for immutable fixtures; reuse top-level `final` finders/constants across tests.
- Dispose controllers/handlers explicitly at the end of tests.

## Widget Tests

- Use `testWidgets` with a `WidgetTester` named `tester` (or `widgetTester` if clearer).
- Prefer project-provided pump helpers or app builders; fall back to `MaterialApp` directly.
- Use existing tester extensions/helpers for common actions.
- Call `await tester.pumpAndSettle()` after gestures.

## Unit Test Template

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

final _repository = MockRepository();
final _sut = FeatureUseCase(repository: _repository);

void main() {
  _setup();

  group('FeatureUseCase Tests', () {
    _featureUseCase_should_return_success_when_repository_succeeds();
    _featureUseCase_should_return_failure_when_repository_fails();
  });
}

void _setup() {
  tearDown(() {
    reset(_repository);
  });
}

void _featureUseCase_should_return_success_when_repository_succeeds() {
  test('FeatureUseCase should return success when repository succeeds', () async {
    when(() => _repository.getData()).thenAnswer((_) => Future.value(Right(Data())));

    final result = await _sut.execute();

    expect(result.isRight(), isTrue);
  });
}

void _featureUseCase_should_return_failure_when_repository_fails() {
  test('FeatureUseCase should return failure when repository fails', () async {
    when(() => _repository.getData()).thenAnswer((_) => Future.value(Left(Failure())));

    final result = await _sut.execute();

    expect(result.isLeft(), isTrue);
  });
}
```

## Widget Test Template

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

final _cubit = MockFeatureCubit();

void main() {
  _setup();

  group('FeatureView Widget Tests', () {
    _featureView_should_show_loader_when_loading();
    _featureView_should_display_data_when_loaded();
  });
}

void _setup() {
  tearDown(() {
    reset(_cubit);
  });
}

void _featureView_should_show_loader_when_loading() {
  testWidgets('FeatureView should show loader when loading', (widgetTester) async {
    await _pumpFeatureView(widgetTester, isLoading: true);

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}

void _featureView_should_display_data_when_loaded() {
  testWidgets('FeatureView should display data when loaded', (widgetTester) async {
    await _pumpFeatureView(widgetTester, isLoading: false);

    expect(find.text('Data Loaded'), findsOneWidget);
  });
}

Future<void> _pumpFeatureView(
  WidgetTester widgetTester, {
  required bool isLoading,
}) async {
  // Stub _cubit state, then pump via the project's pump helper / app builder.
}
```