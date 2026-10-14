import 'item_repository.dart';

class RestockService {
  final ItemRepository _repository;

  const RestockService(this._repository);

  Future<void> restock(String id, int amount) async {
    final item = await _repository.find(id);
    if (item == null) {
      return;
    }
    _repository.save(item.copyWith(quantity: item.quantity + amount));
  }
}
