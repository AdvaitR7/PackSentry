import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../../theme/app_theme.dart';
import '../../widgets/ps_card.dart';
import '../processing_screen.dart';

class ReviewStep extends StatelessWidget {
  const ReviewStep({super.key});

  static const double _thumbWidth = 104;

  Widget _thumb(Uint8ListLabel label) {
    if (label.bytes == null) {
      return SizedBox(
        width: _thumbWidth,
        child: Column(
          children: [
            Container(
              height: 90,
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: const Center(
                child: Icon(
                  Icons.no_photography_outlined,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label.title,
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }
    return SizedBox(
      width: _thumbWidth,
      child: Column(
        children: [
          Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(
                  label.bytes!,
                  height: 90,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),
              Positioned(
                top: 4,
                right: 4,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: const BoxDecoration(
                    color: AppColors.compliant,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.check, size: 12, color: Colors.white),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            label.title,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<InspectionWizardController>();

    return Scaffold(
      appBar: AppBar(
        leading: Navigator.canPop(context)
            ? IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => Navigator.pop(context),
              )
            : null,
        title: const Text('New Inspection — 3/3 Review'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            const Text(
              'Confirm Inspection Details',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Review package context and captured panels before submitting for statutory analysis.',
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),

            // Package Summary Card
            PsCard(
              child: Column(
                children: [
                  _summaryRow('Package Type', controller.packageType.name),
                  const Divider(height: 1),
                  _summaryRow('Commodity Category', controller.commodityCategory.name),
                  const Divider(height: 1),
                  _summaryRow('Import Status', controller.importStatus.name),
                  const Divider(height: 1),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'All Panels Captured',
                          style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: controller.allPanelsCaptured
                                ? AppColors.compliantBg
                                : AppColors.reviewBg,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            controller.allPanelsCaptured ? 'Yes' : 'No',
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                              color: controller.allPanelsCaptured
                                  ? AppColors.compliantText
                                  : AppColors.reviewText,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Captured Panels Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Captured Panels',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  '${2 + controller.sideImages.length} photos',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: 12),

            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _thumb(Uint8ListLabel('PDP', controller.pdpBytes)),
                  const SizedBox(width: 10),
                  _thumb(Uint8ListLabel('Back', controller.backBytes)),
                  for (var i = 0; i < controller.sideImages.length; i++) ...[
                    const SizedBox(width: 10),
                    _thumb(Uint8ListLabel('Side ${i + 1}', controller.sideImages[i])),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Note card if partial capture
            if (!controller.allPanelsCaptured)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.reviewBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.review.withValues(alpha: 0.3)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.info_outline, color: AppColors.reviewText, size: 20),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Partial capture flagged. Missing declarations will be graded as INSUFFICIENT_EVIDENCE (ADR-0005).',
                        style: TextStyle(fontSize: 12, color: AppColors.textPrimary),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
      // Floor-pinned CTA
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.check_circle_outline),
              label: const Text(
                'Submit for Compliance Analysis',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              onPressed: controller.canSubmit
                  ? () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ProcessingScreen(
                            captureContext: controller.buildCaptureContext(),
                            pdpBytes: controller.pdpBytes!,
                            backBytes: controller.backBytes!,
                            sideImages: controller.sideImages,
                          ),
                        ),
                      );
                    }
                  : null,
            ),
          ),
        ),
      ),
    );
  }
}

class Uint8ListLabel {
  final String title;
  final Uint8List? bytes;
  Uint8ListLabel(this.title, this.bytes);
}
