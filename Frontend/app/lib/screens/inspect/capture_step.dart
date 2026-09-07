import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../camera_screen.dart';
import 'review_step.dart';

class CaptureStep extends StatelessWidget {
  const CaptureStep({super.key});

  Future<void> _captureFromCamera(
    BuildContext context,
    Function(Uint8List) onBytesCaptured,
  ) async {
    final imagePath = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const CameraScreen()),
    );

    if (imagePath == null) return;
    final bytes = await File(imagePath).readAsBytes();
    onBytesCaptured(bytes);
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

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: hasImage ? Colors.green : (isRequired ? Colors.blue : Colors.grey.shade300),
          width: 1.5,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  hasImage ? Icons.check_circle : Icons.camera_alt_outlined,
                  color: hasImage ? Colors.green : (isRequired ? Colors.blue : Colors.grey),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title + (isRequired ? ' *' : ' (Optional)'),
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
                if (hasImage)
                  TextButton(
                    onPressed: onRemove,
                    child: const Text('Remove', style: TextStyle(color: Colors.red)),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(subtitle, style: const TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 12),
            GestureDetector(
              onTap: onCapture,
              child: Container(
                height: 150,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: hasImage
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.memory(imageBytes, fit: BoxFit.cover, width: double.infinity),
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_a_photo_outlined, size: 36, color: Colors.grey.shade600),
                          const SizedBox(height: 8),
                          Text('Tap to photograph panel', style: TextStyle(color: Colors.grey.shade600)),
                        ],
                      ),
              ),
            ),
            if (hasImage) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: onCapture,
                icon: const Icon(Icons.camera_alt),
                label: const Text('Retake Photo'),
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
            _panelCard(
              context: context,
              title: 'Principal Display Panel (PDP)',
              subtitle: 'Front label containing Net Quantity and commodity name.',
              isRequired: true,
              imageBytes: controller.pdpBytes,
              onCapture: () => _captureFromCamera(context, (bytes) => controller.setPdpBytes(bytes)),
              onRemove: () => controller.setPdpBytes(null),
            ),
            _panelCard(
              context: context,
              title: 'Back Panel (BACK)',
              subtitle: 'Information panel declaring MRP, Date, Manufacturer, and Consumer Care.',
              isRequired: true,
              imageBytes: controller.backBytes,
              onCapture: () => _captureFromCamera(context, (bytes) => controller.setBackBytes(bytes)),
              onRemove: () => controller.setBackBytes(null),
            ),
            _panelCard(
              context: context,
              title: 'Side Panel (SIDE)',
              subtitle: 'Supplementary panel declarations if applicable.',
              isRequired: false,
              imageBytes: controller.sideBytes,
              onCapture: () => _captureFromCamera(context, (bytes) => controller.setSideBytes(bytes)),
              onRemove: () => controller.setSideBytes(null),
            ),
            const SizedBox(height: 8),

            // All Images Captured Toggle (ADR-0005 Absence Evidence Gate)
            Card(
              color: controller.allPanelsCaptured
                  ? Colors.blue.withValues(alpha: 0.05)
                  : Colors.amber.withValues(alpha: 0.1),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(
                  color: controller.allPanelsCaptured ? Colors.blue.shade200 : Colors.amber.shade400,
                  width: 1,
                ),
              ),
              child: SwitchListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                title: const Text(
                  'All Images / Panels Captured',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                subtitle: Text(
                  controller.allPanelsCaptured
                      ? 'Inspector confirms all packaging panels have been captured and examined.'
                      : 'Partial capture: missing declarations will downgrade to INSUFFICIENT_EVIDENCE rather than NON_COMPLIANT (ADR-0005).',
                  style: const TextStyle(fontSize: 13),
                ),
                value: controller.allPanelsCaptured,
                onChanged: (val) => controller.setAllPanelsCaptured(val),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.arrow_forward),
                label: const Text('Review & Submit Inspection', style: TextStyle(fontSize: 17)),
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
            if (!controller.canProceedToReview)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Center(
                  child: Text(
                    'Capture both PDP and Back panel images to continue.',
                    style: TextStyle(color: Colors.grey, fontSize: 13),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
