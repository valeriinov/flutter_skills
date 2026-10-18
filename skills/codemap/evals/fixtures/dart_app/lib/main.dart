import 'routes.gr.dart' show HomeRoute;
import 'store/counter_store.dart';

void main() {
  const route = HomeRoute();
  final store = createCounter();
  store.loadNextPage();
  print('$route ${store.state}');
}
