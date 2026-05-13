---
name: freezed-init
description: Add Freezed code generation and concrete data models to a Flutter Clean Architecture project. Replaces the AppFailure placeholder from clean-arch-init with a Freezed sealed class, and adds AppErrorType and AppErrorCode enums. Use when setting up Freezed for immutable models, or when replacing the minimal AppFailure placeholder with a rich failure model.
---

# freezed-init

Add Freezed code generation and concrete data models to a Clean Architecture Flutter project.

This skill replaces the `AppFailure` placeholder from `clean-arch-init` with a concrete Freezed model that includes `type`, `code`, `message`, and `messageLocaleKey`. It also adds the `AppErrorType` and `AppErrorCode` enums used by the failure model.

## Files to Create or Override

### 1. App Error Type Enum: `lib/domain/entities/data_result/app_error_type.dart`

```dart
enum AppErrorType {
  connection,
  timeout,
  server,
  response,
  unauthorized,
  forbidden,
  notFound,
  unknown,
}
```

### 2. App Error Code Enum: `lib/domain/entities/data_result/app_error_code.dart`

```dart
enum AppErrorCode {
  none,
}
```

### 3. App Failure (overrides placeholder): `lib/domain/entities/data_result/app_failure.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:<project_name>/domain/entities/data_result/app_error_code.dart';
import 'package:<project_name>/domain/entities/data_result/app_error_type.dart';

part 'app_failure.freezed.dart';

/// {@category Domain}
///
/// Application-level failure model with structured error information.
///
/// Replaces the placeholder from `clean-arch-init`. Includes error type,
/// error code, message, and message locale key for localization support.
///
/// This is a Freezed sealed class — run `build_runner` after creation to
/// generate the `.freezed.dart` part file.
@freezed
sealed class AppFailure with _$AppFailure {
  const factory AppFailure({
    @Default(AppErrorType.unknown) AppErrorType type,
    @Default(AppErrorCode.none) AppErrorCode code,
    String? message,
    String? messageLocaleKey,
  }) = _AppFailure;
}
```

## Post-Setup Steps

1. Remind the user to add `freezed` and `json_serializable` to `pubspec.yaml` if not already present.
2. Run `build_runner` to generate `.freezed.dart` files:
   ```bash
   dart run build_runner build --delete-conflicting-outputs
   ```
3. Suggest running `dart format .` and verifying no analysis errors.

## Dependencies

This skill requires the following packages in `pubspec.yaml`:

```yaml
dependencies:
  freezed_annotation: ^3.0.0

dev_dependencies:
  freezed: ^3.0.0
  build_runner: ^2.0.0
```

## Prerequisites

- `clean-arch-init` must be applied first (this skill overrides its `AppFailure` placeholder).
- `cubit-init` will immediately benefit from the rich `AppFailure` fields.

## Important Rules

- This skill **overwrites** `lib/domain/entities/data_result/app_failure.dart` — do not preserve the placeholder.
- The `AppFailure` class uses `@freezed` and `sealed class` — requires code generation.
- `AppErrorType` and `AppErrorCode` are simple enums, no code generation needed.
- Member ordering follows Clean Code principles.