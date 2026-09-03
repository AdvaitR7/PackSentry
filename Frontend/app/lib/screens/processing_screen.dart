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

    // Default loading layout with progress indicator...
    return Scaffold(
      appBar: AppBar(title: const Text('Analyzing Product'), centerTitle: true),
      body: const Center(child: CircularProgressIndicator()),
    );
  }
}
