import 'package:flutter/material.dart';
import 'manual_review_screen.dart';

enum ComplianceStatus {
  compliant,
  violation,
  manualReview,
}

class ResultScreen extends StatelessWidget {
  final ComplianceStatus status;

  const ResultScreen({
    super.key,
    this.status = ComplianceStatus.compliant,
  });

  @override
  Widget build(BuildContext context) {
    final isCompliant = status == ComplianceStatus.compliant;
    final isViolation = status == ComplianceStatus.violation;

    String title;
    String message;
    IconData icon;
    Color statusColor;

    int fieldsChecked;
    int fieldsPassed;
    int violations;

    if (isCompliant) {
      title = 'COMPLIANT';
      message = 'The product passed the available checks.';
      icon = Icons.check_circle;
      statusColor = Colors.green;

      fieldsChecked = 4;
      fieldsPassed = 4;
      violations = 0;
    } else if (isViolation) {
      title = 'VIOLATION FOUND';
      message = 'One or more compliance violations were detected.';
      icon = Icons.cancel;
      statusColor = Colors.red;

      fieldsChecked = 4;
      fieldsPassed = 2;
      violations = 2;
    } else {
      title = 'MANUAL REVIEW';
      message = 'This product requires manual verification.';
      icon = Icons.warning;
      statusColor = Colors.orange;

      fieldsChecked = 4;
      fieldsPassed = 2;
      violations = 0;
    }

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
              icon,
              size: 90,
              color: statusColor,
            ),

            const SizedBox(height: 15),

            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: statusColor,
              ),
            ),

            const SizedBox(height: 8),

            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
              ),
            ),

            const SizedBox(height: 30),

            if (isViolation) ...[
              const ViolationCard(
                fieldName: 'Net Quantity',
                detectedValue: '500gm',
                requiredValue: '500 g',
                rule: 'Incorrect unit declaration',
              ),

              const ViolationCard(
                fieldName: 'Manufacturer Details',
                detectedValue: 'Information incomplete',
                requiredValue: 'Complete manufacturer declaration',
                rule: 'Required declaration missing',
              ),
            ] else ...[
              const ResultCard(
                title: 'Manufacturer',
                value: 'ABC Foods Pvt. Ltd.',
                confidence: '96%',
              ),

              const ResultCard(
                title: 'MRP',
                value: '₹100',
                confidence: '99%',
              ),

              const ResultCard(
                title: 'Net Quantity',
                value: '500 g',
                confidence: '91%',
              ),

              const ResultCard(
                title: 'Country of Origin',
                value: 'India',
                confidence: '88%',
              ),
            ],

            const SizedBox(height: 20),

            SummaryCard(
              fieldsChecked: fieldsChecked,
              fieldsPassed: fieldsPassed,
              violations: violations,
              statusColor: statusColor,
            ),

            if (!isCompliant && !isViolation) ...[
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
                        builder: (context) => ManualReviewScreen(),
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