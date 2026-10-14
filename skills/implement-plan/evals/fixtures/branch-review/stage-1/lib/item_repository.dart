import 'item.dart';

abstract interface class ItemRepository {
  Future<Item?> find(String id);

  Future<List<Item>> all();

  Future<void> save(Item item);
}
