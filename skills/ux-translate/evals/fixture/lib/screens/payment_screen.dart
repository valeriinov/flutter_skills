import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

import '../widgets/fixed_width_button.dart';

class PaymentScreen extends StatelessWidget {
  final String amount;
  final VoidCallback onPay;
  final VoidCallback onTopUp;

  const PaymentScreen({
    required this.amount,
    required this.onPay,
    required this.onTopUp,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('paymentTitle'.tr())),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('paymentTotal'.tr(namedArgs: {'amount': amount})),
            const SizedBox(height: 16),
            FixedWidthButton(
              label: 'paymentConfirm'.tr(namedArgs: {'amount': amount}),
              onPressed: onPay,
            ),
            TextButton(onPressed: onTopUp, child: Text('topUpCredits'.tr())),
            Text(
              'termsAgree'.tr(),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
