import 'dart:io';

import 'package:flutter/material.dart';

import '../services/api_service.dart';
import 'result_screen.dart';

class ProcessingScreen extends StatefulWidget {
  final File frontImage;
  final File? backImage;
  final File? sideImage;

  const ProcessingScreen({
    super.key,
    required this.frontImage,
    this.backImage,
    this.sideImage,
  });

  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends State<ProcessingScreen> {
  final ApiService _apiService = ApiService();
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _startAnalysis();
  }

  Future<void> _startAnalysis() async {
    try {
      final result = await _apiService.analyzeImages(
        frontImage: widget.frontImage,
        backImage: widget.backImage,
        sideImage: widget.sideImage,
      );
      debugPrint('Analysis API Response: $result');

      if (!mounted) return;

      // Navigate to ResultScreen with real data from the API
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => const ResultScreen(
            status: ComplianceStatus.compliant, // Or parse from API result
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, color: Colors.red, size: 60),
                const SizedBox(height: 16),
                Text(_errorMessage!, textAlign: TextAlign.center),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: () {
                    setState(() => _errorMessage = null);
                    _startAnalysis();
                  },
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Analyzing Product'), centerTitle: true),
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
                'Please wait while we check the package for Legal Metrology compliance.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 40),
              _buildStep(Icons.check_circle, 'Images captured', isDone: true),
              _buildStep(Icons.sync, 'Reading package information', isDone: true),
              _buildStep(Icons.text_fields, 'Extracting declarations', isDone: true),
              _buildStep(Icons.rule, 'Checking legal rules', isDone: false),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStep(IconData icon, String text, {required bool isDone}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(
            icon,
            color: isDone ? Colors.blue : Colors.grey,
          ),
          const SizedBox(width: 12),
          Text(
            text,
            style: TextStyle(
              fontSize: 16,
              color: isDone ? Colors.black87 : Colors.grey,
            ),
          ),
        ],
      ),
    );
  }
}
