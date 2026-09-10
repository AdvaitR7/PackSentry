import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../../theme/app_theme.dart';
import '../../widgets/ps_button.dart';
import '../../widgets/ps_card.dart';
import '../camera_screen.dart';

class SidePanelsScreen extends StatelessWidget {
  const SidePanelsScreen({super.key});

  Future<void> _takePhoto(
    BuildContext context,
    Function(Uint8List) onCaptured,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      final bytes = await Navigator.push<Uint8List>(
        context,
        MaterialPageRoute(builder: (_) => const CameraScreen()),
      );
      if (bytes == null || bytes.isEmpty) return;

      onCaptured(bytes);
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Side panel photo attached.'),
          backgroundColor: AppColors.compliant,
          duration: Duration(seconds: 2),
        ),
      );
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(
          content: Text('Could not capture photo: $e'),
          backgroundColor: AppColors.violation,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<InspectionWizardController>();
    final sideImages = controller.sideImages;
    final count = sideImages.length;
    final maxCount = InspectionWizardController.maxSideImages;

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Additional Panels (SIDE)',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFE5F0FF),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '$count / $maxCount ATTACHED',
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  color: AppColors.primary,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Photograph or select images from gallery for supplementary faces '
              '(barcodes, FSSAI logos, importer stickers).',
              style: TextStyle(
                fontSize: 13,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 18),

            // List of attached side panels
            for (var i = 0; i < count; i++) ...[
              PsCard(
                borderColor: AppColors.compliant,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: AppColors.compliantBg,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.memory(
                          sideImages[i],
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) => const Center(
                            child: Icon(Icons.check, color: AppColors.compliant, size: 24),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Side Panel ${i + 1}',
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'side_${i + 1}.jpg • ${(sideImages[i].lengthInBytes / (1024 * 1024)).toStringAsFixed(1)} MB',
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextButton(
                          style: TextButton.styleFrom(
                            backgroundColor: const Color(0xFFF0F2FA),
                            foregroundColor: const Color(0xFF2659B2),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          ),
                          onPressed: () => _takePhoto(
                            context,
                            (bytes) => controller.replaceSideImageAt(i, bytes),
                          ),
                          child: const Text(
                            'Retake',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                          ),
                        ),
                        const SizedBox(width: 6),
                        IconButton(
                          style: IconButton.styleFrom(
                            backgroundColor: AppColors.violationBg,
                            foregroundColor: AppColors.violationText,
                            padding: const EdgeInsets.all(6),
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          ),
                          icon: const Icon(Icons.close, size: 14),
                          onPressed: () => controller.removeSideImageAt(i),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],

            // Add panel card if under cap
            if (controller.canAddSideImage) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: const Color(0xFFCCD9EB),
                    width: 1.5,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Side Panel ${count + 1} (Optional)',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: SizedBox(
                            height: 42,
                            child: ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFFF0F5FF),
                                foregroundColor: AppColors.primary,
                                elevation: 0,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  side: const BorderSide(color: Color(0xFFBFD9FA)),
                                ),
                              ),
                              icon: const Icon(Icons.camera_alt, size: 16),
                              label: const Text(
                                'Take Photo',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                              ),
                              onPressed: () => _takePhoto(
                                context,
                                (bytes) => controller.addSideImage(bytes),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: SizedBox(
                            height: 42,
                            child: OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                backgroundColor: const Color(0xFFF5F7FA),
                                foregroundColor: const Color(0xFF4D5973),
                                side: const BorderSide(color: Color(0xFFE0E5F0)),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                              ),
                              icon: const Icon(Icons.folder_open, size: 16),
                              label: const Text(
                                'Gallery File',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                              ),
                              onPressed: () => _takePhoto(
                                context,
                                (bytes) => controller.addSideImage(bytes),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ] else ...[
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    'Maximum of 4 additional panels attached.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: PsButton(
            label: count > 0 ? 'Done • Save $count Side Panels ✓' : 'Done • No Side Panels',
            onPressed: () => Navigator.pop(context),
          ),
        ),
      ),
    );
  }
}
