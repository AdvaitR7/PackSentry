import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../../models/models.dart';
import 'capture_step.dart';

class DetailsStep extends StatelessWidget {
  const DetailsStep({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<InspectionWizardController>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('New Inspection — 1/3 Details'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Package Context',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            const Text(
              'Specify packaging classification. Incomplete or unknown context prevents false statutory non-compliance accusations (ADR-0005).',
              style: TextStyle(color: Colors.grey, fontSize: 14),
            ),
            const SizedBox(height: 24),

            // Package Type Dropdown
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Package Type', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<PackageType>(
                      initialValue: controller.packageType,
                      decoration: const InputDecoration(border: OutlineInputBorder()),
                      items: PackageType.values.map((type) {
                        return DropdownMenuItem(
                          value: type,
                          child: Text(type.name),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) controller.setPackageType(val);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Commodity Category Dropdown
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Commodity Category', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<CommodityCategory>(
                      initialValue: controller.commodityCategory,
                      decoration: const InputDecoration(border: OutlineInputBorder()),
                      items: CommodityCategory.values.map((cat) {
                        return DropdownMenuItem(
                          value: cat,
                          child: Text(cat.name),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) controller.setCommodityCategory(val);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Import Status Dropdown
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Origin / Import Status', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<ImportStatus>(
                      initialValue: controller.importStatus,
                      decoration: const InputDecoration(border: OutlineInputBorder()),
                      items: ImportStatus.values.map((status) {
                        return DropdownMenuItem(
                          value: status,
                          child: Text(status.name),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) controller.setImportStatus(val);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 28),

            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.arrow_forward),
                label: const Text('Proceed to Image Capture', style: TextStyle(fontSize: 17)),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ChangeNotifierProvider.value(
                        value: controller,
                        child: const CaptureStep(),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
