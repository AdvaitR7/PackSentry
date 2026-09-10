import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'processing_screen.dart';
import 'results_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> _inspections = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final list = await _apiService.listInspections(limit: 50);
      if (!mounted) return;
      setState(() {
        _inspections = list;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _openInspection(String inspectionId) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final result = await _apiService.getInspection(inspectionId);
      if (!mounted) return;
      Navigator.pop(context); // dismiss spinner

      if (result is InspectionResponse) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ResultsScreen(response: result)),
        );
      } else if (result is Map<String, dynamic>) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ProcessingScreen(existingInspectionId: inspectionId),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load inspection: $e')),
      );
    }
  }

  Color _statusColor(String status, String? bucket) {
    if (status == 'FAILED') return AppColors.violation;
    if (status != 'COMPLETE') return AppColors.primary;
    if (bucket == 'POTENTIAL_NON_COMPLIANCE') return AppColors.violation;
    if (bucket == 'MANUAL_REVIEW') return AppColors.review;
    if (bucket == 'INSUFFICIENT_EVIDENCE') return AppColors.insufficient;
    return AppColors.compliant;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inspection History'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchHistory,
            tooltip: 'Refresh History',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: Colors.red),
                        const SizedBox(height: 12),
                        Text('Failed to load history: $_error', textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        ElevatedButton(onPressed: _fetchHistory, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : _inspections.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.history, size: 64, color: Colors.grey.shade400),
                          const SizedBox(height: 12),
                          const Text('No past inspections found.', style: TextStyle(fontSize: 16, color: Colors.grey)),
                          const SizedBox(height: 6),
                          const Text('Complete an inspection in the Inspect tab to view it here.', style: TextStyle(fontSize: 13, color: Colors.grey)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: _inspections.length,
                      itemBuilder: (context, index) {
                        final item = _inspections[index] as Map<String, dynamic>;
                        final id = item['id'] as String? ?? '';
                        final status = item['status'] as String? ?? 'QUEUED';
                        final bucket = item['overall_ui_bucket'] as String?;
                        final created = item['created_at'] as String? ?? '';
                        final color = _statusColor(status, bucket);

                        final displayTag = status == 'COMPLETE'
                            ? (bucket?.replaceAll('_', ' ') ?? 'COMPLETE')
                            : status;

                        return Card(
                          margin: const EdgeInsets.only(bottom: 10),
                          child: ListTile(
                            onTap: () => _openInspection(id),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            leading: CircleAvatar(
                              backgroundColor: color.withValues(alpha: 0.15),
                              child: Icon(
                                status == 'COMPLETE'
                                    ? (bucket == 'POTENTIAL_NON_COMPLIANCE' ? Icons.cancel : Icons.check_circle)
                                    : (status == 'FAILED' ? Icons.error : Icons.sync),
                                color: color,
                              ),
                            ),
                            title: Text(
                              id,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                            ),
                            subtitle: Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                created.replaceFirst('T', ' ').split('.').first,
                                style: const TextStyle(fontSize: 12, color: Colors.grey),
                              ),
                            ),
                            trailing: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: color.withValues(alpha: 0.3)),
                              ),
                              child: Text(
                                displayTag,
                                style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
