---
name: cubit-init
description: Initialize flutter_bloc Cubit base classes in a Flutter Clean Architecture project. Scaffolds BaseCubit, BaseState, BaseStatus, OperationGuard, and StatusHandler. Provides the foundational abstractions that concrete feature-level cubits build upon. Use when setting up flutter_bloc state management in a new project or adding the base layer to an existing one.
---

# cubit-init

Initialize flutter_bloc Cubit base classes in a Clean Architecture Flutter project.

This skill scaffolds the foundational abstractions for screen-level state management using `flutter_bloc`. It depends on the `clean-arch-init` foundation (specifically `AppFailure` for error info). If `AppFailure` is still a placeholder, run the `freezed-init` skill first to replace it with a concrete implementation.

## Files to Create

### 1. Base Status: `lib/presentation/ui/base/base_status.dart`

```dart
import 'package:<project_name>/domain/entities/data_result/app_failure.dart';

/// An abstract class for defining the status of a state.
/// This class includes properties for initialization/loading and error info.
abstract class BaseStatus {
  /// Whether the status is initialized.
  final bool isInitialized;

  /// Whether the status is currently loading.
  final bool isLoading;

  /// Structured error info.
  ///
  /// If not null, indicates an error state.
  final AppFailure? errorInfo;

  /// Constructs a [BaseStatus] instance.
  ///
  /// The [isLoading] parameter indicates if the status is currently loading.
  /// The [isInitialized] parameter indicates if the status is initialized.
  /// The [errorInfo] parameter holds an optional error info payload.
  const BaseStatus({
    this.isLoading = false,
    this.isInitialized = false,
    this.errorInfo,
  });

  /// Error message extracted from [errorInfo], if present.
  ///
  /// Returns `null` when there is no error info or no message.
  String? get errorMessage => errorInfo?.message;

  /// Error locale key extracted from [errorInfo], if present.
  ///
  /// Returns `null` when there is no error info.
  String? get errorMessageLocaleKey => errorInfo?.messageLocaleKey;

  /// Error type extracted from [errorInfo], if present.
  ///
  /// Returns `null` when there is no error info.
  AppErrorType? get errorType => errorInfo?.type;

  /// Error code extracted from [errorInfo], if present.
  ///
  /// Returns `null` when there is no error info.
  AppErrorCode? get errorCode => errorInfo?.code;

  /// Whether the status has an error.
  ///
  /// Returns `true` if [errorInfo] is not null.
  bool get hasError => errorInfo != null;
}
```

### 2. Base State: `lib/presentation/ui/base/base_state.dart`

```dart
import 'package:<project_name>/domain/entities/data_result/app_failure.dart';
import 'package:<project_name>/presentation/ui/base/base_status.dart';

/// An abstract base class representing a generic state with a status.
/// The [status] getter provides the current status of the state, which
/// must be an instance of a class extending [BaseStatus].
///
/// Example:
///
/// ```dart
/// import 'package:freezed_annotation/freezed_annotation.dart';
///
/// part 'user_state.freezed.dart';
///
/// @freezed
/// sealed class UserState extends BaseState<UserStatus> with _$UserState {
///   const UserState._();
///
///   const factory UserState({
///     @Default('') String userName,
///     @Default(UserStatus.userStatusBase()) UserStatus status,
///   }) = _UserState;
/// }
///
/// @freezed
/// sealed class UserStatus extends BaseStatus with _$UserStatus {
///   const UserStatus._();
///
///   const factory UserStatus.initial({
///     @Default(false) bool isInitialized,
///     @Default(false) bool isLoading,
///     StatusError? errorInfo,
///   }) = UserStatusInitial;
///
///   const factory UserStatus.base({
///     @Default(true) bool isInitialized,
///     @Default(false) bool isLoading,
///     StatusError? errorInfo,
///   }) = UserStatusBase;
///
///   const factory UserStatus.updatedSuccess({
///     @Default(true) bool isInitialized,
///     @Default(false) bool isLoading,
///     StatusError? errorInfo,
///   }) = UserStatusUpdatedSuccess;
/// }
/// ```
abstract class BaseState<T extends BaseStatus> {
  const BaseState();

  T get status;
}
```

### 3. Operation Guard: `lib/presentation/ui/base/operation_guard.dart`

```dart
/// {@category Utils}
///
/// Guards against stale async operations by tracking the current operation ID.
///
/// Assigns a unique ID on each [increment] call. When the operation completes,
/// use [isCurrent] to verify the result is still relevant before applying it.
///
/// Example:
/// ```dart
/// final _guard = OperationGuard();
///
/// Future<void> _load() async {
///   final operationId = _guard.increment();
///   final result = await repository.fetch();
///   if (!_guard.isCurrent(operationId)) return;
///   emit(result);
/// }
/// ```
class OperationGuard {
  int _currentOperationId = 0;

