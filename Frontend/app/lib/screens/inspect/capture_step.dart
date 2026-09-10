import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../../theme/app_theme.dart';
import '../camera_screen.dart';
import 'review_step.dart';
import 'side_panels_screen.dart';

class CaptureStep extends StatelessWidget {
  const CaptureStep({super.key});

  Future<void> _captureFromCamera(
    BuildContext context,
    String panelLabel,
    Function(Uint8List) onBytesCaptured,
  ) async {
    final messenger = ScaffoldMessenger.of(context);

    try {
      final bytes = await Navigator.push<Uint8List>(
        context,
        MaterialPageRoute(builder: (_) => const CameraScreen()),
      );

      if (bytes == null) return;

      if (bytes.isEmpty) {
        messenger.showSnackBar(
          SnackBar(
            content: Text('$panelLabel photo was empty — please retake it.'),
            backgroundColor: AppColors.violation,
          ),
        );
        return;
      }

      onBytesCaptured(bytes);
      messenger.showSnackBar(
        SnackBar(
          content: Text('$panelLabel photo attached.'),
          backgroundColor: AppColors.compliant,
          duration: const Duration(seconds: 2),
        ),
      );
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(
          content: Text('Could not attach $panelLabel photo: $e'),
          backgroundColor: AppColors.violation,
        ),
      );
    }
  }

  Widget _panelCard({
    required BuildContext context,
    required String title,
    required String subtitle,
    required bool isRequired,
    required Uint8List? imageBytes,
    required VoidCallback onCapture,
    required VoidCallback onRemove,
  }) {
    final hasImage = imageBytes != null && imageBytes.isNotEmpty;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: hasImage
              ? AppColors.compliant
              : (isRequired ? AppColors.primary : AppColors.border),
          width: hasImage ? 1.5 : 1,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A0F172A),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: hasImage
                        ? AppColors.compliantBg
                        : (isRequired ? const Color(0xFFE5F0FF) : const Color(0xFFF1F5F9)),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    hasImage ? Icons.check : Icons.camera_alt_outlined,
                    color: hasImage
                        ? AppColors.compliantText
                        : (isRequired ? AppColors.primary : AppColors.textSecondary),
                    size: 16,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title + (isRequired ? ' *' : ' (Optional)'),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                if (hasImage)
                  TextButton(
                    onPressed: onRemove,
                    child: const Text(
                      'Remove',
                      style: TextStyle(
                        color: AppColors.violation,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            GestureDetector(
              onTap: onCapture,
              child: Container(
                height: 140,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: hasImage ? Colors.black : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: hasImage ? Colors.transparent : const Color(0xFFE2E8F0),
                  ),
                ),
                child: hasImage
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: Image.memory(
                          imageBytes,
                          fit: BoxFit.cover,
                          width: double.infinity,
                        ),
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Icon(
                            Icons.add_a_photo_outlined,
                            size: 32,
                            color: AppColors.textSecondary,
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Tap to photograph panel',
                            style: TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
            if (hasImage) ...[
              const SizedBox(height: 10),
              SizedBox(
                height: 38,
                child: OutlinedButton.icon(
                  onPressed: onCapture,
                  icon: const Icon(Icons.camera_alt, size: 16),
                  label: const Text('Retake Photo', style: TextStyle(fontSize: 13)),
                ),
              ),
            ],
          ],
        ),
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
        title: const Text('New Inspection — 2/3 Capture'),
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: 'Preload Sample Images',
            icon: const Icon(Icons.download_outlined),
            onPressed: () => controller.loadSampleImages(),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            const Text(
              'Capture Panels',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Front and Back are required. Sides optional.',
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),

            // Progress status pills (Figma frame 03)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: controller.hasPdp ? AppColors.compliantBg : Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: controller.hasPdp
                              ? AppColors.compliant
                              : const Color(0xFFE2E8F0),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          controller.hasPdp ? 'PDP ✓' : 'PDP ○',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: controller.hasPdp
                                ? AppColors.compliantText
                                : AppColors.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: controller.hasBack ? AppColors.compliantBg : Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: controller.hasBack
                              ? AppColors.compliant
                              : const Color(0xFFE2E8F0),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          controller.hasBack ? 'Back ✓' : 'Back ○',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: controller.hasBack
                                ? AppColors.compliantText
                                : AppColors.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => ChangeNotifierProvider.value(
                              value: controller,
                              child: const SidePanelsScreen(),
                            ),
                          ),
                        );
                      },
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: controller.hasSide ? AppColors.compliantBg : Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: controller.hasSide
                                ? AppColors.compliant
                                : const Color(0xFFE2E8F0),
                          ),
                        ),
                        child: Center(
                          child: Text(
                            controller.hasSide
                                ? 'Side (${controller.sideImages.length}) ✓'
                                : 'Side ○',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: controller.hasSide
                                  ? AppColors.compliantText
                                  : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // PDP Card
            _panelCard(
              context: context,
              title: 'Principal Display Panel (PDP)',
              subtitle: 'Front label containing Net Quantity and commodity name.',
              isRequired: true,
              imageBytes: controller.pdpBytes,
              onCapture: () => _captureFromCamera(
                context,
                'PDP',
                (bytes) => controller.setPdpBytes(bytes),
              ),
              onRemove: () => controller.setPdpBytes(null),
            ),

            // BACK Card
            _panelCard(
              context: context,
              title: 'Back Panel (BACK)',
              subtitle: 'Information panel declaring MRP, Date, Manufacturer, and Consumer Care.',
              isRequired: true,
              imageBytes: controller.backBytes,
              onCapture: () => _captureFromCamera(
                context,
                'Back',
                (bytes) => controller.setBackBytes(bytes),
              ),
              onRemove: () => controller.setBackBytes(null),
            ),

            // Additional panels cards (exact names and count tested by capture_tray_test.dart)
            for (var i = 0; i < controller.sideImages.length; i++)
              _panelCard(
                context: context,
                title: 'Additional Panel ${i + 1} (SIDE)',
                subtitle: 'Supplementary panel declarations if applicable.',
                isRequired: false,
                imageBytes: controller.sideImages[i],
                onCapture: () => _captureFromCamera(
                  context,
                  'Additional panel ${i + 1}',
                  (bytes) => controller.replaceSideImageAt(i, bytes),
                ),
                onRemove: () => controller.removeSideImageAt(i),
              ),

            // Add Side Panel Button & Manage Side Panels shortcut
            if (controller.canAddSideImage)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Column(
                  children: [
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.add_a_photo_outlined),
                        label: Text(
                          controller.sideImages.isEmpty
                              ? 'Add Additional Panel (Optional)'
                              : 'Add Another Panel (${controller.sideImages.length}/${InspectionWizardController.maxSideImages})',
                        ),
                        onPressed: () => _captureFromCamera(
                          context,
                          'Additional panel ${controller.sideImages.length + 1}',
                          (bytes) => controller.addSideImage(bytes),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: TextButton.icon(
                        style: TextButton.styleFrom(
                          foregroundColor: AppColors.primary,
                        ),
                        icon: const Icon(Icons.dashboard_customize_outlined, size: 16),
                        label: const Text(
                          'Open Side Panels Studio (Figma 03b) →',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => ChangeNotifierProvider.value(
                                value: controller,
                                child: const SidePanelsScreen(),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              )
            else
              const Padding(
                padding: EdgeInsets.only(bottom: 16),
                child: Center(
                  child: Text(
                    'Maximum of 4 additional panels attached.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                ),
              ),

            // All Images Captured Toggle (ADR-0005 Absence Evidence Gate)
            Material(
              color: controller.allPanelsCaptured
                  ? const Color(0xFFF0F7FF)
                  : const Color(0xFFFFFBEB),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(
                  color: controller.allPanelsCaptured
                      ? const Color(0xFFBFDBFE)
                      : const Color(0xFFFDE68A),
                ),
              ),
              child: SwitchListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                title: const Text(
                  'All Images / Panels Captured',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
                subtitle: Text(
                  controller.allPanelsCaptured
                      ? 'Inspector confirms all packaging panels have been captured and examined.'
                      : 'Partial capture: missing declarations will downgrade to INSUFFICIENT_EVIDENCE rather than NON_COMPLIANT (ADR-0005).',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
                value: controller.allPanelsCaptured,
                activeThumbColor: AppColors.primary,
                onChanged: (val) => controller.setAllPanelsCaptured(val),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
      // Pinned floor action bar
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!controller.canProceedToReview)
                const Padding(
                  padding: EdgeInsets.only(bottom: 8),
                  child: Text(
                    'Capture both PDP and Back panel images to continue.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                ),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.arrow_forward),
                  label: const Text(
                    'Review & Submit Inspection',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                  onPressed: controller.canProceedToReview
                      ? () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => ChangeNotifierProvider.value(
                                value: controller,
                                child: const ReviewStep(),
                              ),
                            ),
                          );
                        }
                      : null,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
