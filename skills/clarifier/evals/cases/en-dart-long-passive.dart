// expect: passive: is written; sentence of 30 words; !passive: was sent; !sentence of 28 words; !passive: is kept; ok
/// The cache file is written to the disk by the store each time the user opens the profile screen and the app has a network connection to the remote server.
class ProfileCache {
  // The value was sent by the server and the store keeps it for the next start of the app with no change at all after a cold restart.
  final String note = 'The value is kept by the store';
}
