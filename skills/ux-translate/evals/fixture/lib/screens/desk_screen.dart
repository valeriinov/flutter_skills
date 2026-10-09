import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

import '../widgets/fixed_width_button.dart';

class DeskScreen extends StatelessWidget {
  final int freeDeskCount;
  final VoidCallback onBook;

  const DeskScreen({
    required this.freeDeskCount,
    required this.onBook,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('bookingScreenTitle'.tr())),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('freeDesks'.plural(freeDeskCount)),
            const SizedBox(height: 8),
            Text(
              'deskDescription'.tr(),
              softWrap: true,
            ),
            const SizedBox(height: 16),
            FixedWidthButton(label: 'bookDesk'.tr(), onPressed: onBook),
          ],
        ),
      ),
    );
  }
}
