import '../routes.gr.dart';
import 'base_store.dart';

typedef CounterListener = void Function(int value);

const int counterStart = 0;

class CounterStore extends BaseStore<int> with LoggerMixin implements Disposable {
  CounterStore() : super(counterStart);

  CounterStore.fromValue(int value) : super(value);

  final List<CounterListener> listeners = [];

  @override
  Future<void> loadNextPage() async {
    state = state + 1;
    log('page $state');
  }

  DetailsRoute detailsRoute() => DetailsRoute('$state');

  @override
  void dispose() {}
}

CounterStore createCounter() => CounterStore.fromValue(counterStart);
