import 'review_screen.dart';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _isInitialized = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    _cameras = await availableCameras();

    if (_cameras.isEmpty) {
      return;
    }

    _controller = CameraController(
      _cameras[0],
      ResolutionPreset.high,
      enableAudio: false,
    );

    await _controller!.initialize();

    if (!mounted) return;

    setState(() {
      _isInitialized = true;
    });
  }

  Future<void> _takePicture() async {
    if (!_isInitialized || _controller == null) {
      return;
    }

    final XFile image = await _controller!.takePicture();

    if (!mounted) return;

final result = await Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => ReviewScreen(
      imagePath: image.path,
    ),
  ),
);

if (result == true && mounted) {
  Navigator.pop(context, image.path);
}
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_isInitialized || _controller == null) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          Positioned.fill(
            child: CameraPreview(_controller!),
          ),

          Positioned(
            top: 50,
            left: 20,
            child: IconButton(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(
                Icons.close,
                color: Colors.white,
                size: 30,
              ),
            ),
          ),

          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Center(
              child: GestureDetector(
                onTap: _takePicture,
                child: Container(
                  width: 75,
                  height: 75,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white,
                      width: 5,
                    ),
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.camera_alt,
                      color: Colors.white,
                      size: 35,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}