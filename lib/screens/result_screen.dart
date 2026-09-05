import 'package:flutter/material.dart';
import '../models/scan_result.dart';
import 'manual_review_screen.dart';

class ResultScreen extends StatelessWidget {
  final ScanResult result;

  const ResultScreen({
    super.key,
    required this.result,
  });

  Color get statusColor {
    switch (result.status) {
      case ComplianceStatus.compliant:
        return Colors.green;
      case ComplianceStatus.violation:
        return Colors.red;
      case ComplianceStatus.manualReview:
        return Colors.orange;
    }
  }

  String get statusTitle {
    switch (result.status) {
      case ComplianceStatus.compliant:
        return 'COMPLIANT';
      case ComplianceStatus.violation:
        return 'VIOLATION FOUND';
      case ComplianceStatus.manualReview:
        return 'MANUAL REVIEW';
    }
  }

  String get statusMessage {
    switch (result.status) {
      case ComplianceStatus.compliant:
        return 'The product passed the available checks.';
      case ComplianceStatus.violation:
        return 'One or more compliance violations were detected.';
      case ComplianceStatus.manualReview:
        return 'This product requires manual verification.';
    }
  }

  IconData get statusIcon {
    switch (result.status) {
      case ComplianceStatus.compliant:
        return Icons.check_circle;
      case ComplianceStatus.violation:
        return Icons.cancel;
      case ComplianceStatus.manualReview:
        return Icons.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isViolation =
        result.status == ComplianceStatus.violation;

    final isManualReview =
        result.status == ComplianceStatus.manualReview;

    final fieldsChecked = result.fields.length;

    final fieldsPassed = result.fields
        .where((field) => field.confidence >= 0.80)
        .length;

    final violationCount = result.violations.length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Compliance Result'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Icon(
              statusIcon,
              size: 90,
              color: statusColor,
            ),

            const SizedBox(height: 15),

            Text(
              statusTitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: statusColor,
              ),
            ),

            const SizedBox(height: 8),

            Text(
              statusMessage,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
              ),
            ),

            const SizedBox(height: 25),

            Text(
              result.productName,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 25),

            if (isViolation) ...[
              ...result.violations.map(
                (violation) => ViolationCard(
                  fieldName: violation.fieldName,
                  detectedValue: violation.detectedValue,
                  requiredValue: violation.requiredValue,
                  rule: violation.description,
                ),
              ),
            ] else ...[
              ...result.fields.map(
                (field) => ResultCard(
                  title: field.name,
                  value: field.value,
                  confidence:
                      '${(field.confidence * 100).round()}%',
                ),
              ),
            ],

            const SizedBox(height: 20),

            SummaryCard(
              fieldsChecked: fieldsChecked,
              fieldsPassed: fieldsPassed,
              violations: violationCount,
              statusColor: statusColor,
            ),

            if (isManualReview) ...[
              const SizedBox(height: 15),

              const ReviewCard(
                reason: 'Low OCR confidence detected.',
              ),

              const SizedBox(height: 20),

              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) =>
                            const ManualReviewScreen(),
                      ),
                    );
                  },
                  icon: const Icon(Icons.rate_review),
                  label: const Text(
                    'Open Manual Review',
                    style: TextStyle(fontSize: 17),
                  ),
                ),
              ),
            ],

            const SizedBox(height: 25),

            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.popUntil(
                    context,
                    (route) => route.isFirst,
                  );
                },
                child: const Text(
                  'Scan Another Product',
                  style: TextStyle(fontSize: 17),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ResultCard extends StatelessWidget {
  final String title;
  final String value;
  final String confidence;

  const ResultCard({
    super.key,
    required this.title,
    required this.value,
    required this.confidence,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(
              Icons.check_circle,
              color: Colors.green,
            ),

            const SizedBox(width: 12),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),

                  const SizedBox(height: 4),

                  Text(value),
                ],
              ),
            ),

            Text(
              confidence,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ViolationCard extends StatelessWidget {
  final String fieldName;
  final String detectedValue;
  final String requiredValue;
  final String rule;

  const ViolationCard({
    super.key,
    required this.fieldName,
    required this.detectedValue,
    required this.requiredValue,
    required this.rule,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.cancel,
                  color: Colors.red,
                ),

                const SizedBox(width: 10),

                Expanded(
                  child: Text(
                    fieldName,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            Text(
              'Detected: $detectedValue',
              style: const TextStyle(fontSize: 15),
            ),

            const SizedBox(height: 5),

            Text(
              'Required: $requiredValue',
              style: const TextStyle(fontSize: 15),
            ),

            const SizedBox(height: 10),

            Text(
              'Issue: $rule',
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                color: Colors.red,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SummaryCard extends StatelessWidget {
  final int fieldsChecked;
  final int fieldsPassed;
  final int violations;
  final Color statusColor;

  const SummaryCard({
    super.key,
    required this.fieldsChecked,
    required this.fieldsPassed,
    required this.violations,
    required this.statusColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Compliance Summary',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 15),

            SummaryRow(
              label: 'Fields Checked',
              value: '$fieldsChecked',
            ),

            SummaryRow(
              label: 'Fields Passed',
              value: '$fieldsPassed',
            ),

            SummaryRow(
              label: 'Violations',
              value: '$violations',
              valueColor: violations > 0
                  ? Colors.red
                  : statusColor,
            ),
          ],
        ),
      ),
    );
  }
}

class SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const SummaryRow({
    super.key,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 16),
          ),

          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: valueColor,
            ),
          ),
        ],
      ),
    );
  }
}

class ReviewCard extends StatelessWidget {
  final String reason;

  const ReviewCard({
    super.key,
    required this.reason,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(
          Icons.warning,
          color: Colors.orange,
        ),
        title: const Text('Review Required'),
        subtitle: Text(reason),
      ),
    );
  }
}