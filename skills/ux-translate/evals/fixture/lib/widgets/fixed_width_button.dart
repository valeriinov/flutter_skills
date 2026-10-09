import 'package:flutter/material.dart';

/// Primary action button of a fixed width, shared by every screen.
///
/// The [label] is the localized text; it stays on one line and is cut
/// with an ellipsis when it is wider than the button.
class FixedWidthButton extends StatelessWidget {
  static const double width = 120;

  final String label;
  final VoidCallback onPressed;

  const FixedWidthButton({
    required this.label,
    required this.onPressed,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: 44,
      child: FilledButton(
        onPressed: onPressed,
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}
