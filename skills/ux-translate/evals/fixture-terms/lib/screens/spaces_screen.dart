import 'package:flutter/material.dart';
import '../widgets/fixed_width_button.dart';
import 'archive_screen.dart';

class SpacesScreen extends StatelessWidget {
  const SpacesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Row(children: [
        Text(LocaleKeys.spacesTitle.tr()),
        FixedWidthButton(
          label: LocaleKeys.openArchiveButton.tr(),
          onPressed: () => Navigator.of(context).push(ArchiveScreen.route()),
        ),
      ]),
      Text(LocaleKeys.hostCardTitle.tr()),
      Text(LocaleKeys.hostOnSiteDescr.tr()),
      FilledButton(onPressed: () {}, child: Text(LocaleKeys.hostContactButton.tr())),
      FilledButton(onPressed: () {}, child: Text(LocaleKeys.selectDateButton.tr())),
      FilledButton(onPressed: () {}, child: Text(LocaleKeys.bookDeskButton.tr())),
    ]);
  }
}
