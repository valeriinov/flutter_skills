import 'rate_cache.dart';
import 'rate_source.dart';

class PriceConverter {
  final RateCache _rates;

  PriceConverter(RateSource source) : _rates = RateCache(source);

  /// Converts [amount] in the base currency into [currency].
  ///
  /// Returns null when no rate is available for [currency].
  Future<double?> convert(double amount, String currency) async {
    final rate = await _rates.rate(currency);
    return amount * rate;
  }
}
