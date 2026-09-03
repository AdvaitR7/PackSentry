import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'camera_screen.dart';
import 'processing_screen.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  Uint8List? frontBytes;
  Uint8List? backBytes;
  Uint8List? sideBytes;

  @override
  void initState() {
    super.initState();
    _loadSampleImages();
  }

  Future<void> _loadSampleImages() async {
    try {
      final frontData = await rootBundle.load('assets/images/front.png');
      final backData = await rootBundle.load('assets/images/back.png');
      final sideData = await rootBundle.load('assets/images/side.png');

      if (mounted) {
        setState(() {
          frontBytes = frontData.buffer.asUint8List();
          backBytes = backData.buffer.asUint8List();
          sideBytes = sideData.buffer.asUint8List();
        });
      }
    } catch (e) {
      debugPrint('Could not preload sample images: $e');
    }
  }

  Future<void> captureImage(String side) async {
    final imagePath = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const CameraScreen(),
      ),
    );

    if (imagePath == null) return;

    final bytes = await File(imagePath).readAsBytes();

    setState(() {
      if (side == 'front') {
        frontBytes = bytes;
      } else if (side == 'back') {
        backBytes = bytes;
      } else if (side == 'side') {
        sideBytes = bytes;
      }
    });
  }

  void removeImage(String side) {
    setState(() {
      if (side == 'front') {
        frontBytes = null;
      } else if (side == 'back') {
        backBytes = null;
      } else if (side == 'side') {
        sideBytes = null;
      }
    });
  }

  Widget imageSection({
    required String title,
    required String description,
    required Uint8List? imageBytes,
    required VoidCallback onTap,
    required String side,
  }) {
    final isCaptured = imageBytes != null;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  isCaptured
                      ? Icons.check_circle
                      : Icons.camera_alt_outlined,
                  color: isCaptured ? Colors.green : Colors.blue,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 19,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                if (isCaptured)
                  TextButton(
                    onPressed: () => removeImage(side),
                    child: const Text('Remove'),
                  ),
              ],
            ),

            const SizedBox(height: 5),

            Text(
              description,
              style: const TextStyle(
                color: Colors.grey,
                fontSize: 14,
              ),
            ),

            const SizedBox(height: 12),

            GestureDetector(
              onTap: onTap,
              child: Container(
                height: 170,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isCaptured
                        ? Colors.green
                        : Colors.grey.shade300,
                    width: 1.5,
                  ),
                ),
                child: isCaptured
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(11),
                        child: Image.memory(
                          imageBytes,
                          width: double.infinity,
                          fit: BoxFit.cover,
                        ),
                      )
                    : const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.add_a_photo_outlined,
                            size: 42,
                            color: Colors.grey,
                          ),
                          SizedBox(height: 10),
                          Text(
                            'Tap to capture',
                            style: TextStyle(
                              fontSize: 15,
                              color: Colors.grey,
                            ),
                          ),
                        ],
                      ),
              ),
            ),

            if (isCaptured) ...[
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: onTap,
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Retake Photo'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final capturedCount = [
      frontBytes,
      backBytes,
      sideBytes,
    ].where((image) => image != null).length;

    final canAnalyze = frontBytes != null;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Product'),
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: 'Load Sample Images',
            icon: const Icon(Icons.refresh),
            onPressed: _loadSampleImages,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Capture Product Images',
              style: TextStyle(
                fontSize: 27,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            const Text(
              'Capture clear images of the product package '
              'from different sides.',
              style: TextStyle(
                fontSize: 15,
                color: Colors.grey,
              ),
            ),

            const SizedBox(height: 20),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.photo_library_outlined,
                    color: Colors.blue,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      '$capturedCount of 3 images captured',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            imageSection(
              title: 'Front',
              description: 'Capture the front label of the package.',
              imageBytes: frontBytes,
              side: 'front',
              onTap: () => captureImage('front'),
            ),

            imageSection(
              title: 'Back',
              description: 'Capture declarations on the back.',
              imageBytes: backBytes,
              side: 'back',
              onTap: () => captureImage('back'),
            ),

            imageSection(
              title: 'Side',
              description: 'Capture additional information on the side.',
              imageBytes: sideBytes,
              side: 'side',
              onTap: () => captureImage('side'),
            ),

            const SizedBox(height: 8),

            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                onPressed: canAnalyze
                    ? () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ProcessingScreen(
                              frontBytes: frontBytes!,
                              backBytes: backBytes,
                              sideBytes: sideBytes,
                            ),
                          ),
                        );
                      }
                    : null,
                icon: const Icon(Icons.analytics_outlined),
                label: const Text(
                  'Analyze Product',
                  style: TextStyle(fontSize: 18),
                ),
              ),
            ),

            const SizedBox(height: 12),

            if (!canAnalyze)
              const Center(
                child: Text(
                  'Capture the front image to continue.',
                  style: TextStyle(
                    color: Colors.grey,
                    fontSize: 13,
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