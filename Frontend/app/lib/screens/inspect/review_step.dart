import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../processing_screen.dart';

class ReviewStep extends StatelessWidget {
  const ReviewStep({super.key});

  /// Fixed-width so up to six panels can scroll horizontally without overflowing.
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
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(child: Icon(Icons.no_photography_outlined, color: Colors.grey)),
            ),
            const SizedBox(height: 4),
            Text(label.title, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
      );
    }
    return SizedBox(
      width: _thumbWidth,
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Image.memory(label.bytes!, height: 90, width: double.infinity, fit: BoxFit.cover),
          ),
          const SizedBox(height: 4),
          Text(label.title, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<InspectionWizardController>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('New Inspection — 3/3 Review'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Confirm Inspection Details',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    _summaryRow('Package Type', controller.packageType.name),
                    _summaryRow('Commodity Category', controller.commodityCategory.name),
                    _summaryRow('Import Status', controller.importStatus.name),
                    _summaryRow('All Panels Captured', controller.allPanelsCaptured ? 'Yes' : 'No'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text('Captured Panels', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 10),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
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
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.check_circle_outline),
                label: const Text('Submit for Compliance Analysis', style: TextStyle(fontSize: 17)),
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
          ],
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
