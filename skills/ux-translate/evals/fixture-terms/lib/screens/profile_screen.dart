import 'package:flutter/material.dart';

class PhoneController extends ChangeNotifier {
  String? errorKey;

  Future<void> validate(String phone) async {
    try {
      final isValid = await PhoneValidator.isValid(phone);
      errorKey = isValid ? null : LocaleKeys.phoneFormatError;
    } catch (_) {
      errorKey = LocaleKeys.phoneFieldError;
    }
    notifyListeners();
  }
}

class ProfileScreen extends StatelessWidget {
  final PhoneController controller;

  const ProfileScreen({required this.controller, super.key});

  @override
  Widget build(BuildContext context) => Column(children: [
        TextField(decoration: InputDecoration(errorText: controller.errorKey?.tr())),
        Text(LocaleKeys.deleteAccountTitle.tr()),
      ]);
}
