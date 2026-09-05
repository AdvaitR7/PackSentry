import 'package:flutter/material.dart';
import '../models/scan_result.dart';
import 'result_screen.dart';

class ProcessingScreen extends StatefulWidget {
  const ProcessingScreen({super.key});

  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends State<ProcessingScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();

    _animation = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(_animationController);
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  ScanResult createSampleResult() {
    return ScanResult(
      productName: 'ABC Foods Product',
      status: ComplianceStatus.compliant,
      fields: [
        ScanField(
          name: 'Manufacturer',
          value: 'ABC Foods Pvt. Ltd.',
          confidence: 0.96,
        ),
        ScanField(
          name: 'Maximum Retail Price',
          value: '₹120',
          confidence: 0.99,
        ),
        ScanField(
          name: 'Net Quantity',
          value: '500 g',
          confidence: 0.91,
        ),
        ScanField(
          name: 'Country of Origin',
          value: 'India',
          confidence: 0.88,
        ),
      ],
      violations: [],
      date: DateTime.now(),
    );
  }

  void showSampleResult() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (context) => ResultScreen(
          result: createSampleResult(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analyzing Product'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedBuilder(
              animation: _animation,
              builder: (context, child) {
                return Transform.rotate(
                  angle: _animation.value * 6.28,
                  child: child,
                );
              },
              child: Container(
                width: 125,
                height: 125,
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.document_scanner_outlined,
                  color: Colors.blue,
                  size: 65,
                ),
              ),
            ),

            const SizedBox(height: 30),

            const Text(
              'Analyzing Product',
              style: TextStyle(
                fontSize: 25,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            Text(
              'Please wait while the system checks the product declarations.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 15,
                height: 1.5,
              ),
            ),

            const SizedBox(height: 30),

            const LinearProgressIndicator(
              minHeight: 7,
              borderRadius: BorderRadius.all(Radius.circular(10)),
            ),

            const SizedBox(height: 30),

            const AnalysisStep(
              icon: Icons.image_search_outlined,
              text: 'Reading product images',
            ),
            const AnalysisStep(
              icon: Icons.text_fields,
              text: 'Extracting product information',
            ),
            const AnalysisStep(
              icon: Icons.rule_folder_outlined,
              text: 'Checking compliance rules',
            ),

            const SizedBox(height: 30),

            OutlinedButton.icon(
              onPressed: showSampleResult,
              icon: const Icon(Icons.visibility_outlined),
              label: const Text('Show Sample Result'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 13,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class AnalysisStep extends StatelessWidget {
  final IconData icon;
  final String text;

  const AnalysisStep({
    super.key,
    required this.icon,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 13,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.grey.shade200,
        ),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: Colors.blue,
            size: 24,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const Icon(
            Icons.check_circle_outline,
            color: Colors.green,
            size: 21,
          ),
        ],
      ),
    );
  }
}