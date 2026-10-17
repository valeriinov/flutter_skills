// expect: passive: is cached; !weak modal; !-ing form; !passive: be written; ok
/// Returns the profile that is cached by the store.
///
/// The call may return null when the store is empty. See [ProfileStore.loading].
///
/// ```dart
/// final profile = store.read(); // should be written as running code
/// ```
class ProfileStore {
  // Is the store running? It should be.
  String? read() => null;
}
