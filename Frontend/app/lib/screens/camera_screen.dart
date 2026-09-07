import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Live viewfinder for capturing a packaging panel.
///
/// Pops the captured JPEG bytes (`Uint8List`) once the inspector confirms the
/// preview, or `null` if they back out. Bytes are read inside this screen so the
/// caller never has to touch the temporary file on disk.
class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _isInitialized = false;
  bool _isCapturing = false;
  String? _errorMessage;

  // Captured but not yet confirmed by the inspector.
  Uint8List? _pendingBytes;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;

    if (state == AppLifecycleState.inactive) {
      controller.dispose();
      _controller = null;
      if (mounted) setState(() => _isInitialized = false);
    } else if (state == AppLifecycleState.resumed && _pendingBytes == null) {
      _initializeCamera();
    }
  }

  Future<void> _initializeCamera() async {
    setState(() {
      _errorMessage = null;
      _isInitialized = false;
    });

    try {
      _cameras = await availableCameras();

      if (_cameras.isEmpty) {
        if (!mounted) return;
        setState(() {
          _errorMessage =
              'No camera was found on this device. Use "Preload Sample Images" '
              'on the capture screen to continue without hardware.';
        });
        return;
      }

      final controller = CameraController(
        _cameras.first,
        ResolutionPreset.high,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      _controller = controller;

      await controller.initialize();
      if (!mounted) return;

      setState(() => _isInitialized = true);
    } on CameraException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = _describeCameraException(e);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorMessage = 'Camera initialisation failed: $e');
    }
  }

  String _describeCameraException(CameraException e) {
    switch (e.code) {
      case 'CameraAccessDenied':
      case 'CameraAccessDeniedWithoutPrompt':
      case 'cameraPermission':
        return 'Camera permission was denied. Enable camera access for '
            'PackSentry in your device settings, then retry.';
      case 'CameraAccessRestricted':
        return 'Camera access is restricted on this device.';
      default:
        return 'Camera error (${e.code}): ${e.description ?? 'unknown failure'}';
    }
  }

  Future<void> _takePicture() async {
    final controller = _controller;
    if (!_isInitialized || controller == null || _isCapturing) return;
    if (controller.value.isTakingPicture) return;

    setState(() => _isCapturing = true);
    await HapticFeedback.mediumImpact();

    try {
      final XFile shot = await controller.takePicture();
      final Uint8List bytes = await shot.readAsBytes();
      if (!mounted) return;

      if (bytes.isEmpty) {
        _showError('Captured image was empty. Please try again.');
        return;
      }

      setState(() => _pendingBytes = bytes);
    } on CameraException catch (e) {
      if (!mounted) return;
      _showError(_describeCameraException(e));
    } catch (e) {
      if (!mounted) return;
      _showError('Failed to capture photo: $e');
    } finally {
      if (mounted) setState(() => _isCapturing = false);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red.shade700),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_pendingBytes != null) {
      return _buildConfirmationView(_pendingBytes!);
    }

    if (_errorMessage != null) {
      return _buildErrorView(_errorMessage!);
    }

    if (!_isInitialized || _controller == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Starting Camera'), centerTitle: true),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Capture Packaging Panel'),
        centerTitle: true,
      ),
      body: Stack(
        children: [
          Positioned.fill(child: CameraPreview(_controller!)),
          Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 30),
              child: FloatingActionButton.large(
                heroTag: 'packsentry_shutter',
                onPressed: _isCapturing ? null : _takePicture,
                child: _isCapturing
                    ? const SizedBox(
                        width: 34,
                        height: 34,
                        child: CircularProgressIndicator(strokeWidth: 3),
                      )
                    : const Icon(Icons.camera_alt, size: 36),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfirmationView(Uint8List bytes) {
    return Scaffold(
      appBar: AppBar(title: const Text('Confirm Panel Photo'), centerTitle: true),
      body: Column(
        children: [
          Expanded(child: Center(child: Image.memory(bytes, fit: BoxFit.contain))),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      setState(() => _pendingBytes = null);
                      if (!_isInitialized) _initializeCamera();
                    },
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retake'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => Navigator.pop<Uint8List>(context, bytes),
                    icon: const Icon(Icons.check),
                    label: const Text('Use This Photo'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(String message) {
    return Scaffold(
      appBar: AppBar(title: const Text('Camera Unavailable'), centerTitle: true),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.no_photography_outlined, size: 54, color: Colors.red),
              const SizedBox(height: 16),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _initializeCamera,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry Camera'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
