---
name: clean-arch-init
description: Initialize a Clean Architecture foundation in a Flutter project. Scaffolds layer directories (domain, data, presentation, common), creates base abstractions (DataResult<T> via dartz Either, AppFailure placeholder, ErrorMapper placeholder, BaseRepository, ErrorReporter), and generates an ARCHITECTURE.md documenting layer contracts and dependency rules. Uses dartz for the Result type. This skill is framework-agnostic regarding state management, DI, routing, and networking. Concrete implementations are added later via separate building-block skills that override the placeholder classes. Use when starting a new Flutter project, migrating an existing one to Clean Architecture, or setting up the project structure.
---

# clean-arch-init

Initialize Clean Architecture in a Flutter project.

This skill scaffolds a **framework-agnostic** Clean Architecture foundation. It depends only on **dartz** for the `DataResult<T>` type. All other dependencies (state management, DI, routing, networking, serialization) are added later via separate building-block skills.

The skill reads the project name from `pubspec.yaml` (`name` field) and uses it for all generated import statements.

## Files to Create

### 1. App Failure Placeholder: `lib/domain/entities/data_result/app_failure.dart`

```dart
/// Application-level failure model.
///
/// This is a **placeholder** with a minimal `message` field.
/// Building-block skills override this file with a concrete implementation
/// that adds fields such as `type`, `code`, `messageLocaleKey`, etc.
///
/// TODO(required): Replace with a concrete failure model via a building-block skill.
class AppFailure {
  final String? message;

  const AppFailure({this.message});
}
```

### 2. Result Type: `lib/domain/entities/data_result/data_result.dart`

```dart
import 'package:dartz/dartz.dart';
import 'package:<project_name>/domain/entities/data_result/app_failure.dart';

/// A type alias for representing the result of an operation
/// that can either succeed or fail.
///
/// The [DataResult] type uses the `Either` type from
/// the `dartz` package to encapsulate
/// two possible outcomes:
/// - `Left(Failure)`: Indicates that the operation failed,
/// providing a [AppFailure] object with error details.
/// - `Right(T)`: Indicates that the operation was successful,
/// containing a value of type [T].
///
/// This structure encourages explicit error handling
/// by making it clear when an operation
/// can fail and requiring the caller to handle both success and failure cases.
///
/// Example:
/// ```dart
/// Future<DataResult<String>> fetchData() async {
///   try {
///     final data = await apiService.getData();
///     return Right(data);
///   } catch (e) {
///     return Left(AppFailure(message: 'Failed to fetch data'));
///   }
/// }
///
/// void handleResult(DataResult<String> result) {
///   result.fold(
///     (failure) => print('Error: ${failure.message}'),
///     (data) => print('Data: $data'),
///   );
/// }
/// ```
typedef DataResult<T> = Either<AppFailure, T>;
```

### 3. Error Reporter Interface: `lib/common/base/reporting/error_reporter.dart`

```dart
/// Contract for reporting application errors to an external service.
abstract interface class ErrorReporter {
  /// Initializes the error reporter.
  ///
  /// Example:
  /// ```dart
  /// await errorReporter.initialize();
  /// ```
  void initialize();

  /// Sends an error report with [stackTrace] details.
  ///
  /// The [error] parameter is the caught exception or error object.
  /// The [stackTrace] parameter is the associated stack trace.
  /// The [isFatal] parameter is whether the error caused an app crash.
  ///
  /// Example:
  /// ```dart
  /// try {
  ///   // ...
  /// } catch (error, stackTrace) {
  ///   await errorReporter.report(error, stackTrace);
  /// }
  /// ```
  Future<void> report(
    Object error,
    StackTrace stackTrace, {
    bool isFatal = false,
  });
}
```

### 4. Error Mapper Placeholder: `lib/data/repositories/mappers/error_mapper.dart`

```dart
import 'package:<project_name>/domain/entities/data_result/app_failure.dart';

