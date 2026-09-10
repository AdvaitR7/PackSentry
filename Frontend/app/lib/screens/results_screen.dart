import 'package:flutter/material.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/ps_card.dart';

class ResultsScreen extends StatelessWidget {
  final InspectionResponse response;

  const ResultsScreen({super.key, required this.response});

  String _panelLabel(List<InspectionImageInfo> images, int index) {
    final role = images[index].role;
    final total = images.where((img) => img.role == role).length;
    if (total < 2) return role.name;
    final ordinal = images.take(index + 1).where((img) => img.role == role).length;
    return '${role.name} $ordinal';
  }

  Color _bucketColor(UiBucket bucket) {
    switch (bucket) {
      case UiBucket.COMPLIANT:
        return AppColors.compliant;
      case UiBucket.POTENTIAL_NON_COMPLIANCE:
        return AppColors.violation;
      case UiBucket.MANUAL_REVIEW:
        return AppColors.review;
      case UiBucket.INSUFFICIENT_EVIDENCE:
        return AppColors.insufficient;
      case UiBucket.NOT_APPLICABLE:
      case UiBucket.NOT_EVALUATED:
        return AppColors.notEvaluated;
    }
  }

  Color _bucketBg(UiBucket bucket) {
    switch (bucket) {
      case UiBucket.COMPLIANT:
        return AppColors.compliantBg;
      case UiBucket.POTENTIAL_NON_COMPLIANCE:
        return AppColors.violationBg;
      case UiBucket.MANUAL_REVIEW:
        return AppColors.reviewBg;
      case UiBucket.INSUFFICIENT_EVIDENCE:
        return AppColors.insufficientBg;
      case UiBucket.NOT_APPLICABLE:
      case UiBucket.NOT_EVALUATED:
        return AppColors.notEvaluatedBg;
    }
  }

  IconData _bucketIcon(UiBucket bucket) {
    switch (bucket) {
      case UiBucket.COMPLIANT:
        return Icons.check_circle;
      case UiBucket.POTENTIAL_NON_COMPLIANCE:
        return Icons.cancel;
      case UiBucket.MANUAL_REVIEW:
        return Icons.warning_amber_rounded;
      case UiBucket.INSUFFICIENT_EVIDENCE:
        return Icons.help_outline;
      case UiBucket.NOT_APPLICABLE:
      case UiBucket.NOT_EVALUATED:
        return Icons.remove_circle_outline;
    }
  }

