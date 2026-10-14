class RateUnavailableException implements Exception {
  final String currency;

  const RateUnavailableException(this.currency);
}

abstract interface class RateSource {
  /// Returns how many units of [currency] one unit of the base currency buys.
  ///
  /// Throws [RateUnavailableException] when no rate is known for [currency].
  Future<double> rate(String currency);
}
