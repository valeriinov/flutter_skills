# AGENTS.md

## Architecture Rules

### Naming conventions

- Domain entities use context-first names: start with the feature or bounded
  context when it disambiguates the model, then describe the role, and end with
  `Data` for data models. Examples: `TripSearchListRequestData`,
  `ParcelClientListItemData`, `RoutePointData`.
- Shared/base types and enums may omit the feature prefix when the name is
  already clear. Examples: `DataResult`, `AppFailure`, `OrderStatus`.
- Repository contracts use `Repository`; implementations use `RepositoryImpl`.
  Examples: `TripRepository`, `TripRepositoryImpl`.
- Use cases use the `UseCase` suffix and group related actions by feature.
  Examples: `TripSearchUseCase`, `AuthUseCase`.
- Data sources use `RemoteDataSource` or `LocalDataSource` suffix.
  Examples: `TripRemoteDataSource`, `AuthLocalDataSource`.
- Data-layer transfer models use the `Dto` suffix, including request and
  response DTOs. Examples: `TripSearchListRequestDataDto`,
  `TripDetailsResponseDto`.
- Mapper files use `<feature>_mapper.dart`. Examples: `trip_mapper.dart`,
  `auth_mapper.dart`.

### Hard rules

- Dependencies point inward: `presentation/` and `data/` may depend on
  `domain/`; `domain/` must not import `data/`, `presentation/`, Flutter UI,
  network, storage, DTOs, or JSON/storage implementation details.
- Feature UI and state management call domain use cases only, not repositories,
  DTOs, data sources, or repository implementations.
- DTOs must not appear in `domain/` or presentation UI/state code.
- Mappers convert between DTOs and domain models; they do not own business rules.
- Repositories are the data boundary: they hide data sources, convert external
  models through mappers, and expose domain models or domain value types.
- `common/` is for shared cross-cutting utilities only, not feature business logic.
