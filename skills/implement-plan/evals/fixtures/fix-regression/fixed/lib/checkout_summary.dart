import 'price_converter.dart';

class CheckoutSummary {
  final PriceConverter _converter;

  const CheckoutSummary(this._converter);

  Future<String> totalLabel(double total, String currency) async {
    final converted = await _converter.convert(total, currency);
    if (converted == null) {
      return 'Price unavailable in $currency';
    }
    return '${converted.toStringAsFixed(2)} $currency';
  }
}
