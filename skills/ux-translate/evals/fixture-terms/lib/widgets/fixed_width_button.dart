import 'package:flutter/material.dart';

/// Section header button of a fixed width; one line, cut with an ellipsis.
class FixedWidthButton extends StatelessWidget {
  static const double width = 96;

  final String label;
  final VoidCallback onPressed;

  const FixedWidthButton({required this.label, required this.onPressed, super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: TextButton(
        onPressed: onPressed,
        child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
      ),
    );
  }
}