/// Maps exceptions and errors into domain-safe [AppFailure] instances.
///
/// This is a **placeholder** with a minimal implementation that only wraps
/// the exception message. Building-block skills override this file with a
/// concrete implementation that maps specific error types (Dio, Firebase, etc.)
/// to structured failures.
///
/// TODO(required): Replace with a concrete error mapper via a building-block skill.
class ErrorMapper {
  AppFailure mapErrorToAppFailure(Object error, StackTrace stackTrace) {
    return AppFailure(message: error.toString());
  }
}
```

### 5. Base Repository: `lib/data/repositories/base_repository.dart`

```dart
import 'package:dartz/dartz.dart';
import 'package:<project_name>/common/base/reporting/error_reporter.dart';
import 'package:<project_name>/data/repositories/mappers/error_mapper.dart';
import 'package:<project_name>/domain/entities/data_result/data_result.dart';

/// An abstract base repository that standardizes error handling for data
/// operations and converts thrown exceptions into domain-safe results
/// represented by [DataResult].
///
/// This class provides two helpers:
/// - [runCatching] for asynchronous actions (e.g., network/database calls).
/// - [runCatchingSync] for synchronous actions (e.g., in-memory computations).
/// - [handleError] to convert caught exceptions into `Left(AppFailure)`.
///
/// When an exception is caught:
/// - A crash report is sent via [CrashlyticsSenderService].
/// - The exception is mapped to an [AppFailure] using [ErrorMapper].
/// - The method returns `Left(AppFailure)` ensuring callers always receive an
///   [Either] without needing try/catch at call sites.
///
/// Example:
///
/// ```dart
/// final class UserRepositoryImpl extends BaseRepository {
///   final Dio _dio;
///
///   UserRepositoryImpl({
///     required Dio dio,
///     required super.errorMapper,
///     required super.errorSender,
///   }) : _dio = dio;
///
///   Future<AppResult<UserEntity>> getUser(int id) {
///     return runCatching(
///       action: () async {
///         final response = await _dio.get('/users/$id');
///
///         return Right(UserEntity.fromJson(response.data));
///       },
///     );
///   }
///
///   AppResult<int> computeLocalValue() {
///     return runCatchingSync(
///       action: () {
///         final value = 2 + 2;
///
///         return Right(value);
///       },
///     );
///   }
/// }
/// ```
abstract base class BaseRepository {
  final ErrorMapper _errorMapper;
  final ErrorReporter _errorReporter;

  BaseRepository({
    required ErrorMapper errorMapper,
    required ErrorReporter errorReporter,
  }) : _errorMapper = errorMapper,
       _errorReporter = errorReporter;

  /// Executes an asynchronous [action] and wraps its result into [DataResult].
  ///
  /// The [action] parameter is a function that must return an [DataResult].
  /// If [action] completes successfully,
  /// the original [DataResult] is returned.
  /// If an exception is thrown, a crash report is sent and `Left(AppFailure)`
  /// is returned using [ErrorMapper].
  ///
  /// Example:
  ///
  /// ```dart
  /// return runCatching(
  ///   action: () async {
  ///     final data = await api.fetch();
  ///
  ///     return Right(data);
  ///   },
  /// );
  /// ```
  Future<DataResult<T>> runCatching<T>({
    required Future<DataResult<T>> Function() action,
  }) async {
    try {
      return await action();
    } catch (error, stackTrace) {
      return handleError(error, stackTrace);
    }
  }

  /// Executes a synchronous [action] and wraps its result into [DataResult].
  ///
  /// The [action] parameter is a function that must return an [DataResult].
  /// If [action] returns successfully, the original [DataResult] is returned.
  /// If an exception is thrown, a crash report is sent and `Left(AppFailure)`
  /// is returned using [ErrorMapper].
  ///
  /// Example:
  ///
  /// ```dart
  /// return runCatchingSync(
  ///   action: () {
  ///     final computed = cache.recalculate();
  ///
  ///     return Right(computed);
  ///   },
  /// );
  /// ```
  DataResult<T> runCatchingSync<T>({required DataResult<T> Function() action}) {
    try {
      return action();
    } catch (error, stackTrace) {
      return handleError(error, stackTrace);
    }
  }

  /// Converts a caught [error] into a domain-safe [DataResult].
  /// Sends a crash report via [CrashlyticsSenderService].
  ///
  /// The [error] parameter is the exception or error to convert.
  /// The [stackTrace] parameter is the associated stack trace.
  ///
  /// The type parameter [T] is the expected success type and only shapes the
  /// return type; it does not affect error mapping.
  ///
  /// Example:
  /// ```dart
  /// try {
  ///   // code that may throw
  /// } catch (e, s) {
  ///   return handleError<MyType>(e, s);
  /// }
  /// ```
  DataResult<T> handleError<T>(Object error, StackTrace stackTrace) {
    _errorReporter.report(error, stackTrace);

    return Left(_errorMapper.mapErrorToAppFailure(error, stackTrace));
  }
}
```

### 6. Directory Structure Scaffold

Create the following empty directories to establish the layer boundaries:

```
lib/
├── common/               # Shared utilities, extensions, constants.
│   ├── adapters/         # Platform/package adapters (added by concrete skills).
│   ├── constants/
│   ├── base/
│   │   └── reporting/
│   │       └── error_reporter.dart
│   └── utils/
│       └── ext/          # Extension methods organized by type.
├── data/                 # Data layer: DTOs, mappers, repositories, sources.
│   ├── dto/              # Data Transfer Objects (added by concrete skills).
│   ├── mappers/          # DTO <-> Domain mappers.
│   ├── network/          # Network layer (added by concrete skills).
│   ├── repositories/
│   │   ├── base_repository.dart
│   │   └── mappers/
│   │       └── error_mapper.dart
│   ├── sources/          # Concrete data source implementations.
│   └── utils/            # Data-specific utilities.
├── domain/               # Domain layer: entities, repositories, use cases.
│   ├── entities/
│   │   └── data_result/
│   │       ├── app_failure.dart
│   │       └── data_result.dart
│   ├── repositories/     # Repository interfaces.
│   └── usecases/         # Application use cases.
└── presentation/         # UI layer: screens, navigation, DI, widgets.
    ├── di/               # Dependency injection setup (added by concrete skills).
    └── ui/
        ├── base/         # Base abstractions for state management (added by concrete skills).
        ├── navigation/   # Router configuration (added by concrete skills).
        ├── resources/    # Theme, colors, dimensions.
        ├── screens/      # Feature screens organized by feature name.
        └── widgets/      # Reusable UI components.
