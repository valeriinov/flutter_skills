---
name: dio-init
description: Add Dio networking infrastructure and replace the ErrorMapper placeholder with a Dio-aware implementation. Scaffolds structured error handling (ErrorDataDto, ErrorTypeDto, ErrorCodeDto, ErrorDataExtractor, DioErrorDataExtractor) plus BaseResponseDto and foundational serialization helpers. Must be applied after clean-arch-init and freezed-init. Use when setting up Dio as the HTTP client with structured error mapping.
---

# dio-init

Add Dio networking infrastructure and replace the `ErrorMapper` placeholder with a Dio-aware implementation.

This skill scaffolds structured error handling classes that map `DioException` (and other common exceptions) into domain-safe `AppFailure` instances. It overrides the `ErrorMapper` placeholder from `clean-arch-init`.

## Prerequisites

- `clean-arch-init` must be applied first.
- `freezed-init` must be applied first (this skill depends on `AppFailure` fields: `type`, `code`, `message`, `messageLocaleKey`).
- `get-it-init` is strongly recommended so that `@LazySingleton()` annotations resolve.

## Dependencies

```yaml
dependencies:
  dio: ^5.0.0
  freezed_annotation: ^3.0.0

dev_dependencies:
  freezed: ^3.0.0
  build_runner: ^2.0.0
```

## Files to Create or Override

### 1. Serialization Helpers

#### `lib/data/utils/serialization/nullable_enum_field_key.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

const nullableEnumFieldKey = JsonKey(
  unknownEnumValue: JsonKey.nullForUndefinedEnumValue,
);
```

#### `lib/data/utils/serialization/response_message_reader.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

/// {@category Utils}
///
/// Reader for `message` field when the server uses `description`.
class ResponseMessageReader {
  // Using `Object` is intentional here.
  // ignore: no-object-declaration
  static Object? read(Map json, String _) {
    return json['description'];
  }
}

const responseMessageFieldKey = JsonKey(readValue: ResponseMessageReader.read);
```

#### `lib/data/utils/serialization/response_technical_message_reader.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

/// {@category Utils}
///
/// Reader for `technicalMessage` field when the server uses `message`.
class ResponseTechnicalMessageReader {
  // Using `Object` is intentional here.
  // ignore: no-object-declaration
  static Object? read(Map json, String _) {
    return json['message'];
  }
}

const responseTechnicalMessageFieldKey = JsonKey(
  readValue: ResponseTechnicalMessageReader.read,
);
```

### 2. Base Response DTO: `lib/data/dto/base_response/base_response_dto.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:<project_name>/data/dto/error/error_code_dto.dart';
import 'package:<project_name>/data/utils/serialization/nullable_enum_field_key.dart';
import 'package:<project_name>/data/utils/serialization/response_message_reader.dart';
import 'package:<project_name>/data/utils/serialization/response_technical_message_reader.dart';

part 'base_response_dto.freezed.dart';
part 'base_response_dto.g.dart';

@freezed
sealed class BaseResponseDto with _$BaseResponseDto {
  const factory BaseResponseDto({
    @nullableEnumFieldKey ErrorCodeDto? errorCode,
    @responseMessageFieldKey String? message,
    @responseTechnicalMessageFieldKey String? technicalMessage,
  }) = _BaseResponseDto;

  const BaseResponseDto._();

  factory BaseResponseDto.fromJson(Map<String, Object?> json) =>
      _$BaseResponseDtoFromJson(json);
}
```

### 3. Error Type DTO: `lib/data/dto/error/error_type_dto.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

enum ErrorTypeDto {
  @JsonValue('CONNECTION_ERROR')
  connection,
  @JsonValue('TIMEOUT_ERROR')
  timeout,
  @JsonValue('SERVER_ERROR')
  server,
  @JsonValue('RESPONSE_ERROR')
  response,
  @JsonValue('UNAUTHORIZED_ERROR')
  unauthorized,
  @JsonValue('FORBIDDEN_ERROR')
  forbidden,
  @JsonValue('NOT_FOUND_ERROR')
  notFound,
  @JsonValue('CACHE_ERROR')
  cache,
  @JsonValue('STATE_ERROR')
  state,
  @JsonValue('PARSING_ERROR')
  parsing,
  @JsonValue('TYPE_ERROR')
  type,
  @JsonValue('UNKNOWN_ERROR')
  unknown,
}
```

### 4. Error Code DTO: `lib/data/dto/error/error_code_dto.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

