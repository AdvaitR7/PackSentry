import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  final String label;
  final Color backgroundColor;
  final Color textColor;
  final IconData? icon;
  final bool hasDot;

  const StatusChip({
    super.key,
    required this.label,
    required this.backgroundColor,
    required this.textColor,
    this.icon,
    this.hasDot = false,
  });

  factory StatusChip.compliant([String label = 'COMPLIANT']) {
    return StatusChip(
      label: label,
      backgroundColor: AppColors.compliantBg,
      textColor: AppColors.compliantText,
      hasDot: true,
    );
  }

  factory StatusChip.violation([String label = 'NON-COMPLIANT']) {
    return StatusChip(
      label: label,
      backgroundColor: AppColors.violationBg,
      textColor: AppColors.violationText,
      hasDot: true,
    );
  }

  factory StatusChip.review([String label = 'MANUAL REVIEW']) {
    return StatusChip(
      label: label,
      backgroundColor: AppColors.reviewBg,
      textColor: AppColors.reviewText,
      hasDot: true,
    );
  }

  factory StatusChip.insufficient([String label = 'INSUFFICIENT EVIDENCE']) {
    return StatusChip(
      label: label,
      backgroundColor: AppColors.insufficientBg,
      textColor: AppColors.insufficientText,
      hasDot: true,
    );
  }

  factory StatusChip.ready([String label = 'READY']) {
    return StatusChip(
      label: label,
      backgroundColor: AppColors.compliantBg,
      textColor: AppColors.compliantText,
    );
  }

  factory StatusChip.standby([String label = 'STANDBY']) {
    return StatusChip(
      label: label,
      backgroundColor: AppColors.reviewBg,
      textColor: AppColors.reviewText,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (hasDot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: textColor,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 5),
          ] else if (icon != null) ...[
            Icon(icon, size: 12, color: textColor),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              color: textColor,
              fontWeight: FontWeight.w700,
              fontSize: 10,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}
