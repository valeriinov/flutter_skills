import 'rate_source.dart';

class PriceConverter {
  final RateSource _source;

  const PriceConverter(this._source);

  /// Converts [amount] in the base currency into [currency].
  ///
  /// Returns null when no rate is available for [currency].
  Future<double?> convert(double amount, String currency) async {
    try {
      final rate = await _source.rate(currency);
      return amount / rate;
    } on RateUnavailableException {
      return null;
    }
  }
}
