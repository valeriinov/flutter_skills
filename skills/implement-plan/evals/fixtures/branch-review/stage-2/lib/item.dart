class Item {
  final String id;
  final String name;
  final int quantity;
  final int reorderLevel;

  const Item({
    required this.id,
    required this.name,
    required this.quantity,
    required this.reorderLevel,
  });

  Item copyWith({int? quantity}) {
    return Item(
      id: id,
      name: name,
      quantity: quantity ?? this.quantity,
      reorderLevel: reorderLevel,
    );
  }
}
