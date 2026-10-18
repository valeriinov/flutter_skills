/// Holds one value and pages through more of it.
abstract class BaseStore<T> {
  BaseStore(this._state);

  T _state;

  T get state => _state;

  set state(T value) {
    _state = value;
  }

  Future<void> loadNextPage();
}

mixin LoggerMixin {
  void log(String message) {}
}

abstract interface class Disposable {
  void dispose();
}
