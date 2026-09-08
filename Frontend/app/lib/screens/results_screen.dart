import 'package:flutter/material.dart';
import '../models/models.dart';

class ResultsScreen extends StatelessWidget {
  final InspectionResponse response;

  const ResultsScreen({super.key, required this.response});

  /// Labels the evidence card at [index]. An inspection may carry several SIDE
  /// panels, so a role shared by more than one image is numbered to keep the
  /// cards distinguishable; unique roles (PDP, BACK) stay bare.
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
        return Colors.green;
      case UiBucket.POTENTIAL_NON_COMPLIANCE:
        return Colors.red;
      case UiBucket.MANUAL_REVIEW:
        return Colors.orange;
      case UiBucket.INSUFFICIENT_EVIDENCE:
        return Colors.amber.shade800;
      case UiBucket.NOT_APPLICABLE:
      case UiBucket.NOT_EVALUATED:
        return Colors.grey;
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

  Widget _summaryChip(String label, int count, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Text(
            count.toString(),
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color),
          ),
          Text(
            label,
            style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
          ),
        ],
      ),
    );
  }

  Widget _ruleCard(RuleResult result) {
    final color = _bucketColor(result.uiBucket);
    final hasObsExp = result.observed != null || result.expected != null;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: color.withValues(alpha: 0.4), width: 1.2),
      ),
      child: ExpansionTile(
        leading: Icon(_bucketIcon(result.uiBucket), color: color),
        title: Text(
          result.citation.provision,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
        ),
        subtitle: Text(
          result.title,
          style: const TextStyle(fontSize: 13, color: Colors.black87),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            result.uiBucket.name.replaceAll('_', ' '),
            style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 11),
          ),
        ),
        childrenPadding: const EdgeInsets.all(16),
        children: [
          // Message / explanation
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              result.message,
              style: const TextStyle(fontSize: 14, height: 1.4),
            ),
          ),
          const SizedBox(height: 12),

          // Observed vs Expected comparison box
          if (hasObsExp) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                children: [
                  if (result.observed != null)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(width: 80, child: Text('Observed:', style: TextStyle(color: Colors.grey, fontSize: 13))),
                        Expanded(child: Text(result.observed!, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
                      ],
                    ),
                  if (result.observed != null && result.expected != null) const SizedBox(height: 6),
                  if (result.expected != null)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(width: 80, child: Text('Expected:', style: TextStyle(color: Colors.grey, fontSize: 13))),
                        Expanded(child: Text(result.expected!, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Colors.blue))),
                      ],
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],

          // Statutory Citation box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.withValues(alpha: 0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.gavel, size: 16, color: Colors.blue),
                    const SizedBox(width: 6),
                    Text(
                      'Statutory Citation: ${result.citation.provision}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.blue),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  '${result.citation.instrument} (${result.citation.gsr}, dt. ${result.citation.gazetteDate.toIso8601String().split('T').first})',
                  style: const TextStyle(fontSize: 12, color: Colors.black87),
                ),
                if (result.reasonCode.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text('Reason Code: ${result.reasonCode}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final overallColor = _bucketColor(response.overallUiBucket);
    final rules = response.ruleResults ?? [];

    // Group rules by severity
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
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: overallColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: overallColor.withValues(alpha: 0.4), width: 2),
              ),
              child: Column(
                children: [
                  Icon(_bucketIcon(response.overallUiBucket), size: 64, color: overallColor),
                  const SizedBox(height: 10),
                  Text(
                    response.overallUiBucket.name.replaceAll('_', ' '),
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: overallColor,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Inspection ID: ${response.inspectionId}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Summary Counts
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _summaryChip('Passed', response.summary.compliant ?? 0, Colors.green),
                _summaryChip('Violations', response.summary.potentialNonCompliance ?? 0, Colors.red),
                _summaryChip('Review', response.summary.manualReview ?? 0, Colors.orange),
                _summaryChip('N/A', (response.summary.notApplicable ?? 0) + (response.summary.notEvaluated ?? 0), Colors.grey),
              ],
            ),
            const SizedBox(height: 24),

            // Captured Evidence Images
            if (response.images != null && response.images!.isNotEmpty) ...[
              const Text('Captured Evidence Panels', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              SizedBox(
                height: 140,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: response.images!.length,
                  itemBuilder: (context, index) {
                    final img = response.images![index];
                    return Container(
                      width: 140,
                      margin: const EdgeInsets.only(right: 12),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(11),
                            child: Image.network(
                              img.originalUrl,
                              fit: BoxFit.cover,
                              errorBuilder: (ctx, err, stack) => Container(
                                color: Colors.grey.shade200,
                                child: const Center(child: Icon(Icons.broken_image, color: Colors.grey)),
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
                                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 24),
            ],

            // Rule Findings by Priority
            const Text('Statutory Rule Findings', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),

            if (violations.isNotEmpty) ...[
              const Text('POTENTIAL NON-COMPLIANCE', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              ...violations.map(_ruleCard),
            ],

            if (manual.isNotEmpty) ...[
              const Text('MANUAL REVIEW REQUIRED', style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              ...manual.map(_ruleCard),
            ],

            if (insufficient.isNotEmpty) ...[
              const Text('INSUFFICIENT EVIDENCE (ABSENCE GATE)', style: TextStyle(color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              ...insufficient.map(_ruleCard),
            ],

            if (compliant.isNotEmpty) ...[
              const Text('COMPLIANT DECLARATIONS', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              ...compliant.map(_ruleCard),
            ],

            if (other.isNotEmpty) ...[
              const Text('NOT APPLICABLE / NOT EVALUATED', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              ...other.map(_ruleCard),
            ],

            const SizedBox(height: 24),

            // Engine Metadata
            Card(
              color: Colors.grey.shade100,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Audit & Engine Provenance', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 4),
                    Text('Ruleset: ${response.engine.ruleEngineVersion} (effective as of ${response.engine.rulesetAsOf.toIso8601String().split('T').first})', style: const TextStyle(fontSize: 12)),
                    Text('OCR Engine: ${response.engine.ocrEngine}', style: const TextStyle(fontSize: 12)),
                    Text('Alias Table: ${response.engine.aliasTableVersion}', style: const TextStyle(fontSize: 12)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
