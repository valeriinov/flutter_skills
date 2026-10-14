import 'item.dart';
import 'item_repository.dart';

class StockImport {
  final ItemRepository _repository;

  const StockImport(this._repository);

  Future<int> importAll(List<Item> items) async {
    for (final item in items) {
      _repository.save(item);
    }
    return items.length;
  }
}
