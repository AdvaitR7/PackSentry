import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ps_card.dart';
import 'results_screen.dart';

class ProcessingScreen extends StatefulWidget {
  final CaptureContext? captureContext;
  final Uint8List? pdpBytes;
  final Uint8List? backBytes;
  final List<Uint8List> sideImages;
  final String? existingInspectionId;

  const ProcessingScreen({
    super.key,
    this.captureContext,
    this.pdpBytes,
    this.backBytes,
    this.sideImages = const [],
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

  static const Map<String, String> _stageDescriptions = {
    'QUEUED': 'Enqueuing inspection job into server worker queue...',
    'PREPROCESSING': 'Normalising orientation & contrast enhancement...',
    'OCR': 'Extracting raw packaging text with Cloud Vision & PaddleOCR...',
    'EXTRACTING': 'Synthesising D1-D6 statutory declarations...',
    'EVALUATING': 'Evaluating Rules under Legal Metrology 2011 standard...',
    'PERSISTING': 'Writing audit trace & evidence spans to database...',
    'COMPLETE': 'Statutory compliance verification complete.',
  };

  @override
  void initState() {
    super.initState();
    if (widget.existingInspectionId != null) {
      _inspectionId = widget.existingInspectionId;
      _startPolling();
    } else if (widget.captureContext != null &&
        widget.pdpBytes != null &&
        widget.backBytes != null) {
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
        sideImages: widget.sideImages,
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
          final msg = (result['stage_message'] as String?) ??
              (result['error_message'] as String?) ??
              status;

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

    Widget statusIndicator;

    if (isDone) {
      statusIndicator = Container(
        width: 18,
        height: 18,
        decoration: const BoxDecoration(
          color: AppColors.compliantBg,
          shape: BoxShape.circle,
        ),
        child: const Icon(Icons.check, size: 12, color: AppColors.compliantText),
      );
    } else if (isCurrent) {
      statusIndicator = Container(
        width: 18,
        height: 18,
        decoration: const BoxDecoration(
          color: AppColors.primaryLight,
          shape: BoxShape.circle,
        ),
        child: const Center(
          child: SizedBox(
            width: 10,
            height: 10,
            child: CircularProgressIndicator(strokeWidth: 1.5, color: AppColors.primary),
          ),
        ),
      );
    } else {
      statusIndicator = Container(
        width: 18,
        height: 18,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: AppColors.border, width: 1.5),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          statusIndicator,
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              stageName,
              style: TextStyle(
                fontSize: 14,
                fontWeight: isCurrent ? FontWeight.w700 : (isDone ? FontWeight.w600 : FontWeight.w500),
                color: isCurrent
                    ? AppColors.primary
                    : (isDone ? AppColors.textPrimary : AppColors.textSecondary),
              ),
            ),
          ),
          if (isCurrent)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'PROCESSING',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                  color: AppColors.primary,
                  letterSpacing: 0.5,
                ),
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currentIndex = _stages.indexOf(_currentStatus).clamp(0, _stages.length - 1);
    final progressFraction = (currentIndex + 1) / _stages.length;

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
                    Container(
                      width: 72,
                      height: 72,
                      decoration: const BoxDecoration(
                        color: AppColors.violationBg,
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: Icon(Icons.error_outline, size: 40, color: AppColors.violation),
                      ),
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'Inspection Failed',
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _errorMessage!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppColors.violationText, fontSize: 13),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Return to Wizard'),
                      ),
                    ),
                  ],
                )
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Stage Pill
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                      decoration: BoxDecoration(
                        color: AppColors.primaryLight,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        'STAGE ${currentIndex + 1} OF ${_stages.length}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: AppColors.primary,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Glowing Circle Avatar
                    Container(
                      width: 90,
                      height: 90,
                      decoration: BoxDecoration(
                        color: AppColors.darkHero,
                        shape: BoxShape.circle,
                        boxShadow: const [
                          BoxShadow(
                            color: Color(0x332563EB),
                            blurRadius: 24,
                            spreadRadius: 4,
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Text(
                          '⚡',
                          style: TextStyle(fontSize: 36),
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Stage Title & Subtitle
                    Text(
                      _currentStatus == 'QUEUED'
                          ? 'Queued for Analysis...'
                          : (_currentStatus == 'EVALUATING'
                              ? 'Evaluating Rules…'
                              : 'Processing Stage: $_currentStatus'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _stageDescriptions[_currentStatus] ?? _stageMessage,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textSecondary,
                        height: 1.4,
                      ),
                    ),
                    if (_inspectionId != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'ID: $_inspectionId',
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                    const SizedBox(height: 20),

                    // Progress Bar
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: progressFraction,
                        minHeight: 6,
                        backgroundColor: const Color(0xFFE2E8F0),
                        valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Stages Card
                    PsCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Pipeline Progress',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 15,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Divider(height: 1),
                          const SizedBox(height: 4),
                          ..._stages.asMap().entries.map((e) => _stageStep(e.value, e.key)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    const Text(
                      'Encrypted TLS • 750ms polling',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}
