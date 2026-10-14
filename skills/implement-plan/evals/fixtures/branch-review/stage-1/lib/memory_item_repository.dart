import 'item.dart';
import 'item_repository.dart';

class MemoryItemRepository implements ItemRepository {
  final Map<String, Item> _items = {};

  @override
  Future<Item?> find(String id) async {
    return _items[id];
  }

  @override
  Future<List<Item>> all() async {
    return _items.values.toList();
  }

  @override
  Future<void> save(Item item) async {
    _items[item.id] = item;
  }
}