enum ErrorCodeDto {
  @JsonValue('phone-number-is-used')
  phoneNumberIsUsed,
  @JsonValue('token-expired')
  tokenExpired,
  none,
}
```

### 5. Error Data DTO: `lib/data/dto/error/error_data_dto.dart`

```dart
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:<project_name>/data/dto/error/error_code_dto.dart';
import 'package:<project_name>/data/dto/error/error_type_dto.dart';
import 'package:<project_name>/data/utils/serialization/nullable_enum_field_key.dart';

part 'error_data_dto.freezed.dart';
part 'error_data_dto.g.dart';

@freezed
sealed class ErrorDataDto with _$ErrorDataDto {
  const factory ErrorDataDto({
    @nullableEnumFieldKey ErrorCodeDto? code,
    @nullableEnumFieldKey ErrorTypeDto? type,
    String? message,
    @JsonKey(includeToJson: false) String? messageLocaleKey,
    String? technicalMessage,
  }) = _ErrorDataDto;

  const ErrorDataDto._();

  factory ErrorDataDto.fromJson(Map<String, Object?> json) =>
      _$ErrorDataDtoFromJson(json);
}
```

### 6. Dio Error Data Extractor: `lib/data/utils/error_handling/dio_error_data_extractor.dart`

```dart
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:<project_name>/data/dto/base_response/base_response_dto.dart';
import 'package:<project_name>/data/dto/error/error_code_dto.dart';
import 'package:injectable/injectable.dart';

typedef _JsonMap = Map<String, Object?>;

/// {@category Utils}
///
/// Extracts error details from [DioException] responses.
///
/// Provides methods to identify error types (timeout, connection, unauthorized)
/// and extract messages from server responses.
@LazySingleton()
class DioErrorDataExtractor {
  ErrorCodeDto? tryExtractErrorCode(Object error) {
    final responseData = tryExtractResponseData(error);

    return responseData?.errorCode;
  }

  String? tryExtractMessage(Object error) {
    final responseData = tryExtractResponseData(error);

    return responseData?.message;
  }

  String? tryExtractTechnicalMessage(Object error) {
    final responseData = tryExtractResponseData(error);

    return responseData?.technicalMessage;
  }

  BaseResponseDto? tryExtractResponseData(Object error) {
    final data = _tryExtractData(error);

    return switch (data) {
      Map() => BaseResponseDto.fromJson(data),
      _ => null,
    };
  }

  bool isTimeout(DioException exception) {
    final type = exception.type;

    return type == DioExceptionType.connectionTimeout ||
        type == DioExceptionType.receiveTimeout ||
        type == DioExceptionType.sendTimeout;
  }

  bool isConnectionProblem(DioException exception) {
    final type = exception.type;

    return type == DioExceptionType.connectionError ||
        type == DioExceptionType.badCertificate ||
        exception.error is SocketException ||
        _isTransportHttpException(exception);
  }

  bool isBadResponse(DioException exception) {
    return exception.type == DioExceptionType.badResponse;
  }

  bool isUnauthorized(DioException exception) {
    final code = tryExtractStatusCode(exception);

    return code == HttpStatus.unauthorized;
  }

  bool isForbidden(DioException exception) {
    final code = tryExtractStatusCode(exception);

    return code == HttpStatus.forbidden;
  }

  bool isNotFound(DioException exception) {
    final code = tryExtractStatusCode(exception);

    return code == HttpStatus.notFound;
  }

  bool isServerError(DioException exception) {
    final code = tryExtractStatusCode(exception);

    if (code == null) {
      return false;
    }

    return code >= 500 && code < 600;
  }

  int? tryExtractStatusCode(DioException e) {
    return e.response?.statusCode;
  }

  bool hasMessage(String? message) {
    return message != null && message.isNotEmpty;
  }

  String requestPath(DioException e) {
    return e.requestOptions.path;
  }

  _JsonMap? _tryExtractData(Object error) {
    final data = switch (error) {
      DioException(:final response) => response?.data,
      _ => null,
    };

    return switch (data) {
      final Map<String, Object?> m => m,
      final Map<Object?, Object?> m => m.map(
        (k, v) => MapEntry(k.toString(), v),
      ),
      _ => null,
    };
  }

