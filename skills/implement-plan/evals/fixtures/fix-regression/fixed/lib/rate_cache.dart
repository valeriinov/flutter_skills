import 'rate_source.dart';

class RateCache implements RateSource {
  final RateSource _source;
  final Map<String, double> _rates = {};

  RateCache(this._source);

  @override
  Future<double> rate(String currency) async {
    final cached = _rates[currency];
    if (cached != null) {
      return cached;
    }
    final fetched = await _source.rate(currency);
    _rates[currency] = fetched;
    return fetched;
  }
}