  /// Advances to the next operation and returns its ID.
  ///
  /// Returns the new current operation ID.
  int increment() => ++_currentOperationId;

  /// Returns whether [operationId] matches the current operation.
  ///
  /// The [operationId] parameter is the ID returned by [increment].
  bool isCurrent(int operationId) => operationId == _currentOperationId;
}
```

### 4. Base Cubit: `lib/presentation/ui/base/base_cubit.dart`

```dart
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:<project_name>/presentation/ui/base/base_state.dart';

/// {@category StateManagement}
///
/// Base cubit that guards every state change against post-close emission.
///
/// Overrides [emit] so that all state updates — including those after async
/// boundaries — are silently dropped when the cubit is already closed.
/// Subclasses use the standard [emit] call; no separate helper is needed.
///
/// Example:
/// ```dart
/// class ExampleCubit extends BaseCubit<ExampleState> {
///   ExampleCubit() : super(const ExampleState());
///
///   Future<void> load() async {
///     final result = await _repository.load();
///     emit(state.copyWith(data: result)); // safe — dropped if cubit is closed
///   }
/// }
/// ```
abstract class BaseCubit<TState extends BaseState<dynamic>>
    extends Cubit<TState> {
  BaseCubit(super.initialState);

  /// Emits [state] only when the cubit is not closed.
  ///
  /// The [state] parameter is the next cubit state to emit.
  /// Calls are silently dropped after the cubit is disposed.
  @override
  void emit(TState state) {
    if (!isClosed) {
      super.emit(state);
    }
  }
}
```

### 5. Status Handler Interface: `lib/presentation/ui/base/status_handler/status_handler.dart`

```dart
import 'package:<project_name>/presentation/ui/base/base_state.dart';

/// {@category StateManagement}
///
/// Interface for handling UI status changes from BLoC states.
abstract interface class StatusHandler {
  /// Processes a status and displays appropriate UI feedback.
  ///
  /// The [status] parameter is the status to handle.
  /// The [showErrorDialogs] parameter controls whether error dialogs
  /// are displayed for error statuses.
  ///
  /// Example:
  /// ```dart
  /// await statusHandler.handleStatus(state.status);
  /// ```
  Future<void> handleStatus(BaseStatus status, {bool showErrorDialogs = true});
}
```

### 6. Status Handler Placeholder: `lib/presentation/ui/base/status_handler/status_handler_impl.dart`

```dart
import 'package:<project_name>/presentation/ui/base/base_state.dart';
import 'package:<project_name>/presentation/ui/base/status_handler/status_handler.dart';

/// {@category StateManagement}
///
/// Placeholder implementation of [StatusHandler].
///
/// This implementation only prints error messages to the console.
/// Building-block skills or project-specific setups override this file
/// with a concrete implementation that integrates with the project's
/// toast system, dialog manager, or error display UI.
///
/// TODO(required): Replace with a concrete status handler implementation.
class StatusHandlerImpl implements StatusHandler {
  @override
  Future<void> handleStatus(
    BaseStatus status, {
    bool showErrorDialogs = true,
  }) async {
    final failure = status.errorInfo;

    if (failure == null || !showErrorDialogs) {
      return;
    }

    print('Error: ${failure.message}');
  }
}
```

## Directory Structure

```
lib/presentation/ui/base/
├── base_cubit.dart
├── base_state.dart
├── base_status.dart
├── operation_guard.dart
└── status_handler/
    ├── status_handler.dart
    └── status_handler_impl.dart
```

## Dependencies

This skill requires the following packages in `pubspec.yaml`:

```yaml
dependencies:
  flutter_bloc: ^9.0.0
```

## Prerequisites

- `clean-arch-init` must be applied first.
- `freezed-init` is **strongly recommended** so that `AppFailure` has fields
  like `type`, `code`, `messageLocaleKey`. Without these, the `errorType`
  and `errorCode` getters in `BaseStatus` will always return `null`.

## Post-Setup Steps

1. Remind the user to add `flutter_bloc` to `pubspec.yaml` if not already present.
2. Suggest running `dart format .` and verifying no analysis errors.
3. Highlight that `status_handler_impl.dart` is a placeholder and should be
   overridden with a project-specific implementation (e.g., toast manager, dialogs).

## Important Rules

- `BaseCubit` must extend `Cubit<TState>` from `flutter_bloc`, not `Bloc`.
- `BaseState` and `BaseStatus` are abstract classes — concrete implementations use Freezed.
- `OperationGuard` uses operation IDs to guard against stale async results.
- `BaseCubit.emit` is safe to call after async boundaries; calls are silently dropped if closed.
- Member ordering follows Clean Code principles.
- Method bodies always use curly braces; never use arrow syntax for named methods.