  Widget _summaryChip(String label, int count, Color color, Color bg) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withValues(alpha: 0.2)),
        ),
        child: Column(
          children: [
            Text(
              count.toString(),
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ruleCard(RuleResult result) {
    final color = _bucketColor(result.uiBucket);
    final bg = _bucketBg(result.uiBucket);
    final hasObsExp = result.observed != null || result.expected != null;

    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: color.withValues(alpha: 0.35), width: 1.2),
      ),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
        leading: Icon(_bucketIcon(result.uiBucket), color: color, size: 22),
        title: Text(
          result.citation.provision,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
        ),
        subtitle: Text(
          result.title,
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            result.uiBucket.name.replaceAll('_', ' '),
            style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 10),
          ),
        ),
        childrenPadding: const EdgeInsets.all(14),
        children: [
          // Message
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              result.message,
              style: const TextStyle(fontSize: 13, height: 1.4, color: AppColors.textPrimary),
            ),
          ),
          const SizedBox(height: 10),

          // Observed vs Expected box
          if (hasObsExp) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  if (result.observed != null)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(
                          width: 80,
                          child: Text(
                            'Observed:',
                            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            result.observed!,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  if (result.observed != null && result.expected != null)
                    const SizedBox(height: 6),
                  if (result.expected != null)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(
                          width: 80,
                          child: Text(
                            'Expected:',
                            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            result.expected!,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                              color: AppColors.primary,
                            ),
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],

          // Statutory Citation
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFF0F5FF),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFBFDBFE)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.gavel, size: 14, color: AppColors.primary),
                    const SizedBox(width: 6),
                    Text(
                      'Statutory Citation: ${result.citation.provision}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                        color: AppColors.primary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${result.citation.instrument} (${result.citation.gsr}, dt. ${result.citation.gazetteDate.toIso8601String().split('T').first})',
                  style: const TextStyle(fontSize: 11, color: AppColors.textPrimary),
                ),
                if (result.reasonCode.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Reason Code: ${result.reasonCode}',
                    style: const TextStyle(fontSize: 10, color: AppColors.textSecondary),
                  ),
                ],
              ],
            ),
          ),
        ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final overallColor = _bucketColor(response.overallUiBucket);
    final overallBg = _bucketBg(response.overallUiBucket);
    final rules = response.ruleResults ?? [];

    final violations = rules.where((r) => r.uiBucket == UiBucket.POTENTIAL_NON_COMPLIANCE).toList();
    final manual = rules.where((r) => r.uiBucket == UiBucket.MANUAL_REVIEW).toList();
    final insufficient = rules.where((r) => r.uiBucket == UiBucket.INSUFFICIENT_EVIDENCE).toList();
    final compliant = rules.where((r) => r.uiBucket == UiBucket.COMPLIANT).toList();
    final other = rules.where((r) => r.uiBucket == UiBucket.NOT_APPLICABLE || r.uiBucket == UiBucket.NOT_EVALUATED).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inspection Findings'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Overall Verdict Banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: overallBg,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: overallColor.withValues(alpha: 0.35), width: 1.5),
              ),
              child: Column(
                children: [
                  Icon(_bucketIcon(response.overallUiBucket), size: 48, color: overallColor),
                  const SizedBox(height: 8),
                  Text(
                    response.overallUiBucket.name.replaceAll('_', ' '),
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: overallColor,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Inspection ID: ${response.inspectionId}',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Summary Counts Row
            Row(
              children: [
                _summaryChip('Passed', response.summary.compliant ?? 0, AppColors.compliant, AppColors.compliantBg),
                _summaryChip('Violations', response.summary.potentialNonCompliance ?? 0, AppColors.violation, AppColors.violationBg),
                _summaryChip('Review', response.summary.manualReview ?? 0, AppColors.review, AppColors.reviewBg),
                _summaryChip('N/A', (response.summary.notApplicable ?? 0) + (response.summary.notEvaluated ?? 0), AppColors.notEvaluated, AppColors.notEvaluatedBg),
              ],
            ),
            const SizedBox(height: 20),

            // Evidence Photos (if any)
            if (response.images != null && response.images!.isNotEmpty) ...[
              const Text(
                'Captured Evidence Panels',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 10),
              SizedBox(
                height: 130,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: response.images!.length,
                  itemBuilder: (context, index) {
                    final img = response.images![index];
                    return Container(
                      width: 130,
                      margin: const EdgeInsets.only(right: 10),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(11),
                            child: Image.network(
                              img.originalUrl,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) => Container(
                                color: const Color(0xFFF1F5F9),
                                child: const Center(
                                  child: Icon(Icons.broken_image, color: AppColors.textSecondary),
                                ),
                              ),
                            ),
                          ),
                          Positioned(
                            bottom: 0,
                            left: 0,
                            right: 0,
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              decoration: const BoxDecoration(
                                color: Colors.black54,
                                borderRadius: BorderRadius.vertical(bottom: Radius.circular(11)),
                              ),
                              child: Text(
                                _panelLabel(response.images!, index),
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),
            ],

            // Statutory Rule Findings
            const Text(
              'Statutory Rule Findings',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
            ),
            const SizedBox(height: 10),

            if (violations.isNotEmpty) ...[
              const Text(
                'POTENTIAL NON-COMPLIANCE',
                style: TextStyle(color: AppColors.violation, fontWeight: FontWeight.w800, fontSize: 11),
              ),
              const SizedBox(height: 6),
              ...violations.map(_ruleCard),
            ],

            if (manual.isNotEmpty) ...[
              const Text(
                'MANUAL REVIEW REQUIRED',
                style: TextStyle(color: AppColors.review, fontWeight: FontWeight.w800, fontSize: 11),
              ),
              const SizedBox(height: 6),
              ...manual.map(_ruleCard),
            ],

            if (insufficient.isNotEmpty) ...[
              const Text(
                'INSUFFICIENT EVIDENCE (ABSENCE GATE)',
                style: TextStyle(color: AppColors.insufficient, fontWeight: FontWeight.w800, fontSize: 11),
              ),
              const SizedBox(height: 6),
              ...insufficient.map(_ruleCard),
            ],

            if (compliant.isNotEmpty) ...[
              const Text(
                'COMPLIANT DECLARATIONS',
                style: TextStyle(color: AppColors.compliant, fontWeight: FontWeight.w800, fontSize: 11),
              ),
              const SizedBox(height: 6),
              ...compliant.map(_ruleCard),
            ],

            if (other.isNotEmpty) ...[
              const Text(
                'NOT APPLICABLE / NOT EVALUATED',
                style: TextStyle(color: AppColors.notEvaluated, fontWeight: FontWeight.w800, fontSize: 11),
              ),
              const SizedBox(height: 6),
              ...other.map(_ruleCard),
            ],

            const SizedBox(height: 16),

            // Engine Metadata Card
            PsCard(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Audit & Engine Provenance',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Ruleset: ${response.engine.ruleEngineVersion} (effective as of ${response.engine.rulesetAsOf.toIso8601String().split('T').first})',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                  Text(
                    'OCR Engine: ${response.engine.ocrEngine}',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                  Text(
                    'Alias Table: ${response.engine.aliasTableVersion}',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
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
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.picture_as_pdf_outlined),
              label: const Text(
                'Export Schedule 7 PDF Report',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
              ),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Exporting Schedule 7 statutory inspection sheet...'),
                    duration: Duration(seconds: 2),
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