```

### 7. Architecture Documentation: `ARCHITECTURE.md`

```markdown
# Clean Architecture

## Overview

This project follows Clean Architecture with a strict separation between:
- **Domain** — business logic, independent of frameworks.
- **Data** — data access, networking, storage.
- **Presentation** — UI, state management, navigation.
- **Common** — shared utilities crossing all layers.

## Dependency Rule

Dependencies point inward only:
```
Presentation -> Domain <- Data
```

- **Domain** knows nothing about Data or Presentation.
- **Data** depends only on Domain.
- **Presentation** depends on Domain (and may depend on Data for DI wiring only).
- **Common** is accessible from all layers.

## Layer Details

### Domain Layer (`lib/domain/`)

Contains business entities, repository contracts, and use cases.
This layer is framework-agnostic and highly testable.

- **Entities** (`entities/`) — Core business models. No JSON, no framework annotations.
- **Repositories** (`repositories/`) — Abstract interfaces for data operations.
- **Use Cases** (`usecases/`) — Encapsulate specific business rules. Thin delegation to repositories.

### Data Layer (`lib/data/`)

Implements repository contracts and handles external data interactions.

- **DTOs** (`dto/`) — Data Transfer Objects for API payloads. Include serialization.
- **Mappers** (`mappers/`) — Transform between DTOs and Domain entities.
- **Repositories** (`repositories/`) — Concrete implementations extending `BaseRepository`.
- **Sources** (`sources/`) — Concrete data source implementations (remote APIs, local DB).
- **Network** (`network/`) — HTTP clients, interceptors, environment setup.
- **Utils** (`utils/`) — Serialization helpers, error handling utilities.

### Presentation Layer (`lib/presentation/`)

Contains UI, navigation, resources, and shared widgets.

