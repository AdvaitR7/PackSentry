import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ps_card.dart';

class RulesScreen extends StatefulWidget {
  const RulesScreen({super.key});

  @override
  State<RulesScreen> createState() => _RulesScreenState();
}

class _RulesScreenState extends State<RulesScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> _rules = [];
  List<dynamic> _filteredRules = [];
  bool _isLoading = true;
  String? _error;
  final TextEditingController _searchController = TextEditingController();

  int _selectedFilter = 0;
  static const List<String> _filters = ['All', 'Mandatory', 'Units', '2026'];

  @override
  void initState() {
    super.initState();
    _fetchRules();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _fetchRules() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final rules = await _apiService.getRules();
      if (!mounted) return;
      setState(() {
        _rules = rules;
        _filteredRules = rules;
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

  void _filterRules(String query) {
    List<dynamic> base;
    if (_selectedFilter == 0) {
      base = _rules;
    } else if (_selectedFilter == 1) {
      base = _rules
          .where((r) => (r['provision'] as String? ?? '').toLowerCase().contains('rule 6'))
          .toList();
    } else if (_selectedFilter == 2) {
      base = _rules
          .where((r) => (r['provision'] as String? ?? '').toLowerCase().contains('rule 13'))
          .toList();
    } else {
      base = _rules
          .where((r) => (r['gsr'] as String? ?? '').contains('418(E)'))
          .toList();
    }

    if (query.isEmpty) {
      setState(() {
        _filteredRules = base;
      });
      return;
    }

    final lower = query.toLowerCase();
    setState(() {
      _filteredRules = base.where((r) {
        final title = (r['title'] as String? ?? '').toLowerCase();
        final prov = (r['provision'] as String? ?? '').toLowerCase();
        final ruleId = (r['rule_id'] as String? ?? '').toLowerCase();
        return title.contains(lower) || prov.contains(lower) || ruleId.contains(lower);
      }).toList();
    });
  }

  Widget _filterChip(String label, int index) {
    final isSelected = _selectedFilter == index;

    return GestureDetector(
      onTap: () {
        setState(() {
          _selectedFilter = index;
        });
        _filterRules(_searchController.text);
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.darkHero : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? AppColors.darkHero : AppColors.border,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            color: isSelected ? Colors.white : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }

  String _ruleIcon(String provision) {
    final lower = provision.toLowerCase();
    if (lower.contains('rule 6')) return '📋';
    if (lower.contains('rule 13')) return '⚖️';
    if (lower.contains('rule 4')) return '🏭';
    if (lower.contains('rule 12') || lower.contains('sch 4')) return '📏';
    return '📜';
  }

  String _ruleSubtitle(Map<String, dynamic> r) {
    final title = r['title'] as String? ?? '';
    if (title.isNotEmpty) return title;
    return '${r['instrument'] as String? ?? ''} (${r['gsr'] as String? ?? ''}, dt. ${r['gazette_date'] as String? ?? ''})';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          children: [
            const Text(
              'Rules Reference',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            Text(
              'LMPC Rules 2011 • ${_rules.length} active provisions',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w400,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchRules,
            tooltip: 'Refresh Rules',
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search provisions…',
                hintStyle: const TextStyle(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                ),
                prefixIcon: const Icon(
                  Icons.search,
                  size: 20,
                  color: AppColors.textSecondary,
                ),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onChanged: _filterRules,
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                for (var i = 0; i < _filters.length; i++) ...[
                  if (i > 0) const SizedBox(width: 8),
                  _filterChip(_filters[i], i),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(color: AppColors.primary),
                  )
                : _error != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                width: 56,
                                height: 56,
                                decoration: const BoxDecoration(
                                  color: AppColors.violationBg,
                                  shape: BoxShape.circle,
                                ),
                                child: const Center(
                                  child: Icon(
                                    Icons.error_outline,
                                    color: AppColors.violation,
                                    size: 32,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'Failed to load rules: $_error',
                                textAlign: TextAlign.center,
                                style: const TextStyle(fontSize: 13),
                              ),
                              const SizedBox(height: 16),
                              SizedBox(
                                width: 160,
                                child: ElevatedButton(
                                  onPressed: _fetchRules,
                                  child: const Text('Retry'),
                                ),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _filteredRules.isEmpty
                        ? const Center(
                            child: Text(
                              'No statutory rules match query.',
                              style: TextStyle(color: AppColors.textSecondary),
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                            itemCount: _filteredRules.length,
                            itemBuilder: (context, index) {
                              final r = _filteredRules[index] as Map<String, dynamic>;
                              final provision = r['provision'] as String? ?? '';
                              final ruleId = r['rule_id'] as String? ?? '';

                              return Container(
                                margin: const EdgeInsets.only(bottom: 10),
                                child: PsCard(
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                  child: Row(
                                    children: [
                                      Container(
                                        width: 36,
                                        height: 36,
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFF0F2FA),
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        child: Center(
                                          child: Text(
                                            _ruleIcon(provision),
                                            style: const TextStyle(fontSize: 16),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              provision,
                                              style: const TextStyle(
                                                fontSize: 11,
                                                fontWeight: FontWeight.w800,
                                                color: AppColors.primary,
                                                letterSpacing: 0.3,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              _ruleSubtitle(r),
                                              style: const TextStyle(
                                                fontSize: 13,
                                                fontWeight: FontWeight.w700,
                                                color: AppColors.textPrimary,
                                              ),
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                            Text(
                                              ruleId,
                                              style: const TextStyle(
                                                fontSize: 11,
                                                color: AppColors.textSecondary,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      const Icon(
                                        Icons.chevron_right,
                                        color: AppColors.textMuted,
                                        size: 20,
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
