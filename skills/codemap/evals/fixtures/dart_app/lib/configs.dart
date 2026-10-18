class FirstConfig {
  void applyConfig(
    String firstSettingValue,
    String secondSettingValue,
    String thirdSettingValue,
    String fourthSettingValue,
    String fifthSettingValue,
    String sixthSettingValue,
    String seventhSettingValue,
  ) {}

  void resetConfig(
    String firstSettingValue,
    String secondSettingValue,
    String thirdSettingValue,
    String fourthSettingValue,
    String fifthSettingValue,
    String sixthSettingValue,
    String seventhSettingValue,
  ) {}
}

class SecondConfig {
  void applyConfig(
    String firstSettingValue,
    String secondSettingValue,
    String thirdSettingValue,
    String fourthSettingValue,
    String fifthSettingValue,
    String sixthSettingValue,
    String seventhSettingValue,
  ) {}

  void resetConfig(
    String firstSettingValue,
    String secondSettingValue,
    String thirdSettingValue,
    String fourthSettingValue,
    String fifthSettingValue,
    String sixthSettingValue,
    String seventhSettingValue,
  ) {}
}

class ThirdConfig {
  void applyConfig(
    String firstSettingValue,
    String secondSettingValue,
    String thirdSettingValue,
    String fourthSettingValue,
    String fifthSettingValue,
    String sixthSettingValue,
    String seventhSettingValue,
  ) {}

  void resetConfig(
    String firstSettingValue,
    String secondSettingValue,
    String thirdSettingValue,
    String fourthSettingValue,
    String fifthSettingValue,
    String sixthSettingValue,
    String seventhSettingValue,
  ) {}
}

void applyAll(FirstConfig first, SecondConfig second, ThirdConfig third) {
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