  bool _isTransportHttpException(DioException exception) {
    return exception.response == null && exception.error is HttpException;
  }
}
```

### 7. Error Data Extractor: `lib/data/utils/error_handling/error_data_extractor.dart`

```dart
import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:<project_name>/data/dto/error/error_data_dto.dart';
import 'package:<project_name>/data/dto/error/error_type_dto.dart';
import 'package:<project_name>/data/utils/error_handling/dio_error_data_extractor.dart';
import 'package:injectable/injectable.dart';

/// {@category Utils}
///
/// Extracts structured error data from various exception types.
///
/// Handles Dio, timeout, socket, and other common exceptions,
/// converting them to a unified [ErrorDataDto] format.
@LazySingleton()
class ErrorDataExtractor {
  final DioErrorDataExtractor _dioErrorDataExtractor;

  const ErrorDataExtractor({
    required DioErrorDataExtractor dioErrorDataExtractor,
  }) : _dioErrorDataExtractor = dioErrorDataExtractor;

  ErrorDataDto extractErrorData(Object error) {
    return switch (error) {
      DioException() => _fromDioException(error),
      TimeoutException() => _fromTimeoutException(error),
      SocketException() => _fromSocketException(error),
      HandshakeException() => _fromHandshakeException(error),
      StateError() => _fromStateError(error),
      FormatException() => _fromFormatException(error),
      TypeError() => _fromTypeError(error),
      _ => _fromUnknownError(error),
    };
  }

  ErrorDataDto _fromDioException(DioException error) {
    final code = _dioErrorDataExtractor.tryExtractErrorCode(error);
    final type = _extractDioExceptionType(error);
    final message = _dioErrorDataExtractor.tryExtractMessage(error);

    return ErrorDataDto(
      code: code,
      type: type,
      message: message,
      messageLocaleKey: _extractDioMessageLocaleKey(type: type),
      technicalMessage: _extractDioTechnicalMessage(error),
    );
  }

  ErrorTypeDto _extractDioExceptionType(DioException error) {
    if (_dioErrorDataExtractor.isTimeout(error)) {
      return ErrorTypeDto.timeout;
    }

    if (_dioErrorDataExtractor.isConnectionProblem(error)) {
      return ErrorTypeDto.connection;
    }

    if (_dioErrorDataExtractor.isBadResponse(error)) {
      return _extractBadResponseType(error);
    }

    return ErrorTypeDto.response;
  }

  ErrorTypeDto _extractBadResponseType(DioException error) {
    if (_dioErrorDataExtractor.isUnauthorized(error)) {
      return ErrorTypeDto.unauthorized;
    }

    if (_dioErrorDataExtractor.isForbidden(error)) {
      return ErrorTypeDto.forbidden;
    }

    if (_dioErrorDataExtractor.isNotFound(error)) {
      return ErrorTypeDto.notFound;
    }

    if (_dioErrorDataExtractor.isServerError(error)) {
      return ErrorTypeDto.server;
    }

    return ErrorTypeDto.response;
  }

  String? _extractDioMessageLocaleKey({ErrorTypeDto? type}) {
    return switch (type) {
      ErrorTypeDto.unauthorized => 'auth_session_expired',
      _ => 'unknown_error',
    };
  }

  String? _extractDioTechnicalMessage(DioException error) {
    final apiTechnical = _dioErrorDataExtractor.tryExtractTechnicalMessage(
      error,
    );

    if (_dioErrorDataExtractor.hasMessage(apiTechnical)) {
      return apiTechnical;
    }

    final raw = error.error?.toString();

    return _handleTechnicalMessage(raw, error);
  }

  ErrorDataDto _fromTimeoutException(TimeoutException error) {
    return ErrorDataDto(
      type: ErrorTypeDto.timeout,
      technicalMessage: _handleTechnicalMessage(error.message, error),
    );
  }

  ErrorDataDto _fromSocketException(SocketException error) {
    return ErrorDataDto(
      type: ErrorTypeDto.connection,
      technicalMessage: _handleTechnicalMessage(error.message, error),
    );
  }

  ErrorDataDto _fromHandshakeException(HandshakeException error) {
    return ErrorDataDto(
      type: ErrorTypeDto.connection,
      technicalMessage: _handleTechnicalMessage(error.message, error),
    );
  }

