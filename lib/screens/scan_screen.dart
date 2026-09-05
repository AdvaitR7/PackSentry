import 'package:flutter/material.dart';
import 'camera_screen.dart';
import 'processing_screen.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  String? frontImage;
  String? backImage;
  String? sideImage;

  bool get canAnalyze => frontImage != null;

  void openCamera(String imageType) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CameraScreen(
          imageType: imageType,
          onImageCaptured: (imagePath) {
            setState(() {
              if (imageType == 'Front') {
                frontImage = imagePath;
              } else if (imageType == 'Back') {
                backImage = imagePath;
              } else {
                sideImage = imagePath;
              }
            });
          },
        ),
      ),
    );
  }

  void removeImage(String imageType) {
    setState(() {
      if (imageType == 'Front') {
        frontImage = null;
      } else if (imageType == 'Back') {
        backImage = null;
      } else {
        sideImage = null;
      }
    });
  }

  void analyzeProduct() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const ProcessingScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final capturedCount = [
      frontImage,
      backImage,
      sideImage,
    ].where((image) => image != null).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Product'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Capture Product Images',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Take clear photos of the product package for accurate analysis.',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 15,
                height: 1.4,
              ),
            ),

            const SizedBox(height: 20),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.blue.shade100,
                ),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.photo_camera_outlined,
                    color: Colors.blue,
                    size: 30,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      '$capturedCount of 3 images captured',
                      style: const TextStyle(
                        color: Colors.blue,
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 25),

            ImageCaptureCard(
              title: 'Front Image',
              description: 'Capture the front side of the package',
              icon: Icons.crop_portrait,
              imagePath: frontImage,
              requiredImage: true,
              onCapture: () => openCamera('Front'),
              onRemove: () => removeImage('Front'),
            ),

            ImageCaptureCard(
              title: 'Back Image',
              description: 'Capture ingredients and manufacturer details',
              icon: Icons.flip,
              imagePath: backImage,
              onCapture: () => openCamera('Back'),
              onRemove: () => removeImage('Back'),
            ),

            ImageCaptureCard(
              title: 'Side Image',
              description: 'Capture additional product declarations',
              icon: Icons.view_sidebar,
              imagePath: sideImage,
              onCapture: () => openCamera('Side'),
              onRemove: () => removeImage('Side'),
            ),

            const SizedBox(height: 15),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: canAnalyze ? analyzeProduct : null,
                icon: const Icon(Icons.analytics_outlined),
                label: const Text('Analyze Product'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),

            if (!canAnalyze) ...[
              const SizedBox(height: 10),
              const Center(
                child: Text(
                  'Capture the front image to continue',
                  style: TextStyle(
                    color: Colors.grey,
                    fontSize: 13,
                  ),
                ),
              ),
            ],

            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

class ImageCaptureCard extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;
  final String? imagePath;
  final bool requiredImage;
  final VoidCallback onCapture;
  final VoidCallback onRemove;

  const ImageCaptureCard({
    super.key,
    required this.title,
    required this.description,
    required this.icon,
    required this.imagePath,
    required this.onCapture,
    required this.onRemove,
    this.requiredImage = false,
  });

  @override
  Widget build(BuildContext context) {
    final hasImage = imagePath != null;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: hasImage ? Colors.green.shade200 : Colors.grey.shade200,
          width: 1.3,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: hasImage
                      ? Colors.green.shade50
                      : Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  hasImage ? Icons.check_circle : icon,
                  color: hasImage ? Colors.green : Colors.blue,
                  size: 28,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            title,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        if (requiredImage) ...[
                          const SizedBox(width: 6),
                          const Text(
                            'Required',
                            style: TextStyle(
                              color: Colors.red,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      hasImage ? 'Image captured successfully' : description,
                      style: TextStyle(
                        color: hasImage
                            ? Colors.green.shade700
                            : Colors.grey.shade600,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          if (hasImage)
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onCapture,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retake'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onRemove,
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Remove'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                    ),
                  ),
                ),
              ],
            )
          else
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onCapture,
                icon: const Icon(Icons.camera_alt_outlined),
                label: const Text('Capture Image'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 13),
                  foregroundColor: Colors.blue,
                  side: const BorderSide(color: Colors.blue),
                ),
              ),
            ),
        ],
      ),
    );
  }
}