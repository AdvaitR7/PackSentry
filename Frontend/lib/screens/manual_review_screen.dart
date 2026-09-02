import 'package:flutter/material.dart';

class ManualReviewScreen extends StatelessWidget {
  const ManualReviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Manual Review'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Icon(
              Icons.warning_amber_rounded,
              size: 90,
              color: Colors.orange,
            ),

            const SizedBox(height: 15),

            const Text(
              'Verification Required',
              style: TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.bold,
                color: Colors.orange,
              ),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 10),

            const Text(
              'Some information could not be verified '
              'with sufficient confidence.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey,
              ),
            ),

            const SizedBox(height: 30),

            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Reason for Review',
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),

            const SizedBox(height: 10),

            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.info_outline,
                  color: Colors.orange,
                ),
                title: const Text(
                  'Low OCR Confidence',
                ),
                subtitle: const Text(
                  'Some text on the package could not '
                  'be read clearly.',
                ),
              ),
            ),

            const SizedBox(height: 25),

            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Fields Requiring Attention',
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),

            const SizedBox(height: 10),

            const ReviewFieldCard(
              fieldName: 'Net Quantity',
              value: '500 ?',
              confidence: '62%',
            ),

            const ReviewFieldCard(
              fieldName: 'Manufacturer',
              value: 'ABC Foods',
              confidence: '58%',
            ),

            const SizedBox(height: 25),

            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.edit),
                label: const Text(
                  'Review Information',
                  style: TextStyle(fontSize: 17),
                ),
              ),
            ),

            const SizedBox(height: 12),

            SizedBox(
              width: double.infinity,
              height: 52,
              child: OutlinedButton.icon(
                onPressed: () {
                  Navigator.popUntil(
                    context,
                    (route) => route.isFirst,
                  );
                },
                icon: const Icon(Icons.camera_alt),
                label: const Text(
                  'Scan Again',
                  style: TextStyle(fontSize: 17),
                ),
              ),
            ),

            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

class ReviewFieldCard extends StatelessWidget {
  final String fieldName;
  final String value;
  final String confidence;

  const ReviewFieldCard({
    super.key,
    required this.fieldName,
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
              Icons.warning_amber_rounded,
              color: Colors.orange,
            ),

            const SizedBox(width: 12),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    fieldName,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),

                  const SizedBox(height: 5),

                  Text(value),
                ],
              ),
            ),

            Text(
              confidence,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.orange,
              ),
            ),
          ],
        ),
      ),
    );
  }
}