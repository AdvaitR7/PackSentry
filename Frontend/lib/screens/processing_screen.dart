import 'package:flutter/material.dart';
import 'result_screen.dart';

class ProcessingScreen extends StatelessWidget {
  const ProcessingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analyzing Product'),
        centerTitle: true,
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),

              const SizedBox(height: 30),

              const Text(
                'Analyzing Product',
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 12),

              const Text(
                'Please wait while we check the package '
                'for Legal Metrology compliance.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.grey,
                ),
              ),

              const SizedBox(height: 40),

              const ProcessingStep(
                icon: Icons.check_circle,
                text: 'Images captured',
              ),

              const ProcessingStep(
                icon: Icons.sync,
                text: 'Reading package information',
              ),

              const ProcessingStep(
                icon: Icons.text_fields,
                text: 'Extracting declarations',
              ),

              const ProcessingStep(
                icon: Icons.rule,
                text: 'Checking legal rules',
              ),

              const SizedBox(height: 35),

              ElevatedButton(
                onPressed: () {
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const ResultScreen(
                        status: ComplianceStatus.compliant,
                      ),
                    ),
                  );
                },
                child: const Text('Show Sample Result'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ProcessingStep extends StatelessWidget {
  final IconData icon;
  final String text;

  const ProcessingStep({
    super.key,
    required this.icon,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(
            icon,
            color: Colors.blue,
          ),
          const SizedBox(width: 12),
          Text(
            text,
            style: const TextStyle(
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
}