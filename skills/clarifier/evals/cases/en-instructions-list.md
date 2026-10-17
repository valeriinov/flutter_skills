<!-- expect: !list of; !paragraph of; !-ing form; ok -->
# Checks

The release needs eight checks:

- tests pass
- the changelog lists the fix
- the version goes up
- the tag points at the merge
- the build uploads
- the store accepts the build
- the notes name the fix
- the team gets a message

The cache keeps each entry for one hour. The app reads the cache first. A miss goes to the server. The server sends fresh data. The app writes it to the cache. The old entry goes away. The user sees the new data.

Whether the cache is loading.