  ErrorDataDto _fromStateError(StateError error) {
    return ErrorDataDto(
      type: ErrorTypeDto.state,
      technicalMessage: _handleTechnicalMessage(error.message, error),
    );
  }

  ErrorDataDto _fromFormatException(FormatException error) {
    return ErrorDataDto(
      type: ErrorTypeDto.parsing,
      technicalMessage: _handleTechnicalMessage(error.message, error),
    );
  }

  ErrorDataDto _fromTypeError(TypeError error) {
    return ErrorDataDto(
      type: ErrorTypeDto.type,
      technicalMessage: error.toString(),
    );
  }

  String? _handleTechnicalMessage(String? technicalMessage, Object error) {
    if (technicalMessage != null && technicalMessage.isNotEmpty) {
      return technicalMessage;
    }

    return error.toString();
  }

  ErrorDataDto _fromUnknownError(Object error) {
    return ErrorDataDto(
      type: ErrorTypeDto.unknown,
      messageLocaleKey: 'unknown_error',
      technicalMessage: error.toString(),
    );
  }
}
```

### 8. Error Mapper Override: `lib/data/mappers/error_mapper.dart`

```dart
import 'package:<project_name>/data/dto/error/error_code_dto.dart';
import 'package:<project_name>/data/dto/error/error_type_dto.dart';
import 'package:<project_name>/data/utils/error_handling/error_data_extractor.dart';
import 'package:<project_name>/domain/entities/data_result/app_error_code.dart';
import 'package:<project_name>/domain/entities/data_result/app_error_type.dart';
import 'package:<project_name>/domain/entities/data_result/app_failure.dart';
import 'package:injectable/injectable.dart';

@LazySingleton()
class ErrorMapper {
  final ErrorDataExtractor _errorDataExtractor;

  const ErrorMapper({required ErrorDataExtractor errorDataExtractor})
    : _errorDataExtractor = errorDataExtractor;

  AppFailure mapErrorToAppFailure(Object error, StackTrace stackTrace) {
    final dto = _errorDataExtractor.extractErrorData(error);

    return AppFailure(
      type: _mapErrorTypeDtoToAppErrorType(dto.type),
      code: _mapErrorCodeDtoToAppErrorCode(dto.code),
      message: dto.message,
      messageLocaleKey: dto.messageLocaleKey,
    );
  }

  AppErrorType _mapErrorTypeDtoToAppErrorType(ErrorTypeDto? dto) {
    return AppErrorType.values.firstWhere(
      (e) => e.name == dto?.name,
      orElse: () => AppErrorType.unknown,
    );
  }

  AppErrorCode _mapErrorCodeDtoToAppErrorCode(ErrorCodeDto? dto) {
    return AppErrorCode.values.firstWhere(
      (e) => e.name == dto?.name,
      orElse: () => AppErrorCode.none,
    );
  }
}
```

### 9. Dio Provider Module: `lib/presentation/di/modules/dio_module.dart`

```dart
import 'package:dio/dio.dart';
import 'package:injectable/injectable.dart';

@module
abstract class DioModule {
  @lazySingleton
  Dio dio() {
    final options = BaseOptions(
      connectTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
    );

    return Dio(options);
  }
}
```

## Post-Setup Steps

1. Add `dio` and `freezed_annotation` to `pubspec.yaml` dependencies, and `freezed` + `build_runner` to dev dependencies.
2. Run `rps gen` (or `dart run build_runner build --delete-conflicting-outputs`) to generate `.freezed.dart` and `.g.dart` files.
3. Run `dart format .` and `flutter analyze` with zero errors.
4. Note that `ErrorMapper` now requires `ErrorDataExtractor` in its constructor. Update any manual instantiations or mock setups.

## Important Rules

- This skill **overwrites** `lib/data/mappers/error_mapper.dart` from `clean-arch-init`. Do not preserve the placeholder.
- `DioErrorDataExtractor` and `ErrorDataExtractor` use `{@category Utils}`.
- `ErrorMapper`, DTOs, and enums do **not** use Dartdoc categories.
- `ErrorDataDto` uses `@JsonKey(includeToJson: false)` for `messageLocaleKey` since it is computed, not serialized.
- `BaseResponseDto` is a minimal standalone class. If the project later needs `BaseResponse` as an abstract superclass (for `BaseDataResponse` / `BaseListResponse`), create it and update `BaseResponseDto` to extend it.