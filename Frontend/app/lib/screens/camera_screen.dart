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

    Navigator.pop(context, image.path);
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
      appBar: AppBar(
        title: const Text('Capture Packaging Panel'),
        centerTitle: true,
      ),
      body: Stack(
        children: [
          CameraPreview(_controller!),
          Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 30),
              child: FloatingActionButton.large(
                onPressed: _takePicture,
                child: const Icon(Icons.camera_alt, size: 36),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
