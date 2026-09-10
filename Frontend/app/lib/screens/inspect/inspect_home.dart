import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../controllers/inspection_wizard_controller.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/ps_card.dart';
import '../../widgets/status_chip.dart';
import '../processing_screen.dart';
import '../results_screen.dart';
import 'details_step.dart';

class InspectHomeScreen extends StatefulWidget {
  const InspectHomeScreen({super.key});

  @override
  State<InspectHomeScreen> createState() => _InspectHomeScreenState();
}

class _InspectHomeScreenState extends State<InspectHomeScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> _inspections = [];
  bool _isLoading = true;
  int _completedToday = 0;
  int _violationsFlagged = 0;

  @override
  void initState() {
    super.initState();
    _fetchDashboardData();
  }

  Future<void> _fetchDashboardData() async {
    try {
      final list = await _apiService.listInspections(limit: 20);
      if (!mounted) return;

      final now = DateTime.now();
      int completed = 0;
      int violations = 0;

      for (final item in list) {
        if (item is! Map<String, dynamic>) continue;
        final status = item['status'] as String? ?? '';
        final bucket = item['overall_ui_bucket'] as String? ?? '';
        final overall = item['overall'] as String? ?? '';

        if (status == 'COMPLETE') {
          final createdStr = item['created_at'] as String?;
          if (createdStr != null) {
            try {
              final dt = DateTime.parse(createdStr).toLocal();
              if (dt.year == now.year &&
                  dt.month == now.month &&
                  dt.day == now.day) {
                completed++;
              }
            } catch (_) {
              completed++;
            }
          } else {
            completed++;
          }
        }

        if (bucket == 'POTENTIAL_NON_COMPLIANCE' ||
            overall == 'NON_COMPLIANT') {
          violations++;
        }
      }

      setState(() {
        _inspections = list;
        _completedToday = completed;
        _violationsFlagged = violations;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _openInspection(String inspectionId) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      ),
    );

    try {
      final result = await _apiService.getInspection(inspectionId);
      if (!mounted) return;
      Navigator.pop(context);

      if (result is InspectionResponse) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ResultsScreen(response: result)),
        );
      } else if (result is Map<String, dynamic>) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) =>
                ProcessingScreen(existingInspectionId: inspectionId),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      Navigator.pop(context);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to load inspection: $e')));
    }
  }

  String _formatTimeAgo(String? isoString) {
    if (isoString == null || isoString.isEmpty) return 'Recent';
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays == 1) return 'Yesterday';
      return '${dt.day}/${dt.month}';
    } catch (_) {
      return isoString.replaceFirst('T', ' ').split('.').first;
    }
  }

  String _inspectionTitle(Map<String, dynamic> item) {
    final context = item['context'];
    if (context is Map<String, dynamic>) {
      final category = context['commodity_category'] as String?;
      if (category != null && category.isNotEmpty) {
        final formatted = category.replaceAll('_', ' ');
        return formatted;
      }
    }
    final id = item['id'] as String? ?? '';
    return id.isNotEmpty ? 'Inspection $id' : 'Package Inspection';
  }

  String _inspectionSubtitle(Map<String, dynamic> item) {
    final timeAgo = _formatTimeAgo(item['created_at'] as String?);
    final context = item['context'];
    String typeStr = '';
    if (context is Map<String, dynamic>) {
      final type = context['package_type'] as String?;
      if (type != null && type.isNotEmpty) {
        typeStr = ' • $type';
      }
    }
    return '$timeAgo$typeStr';
  }

  Widget _buildStatusChip(Map<String, dynamic> item) {
    final status = item['status'] as String? ?? 'QUEUED';
    final bucket = item['overall_ui_bucket'] as String?;

    if (status == 'COMPLETE') {
      if (bucket == 'POTENTIAL_NON_COMPLIANCE') {
        return StatusChip.violation('NON-COMPLIANT');
      } else if (bucket == 'MANUAL_REVIEW') {
        return StatusChip.review('MANUAL REVIEW');
      } else if (bucket == 'INSUFFICIENT_EVIDENCE') {
        return StatusChip.insufficient('INSUFFICIENT');
      } else {
        return StatusChip.compliant('COMPLIANT');
      }
    } else if (status == 'FAILED') {
      return StatusChip.violation('FAILED');
    } else {
      return StatusChip.review(status);
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<InspectionWizardController>();

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _fetchDashboardData,
          color: AppColors.primary,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header with Inspector info & status
                Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: const BoxDecoration(
                        color: AppColors.darkHero,
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: Text(
                          'VS',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            controller.inspectorId == 'insp_officer_01'
                                ? 'Officer Sharma'
                                : controller.inspectorId,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const Text(
                            'Zone 4 • Legal Metrology',
                            style: TextStyle(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.compliantBg,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 7,
                            height: 7,
                            decoration: const BoxDecoration(
                              color: AppColors.compliant,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 5),
                          const Text(
                            'Online',
                            style: TextStyle(
                              color: AppColors.compliantText,
                              fontWeight: FontWeight.w700,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Dark Hero Banner Card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    color: AppColors.darkHero,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x260F172A),
                        blurRadius: 24,
                        offset: Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF263859),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'CAMERA SCAN',
                          style: TextStyle(
                            color: Color(0xFF66BFFF),
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'New Package Inspection',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Scan Front, Back, and Side panels for automated Rule 6 & 13 verification.',
                        style: TextStyle(
                          fontSize: 13,
                          color: Color(0xFFA6B8D1),
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 18),
                      SizedBox(
                        width: double.infinity,
                        height: 44,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => ChangeNotifierProvider.value(
                                  value: controller,
                                  child: const DetailsStep(),
                                ),
                              ),
                            );
                          },
                          child: const Text(
                            'Start Inspection →',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Dynamic Metrics Row
                Row(
                  children: [
                    Expanded(
                      child: PsCard(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '$_completedToday',
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                                color: AppColors.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 2),
                            const Text(
                              'Completed Today',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: PsCard(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '$_violationsFlagged',
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                                color: AppColors.violation,
                              ),
                            ),
                            const SizedBox(height: 2),
                            const Text(
                              'Violations Flagged',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Recent Inspections Header with Refresh
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Recent Inspections',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh, size: 18),
                      onPressed: _fetchDashboardData,
                      tooltip: 'Refresh',
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Dynamic Recent Inspections List
                if (_isLoading)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: CircularProgressIndicator(
                        color: AppColors.primary,
                      ),
                    ),
                  )
                else if (_inspections.isEmpty)
                  PsCard(
                    padding: const EdgeInsets.all(20),
                    child: Center(
                      child: Column(
                        children: const [
                          Icon(
                            Icons.inventory_2_outlined,
                            color: AppColors.textSecondary,
                            size: 32,
                          ),
                          SizedBox(height: 8),
                          Text(
                            'No recent inspections recorded yet today.',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'Tap "Start Inspection →" above to begin your first scan.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  ..._inspections.take(5).map((item) {
                    if (item is! Map<String, dynamic>) {
                      return const SizedBox.shrink();
                    }
                    final id = item['id'] as String? ?? '';

                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: PsCard(
                        onTap: id.isNotEmpty ? () => _openInspection(id) : null,
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            Container(
                              width: 38,
                              height: 38,
                              decoration: BoxDecoration(
                                color: const Color(0xFFF0F2FA),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Center(
                                child: Text(
                                  '📦',
                                  style: TextStyle(fontSize: 18),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _inspectionTitle(item),
                                    style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w700,
                                      color: AppColors.textPrimary,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    _inspectionSubtitle(item),
                                    style: const TextStyle(
                                      fontSize: 11,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            _buildStatusChip(item),
                          ],
                        ),
                      ),
                    );
                  }),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
