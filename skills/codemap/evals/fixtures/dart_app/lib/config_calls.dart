import 'configs.dart';

void applyDefaults(FirstConfig first, SecondConfig second, ThirdConfig third) {
  first.applyConfig(
    'first value',
    'second value',
    'third value',
    'fourth value',
    'fifth value',
    'sixth value',
    'seventh value',
  );
  first.resetConfig(
    'first value',
    'second value',
    'third value',
    'fourth value',
    'fifth value',
    'sixth value',
    'seventh value',
  );
  second.applyConfig(
    'first value',
    'second value',
    'third value',
    'fourth value',
    'fifth value',
    'sixth value',
    'seventh value',
  );
  second.resetConfig(
    'first value',
    'second value',
    'third value',
    'fourth value',
    'fifth value',
    'sixth value',
    'seventh value',
  );
  third.applyConfig(
    'first value',
    'second value',
    'third value',
    'fourth value',
    'fifth value',
    'sixth value',
    'seventh value',
  );
  third.resetConfig(
    'first value',
    'second value',
    'third value',
    'fourth value',
    'fifth value',
    'sixth value',
    'seventh value',
  );
}
