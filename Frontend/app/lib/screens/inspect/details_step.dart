import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/inspection_wizard_controller.dart';
import '../../models/models.dart';
import '../../theme/app_theme.dart';
import '../../widgets/ps_button.dart';
import '../../widgets/ps_card.dart';
import 'capture_step.dart';

class DetailsStep extends StatelessWidget {
  const DetailsStep({super.key});

  Widget _packageTypeSegment(
    BuildContext context,
    InspectionWizardController controller,
    PackageType type,
    String label,
  ) {
    final isSelected = controller.packageType == type;

    return Expanded(
      child: GestureDetector(
        onTap: () => controller.setPackageType(type),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(9),
            boxShadow: isSelected
                ? const [
                    BoxShadow(
                      color: Color(0x0F000000),
                      blurRadius: 4,
                      offset: Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected ? AppColors.textPrimary : AppColors.textSecondary,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _categoryCard(
    BuildContext context,
    InspectionWizardController controller,
    CommodityCategory category,
    String emoji,
    String label,
  ) {
    final isSelected = controller.commodityCategory == category;

    return Expanded(
      child: GestureDetector(
        onTap: () => controller.setCommodityCategory(category),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFFF0F5FF) : Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isSelected ? AppColors.primary : AppColors.border,
              width: isSelected ? 1.5 : 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(emoji, style: const TextStyle(fontSize: 22)),
              const SizedBox(height: 8),
              Text(
                label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
                  color: isSelected ? const Color(0xFF1A40A6) : AppColors.textPrimary,
                ),
              ),
            ],
          ),
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
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFEBF0FA),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                'STEP 1 OF 3',
                style: TextStyle(
                  fontSize: 11,
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
            const PsSectionHeader(
              title: 'Package Context',
              subtitle: 'Specify packaging classification. Incomplete or unknown context prevents false statutory non-compliance accusations (ADR-0005).',
            ),
            const SizedBox(height: 24),

            // Package Type Segmented Control
            const Text(
              'PACKAGE TYPE',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: AppColors.textSecondary,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: const Color(0xFFEBEDF5),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  _packageTypeSegment(context, controller, PackageType.RETAIL, 'Retail Sale'),
                  _packageTypeSegment(context, controller, PackageType.WHOLESALE, 'Wholesale'),
                  _packageTypeSegment(context, controller, PackageType.INSTITUTIONAL, 'Institutional'),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Commodity Category 2x2 Grid
            const Text(
              'COMMODITY CATEGORY',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: AppColors.textSecondary,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _categoryCard(context, controller, CommodityCategory.FOOD, '🥗', 'Food & FMCG'),
                const SizedBox(width: 10),
                _categoryCard(context, controller, CommodityCategory.COSMETIC, '💄', 'Cosmetics'),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                _categoryCard(context, controller, CommodityCategory.GENERAL, '📦', 'General Goods'),
                const SizedBox(width: 10),
                _categoryCard(context, controller, CommodityCategory.SEEDS, '🌾', 'Seeds & Agri'),
              ],
            ),
            const SizedBox(height: 24),

            // Commodity Attributes Card (Switches)
            PsCard(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Column(
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text(
                      'Imported Commodity',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    subtitle: const Text(
                      'Triggers Rule 6(1)(a) importer address checks',
                      style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                    value: controller.importStatus == ImportStatus.IMPORTED,
                    activeThumbColor: AppColors.primary,
                    onChanged: (isImported) {
                      controller.setImportStatus(
                        isImported ? ImportStatus.IMPORTED : ImportStatus.DOMESTIC,
                      );
                    },
                  ),
                  const Divider(height: 1),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text(
                      'Small Pack (≤ 5 cm³)',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    subtitle: const Text(
                      'Exemption triggers for compact retail units',
                      style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                    value: controller.fourthScheduleKey != null,
                    activeThumbColor: AppColors.primary,
                    onChanged: (isSmall) {
                      controller.setFourthScheduleKey(isSmall ? 'SMALL_PACK_5CM3' : null);
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
      // Floor-pinned CTA button
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: PsButton(
            label: 'Proceed to Image Capture',
            icon: Icons.arrow_forward,
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
      ),
    );
  }
}
