import 'package:dart_app/store/counter_store.dart';

void main() {
  final store = CounterStore();
  store.loadNextPage();
}
