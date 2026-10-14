import 'item.dart';
import 'item_repository.dart';

class StockReport {
  final ItemRepository _repository;

  const StockReport(this._repository);

  Future<List<Item>> itemsToReorder() async {
    final items = await _repository.all();
    return items.where(_needsReorder).toList();
  }

  bool _needsReorder(Item item) {
    return item.quantity > item.reorderLevel;
  }
}
