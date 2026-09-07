import 'package:flutter/material.dart';
import '../services/api_service.dart';

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
    if (query.isEmpty) {
      setState(() {
        _filteredRules = _rules;
      });
      return;
    }

    final lower = query.toLowerCase();
    setState(() {
      _filteredRules = _rules.where((r) {
        final title = (r['title'] as String? ?? '').toLowerCase();
        final prov = (r['provision'] as String? ?? '').toLowerCase();
        final ruleId = (r['rule_id'] as String? ?? '').toLowerCase();
        return title.contains(lower) || prov.contains(lower) || ruleId.contains(lower);
      }).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Statutory Rules Catalog'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchRules,
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search rules (e.g. Net Qty, MRP, Rule 13)...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onChanged: _filterRules,
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.error_outline, color: Colors.red, size: 48),
                              const SizedBox(height: 10),
                              Text('Failed to load rules: $_error', textAlign: TextAlign.center),
                              const SizedBox(height: 16),
                              ElevatedButton(onPressed: _fetchRules, child: const Text('Retry')),
                            ],
                          ),
                        ),
                      )
                    : _filteredRules.isEmpty
                        ? const Center(child: Text('No statutory rules match query.'))
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            itemCount: _filteredRules.length,
                            itemBuilder: (context, index) {
                              final r = _filteredRules[index] as Map<String, dynamic>;
                              final ruleId = r['rule_id'] as String? ?? '';
                              final title = r['title'] as String? ?? '';
                              final provision = r['provision'] as String? ?? '';
                              final gsr = r['gsr'] as String? ?? '';
                              final gazetteDate = r['gazette_date'] as String? ?? '';
                              final instrument = r['instrument'] as String? ?? '';

                              return Card(
                                margin: const EdgeInsets.only(bottom: 10),
                                child: Padding(
                                  padding: const EdgeInsets.all(14),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                            decoration: BoxDecoration(
                                              color: Colors.blue.withValues(alpha: 0.1),
                                              borderRadius: BorderRadius.circular(6),
                                            ),
                                            child: Text(
                                              provision,
                                              style: const TextStyle(
                                                color: Colors.blue,
                                                fontWeight: FontWeight.bold,
                                                fontSize: 12,
                                              ),
                                            ),
                                          ),
                                          const Spacer(),
                                          Text(
                                            ruleId,
                                            style: const TextStyle(fontSize: 11, color: Colors.grey),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        title,
                                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        '$instrument ($gsr, dt. $gazetteDate)',
                                        style: const TextStyle(fontSize: 12, color: Colors.black87),
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
