import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

import '../widgets/fixed_width_button.dart';

class BookingScreen extends StatelessWidget {
  final String date;
  final String time;
  final VoidCallback onCancel;

  const BookingScreen({
    required this.date,
    required this.time,
    required this.onCancel,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'bookingSlot'.tr(namedArgs: {'date': date, 'time': time}),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            Text('cancelLateDescr'.tr()),
            const SizedBox(height: 16),
            FixedWidthButton(label: 'cancelBooking'.tr(), onPressed: onCancel),
          ],
        ),
      ),
    );
  }
}
