import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'results_screen.dart';

class ProcessingScreen extends StatefulWidget {
  final CaptureContext? captureContext;
  final Uint8List? pdpBytes;
  final Uint8List? backBytes;
  final Uint8List? sideBytes;
  final String? existingInspectionId;

  const ProcessingScreen({
    super.key,
    this.captureContext,
    this.pdpBytes,
    this.backBytes,
    this.sideBytes,
    this.existingInspectionId,
  });

  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends State<ProcessingScreen> {
  final ApiService _apiService = ApiService();
  Timer? _pollingTimer;

  String? _inspectionId;
  String _currentStatus = 'QUEUED';
  String _stageMessage = 'Queued for processing...';
  String? _errorMessage;

  static const List<String> _stages = [
    'QUEUED',
    'PREPROCESSING',
    'OCR',
    'EXTRACTING',
    'EVALUATING',
    'PERSISTING',
    'COMPLETE',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.existingInspectionId != null) {
      _inspectionId = widget.existingInspectionId;
      _startPolling();
    } else if (widget.captureContext != null && widget.pdpBytes != null && widget.backBytes != null) {
      _initiateInspection();
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _initiateInspection() async {
    try {
      final res = await _apiService.createInspection(
        context: widget.captureContext!,
        pdpBytes: widget.pdpBytes!,
        backBytes: widget.backBytes!,
        sideBytes: widget.sideBytes,
      );

      if (!mounted) return;
      setState(() {
        _inspectionId = res['inspection_id'] as String?;
        _currentStatus = (res['status'] as String?) ?? 'QUEUED';
      });

      _startPolling();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Failed to start inspection: $e';
      });
    }
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    // Poll every 750ms as specified in ADR-0007
    _pollingTimer = Timer.periodic(const Duration(milliseconds: 750), (timer) async {
      if (_inspectionId == null) return;

      try {
        final result = await _apiService.getInspection(_inspectionId!);

        if (!mounted) return;

        if (result is InspectionResponse) {
          timer.cancel();
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (_) => ResultsScreen(response: result),
            ),
          );
        } else if (result is Map<String, dynamic>) {
          final status = result['status'] as String? ?? 'QUEUED';
          final msg = (result['stage_message'] as String?) ?? (result['error_message'] as String?) ?? status;

          if (status == 'FAILED') {
            timer.cancel();
            setState(() {
              _currentStatus = 'FAILED';
              _errorMessage = msg;
            });
          } else {
            setState(() {
              _currentStatus = status;
              _stageMessage = msg;
            });
          }
        }
      } catch (e) {
        debugPrint('Polling tick error: $e');
      }
    });
  }

  Widget _stageStep(String stageName, int index) {
    final currentIndex = _stages.indexOf(_currentStatus);
    final isDone = currentIndex > index || _currentStatus == 'COMPLETE';
    final isCurrent = _currentStatus == stageName;

    Color color;
    IconData icon;

    if (isDone) {
      color = Colors.green;
      icon = Icons.check_circle;
    } else if (isCurrent) {
      color = Colors.blue;
      icon = Icons.radio_button_checked;
    } else {
      color = Colors.grey.shade400;
      icon = Icons.radio_button_unchecked;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 12),
          Text(
            stageName,
            style: TextStyle(
              fontSize: 15,
              fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
              color: isCurrent ? Colors.blue.shade900 : Colors.black87,
            ),
          ),
          if (isCurrent) ...[
            const Spacer(),
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Compliance Analysis'),
        centerTitle: true,
        automaticallyImplyLeading: _errorMessage != null,
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: _errorMessage != null
              ? Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, size: 70, color: Colors.red),
                    const SizedBox(height: 16),
                    const Text('Inspection Failed', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 10),
                    Text(_errorMessage!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red)),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Return to Wizard'),
                    ),
                  ],
                )
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(
                      width: 70,
                      height: 70,
                      child: CircularProgressIndicator(strokeWidth: 4),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      _stageMessage,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    if (_inspectionId != null)
                      Text(
                        'ID: $_inspectionId',
                        style: const TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    const SizedBox(height: 32),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Pipeline Progress',
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                            const Divider(),
                            ..._stages.asMap().entries.map((e) => _stageStep(e.value, e.key)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}
