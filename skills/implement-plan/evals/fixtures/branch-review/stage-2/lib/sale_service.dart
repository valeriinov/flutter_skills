import 'item_repository.dart';

class SaleService {
  final ItemRepository _repository;

  const SaleService(this._repository);

  Future<bool> sell(String id, int amount) async {
    final item = await _repository.find(id);
    if (item == null) {
      return false;
    }
    if (item.quantity < amount) {
      return false;
    }
    _repository.save(item.copyWith(quantity: item.quantity - amount));
    return true;
  }
}