- **DI** (`di/`) — Dependency injection configuration and setup.
- **UI Base** (`ui/base/`) — Base classes for state management (added by concrete skills).
- **Navigation** (`ui/navigation/`) — Router and route definitions.
- **Resources** (`ui/resources/`) — Theme, colors, text styles, dimensions.
- **Screens** (`ui/screens/<feature>/`) — Feature screens:
  - `<feature>_screen.dart` — Entry point widget.
  - `widgets/` — Screen-specific widgets.
- **Widgets** (`ui/widgets/`) — Reusable components shared across features.

### Common Layer (`lib/common/`)

Cross-cutting concerns accessible from all layers.

- **Adapters** (`adapters/`) — Wrappers for external packages (logging, analytics).
- **Constants** (`constants/`) — App-wide constants.
- **Utils** (`utils/ext/`) — Extension methods organized by type (String, DateTime, etc.).
- **Error Reporter** (`base/reporting/error_reporter.dart`) — Interface for error reporting.

## Base Classes

### AppFailure

An application-level failure model with a `message` field.
This is a placeholder overridden by building-block skills with a concrete
implementation that adds fields like `type`, `code`, `messageLocaleKey`.

### DataResult<T>

A type alias for `Either<AppFailure, T>` from the `dartz` package:
- `Left(AppFailure)`: The operation failed.
- `Right(T)`: The operation was successful.

All repository methods return `Future<DataResult<T>>`. Callers use `fold()` to handle both paths explicitly.

### BaseRepository

Provides `runCatching` and `runCatchingSync` wrappers that:
1. Execute an action.
2. Catch any exception.
3. Send an error report via `ErrorReporter`.
4. Map it to `AppFailure` via `ErrorMapper`.
5. Return `Left(...)`.

This eliminates try/catch boilerplate at every call site.

### ErrorMapper

Maps exceptions to `AppFailure`. This is a placeholder overridden by building-block
skills with a concrete implementation that handles specific error types (Dio, Firebase, etc.).

### ErrorReporter

Interface for reporting errors to external services. Concrete implementations
(Crashlytics, Sentry, custom logger) are provided by building-block skills.

## Adding Concrete Implementations

After this foundation is in place, add building-block skills for:
- **State management** — `cubit-init`, `riverpod-init`, etc.
- **Networking** — `dio-init`, `http-init`, etc.
- **DI** — `get-it-init`, `riverpod-init`, etc.
- **Navigation** — `auto-route-init`, `go-router-init`, etc.
- **Local storage** — `drift-init`, `hive-init`, etc.
- **Models** — `freezed-init`, `json-serializable-init`, etc.
- **Error reporting** — `crashlytics-init`, `sentry-init`, etc.

Each skill scaffolds concrete implementations within the layer boundaries established here.

## Naming Conventions

- Files: `snake_case.dart`
- Classes: `PascalCase`
- Interfaces: `abstract interface class` prefix
- Repository interfaces: `<Feature>Repository`
- Repository implementations: `<Feature>RepositoryImpl`
- Data sources: `<Feature>RemoteDataSource` / `<Feature>LocalDataSource`
- Use cases: `<Feature>UseCase`
- Mappers: `<Feature>Mapper`
```

## Post-Init Steps

1. Inform the user about the created structure and files.
2. Highlight that `app_failure.dart` and `error_mapper.dart` are **placeholders** and must be overridden by a building-block skill (e.g., `freezed-init`, `dio-init`).
3. Remind that this is a framework-agnostic foundation — concrete implementations (state management, DI, networking, etc.) must be added via separate building-block skills.
4. Suggest running `dart format .` and verifying no analysis errors.

## Important Rules

- The only external dependency added by this skill is `dartz` for `Either`.
- Do not add any other framework-specific dependencies (Freezed, flutter_bloc, get_it, auto_route, dio, drift, etc.) in this skill.
- Do not create concrete state management classes, DTOs with JSON serialization, or router configurations.
- `AppFailure` and `ErrorMapper` are **placeholders** — they are intentionally minimal and meant to be overridden by building-block skills.
- `ErrorReporter` is an interface only — concrete implementations belong in building-block skills.
- Member ordering follows Clean Code principles: static fields -> fields -> constructors -> getters/setters -> public methods -> private methods.
- Avoid nested structures: prefer early returns and small private methods.
- Method bodies always use curly braces; never use arrow syntax for named methods.