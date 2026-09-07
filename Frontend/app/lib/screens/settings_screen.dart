import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final ApiService _apiService = ApiService();
  final TextEditingController _urlController = TextEditingController();
  Map<String, dynamic>? _healthData;
  bool _isLoadingHealth = false;
  String? _healthError;

  @override
  void initState() {
    super.initState();
    _urlController.text = ApiService.baseUrl;
    _checkHealth();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _checkHealth({bool autoDetect = false}) async {
    setState(() {
      _isLoadingHealth = true;
      _healthError = null;
    });

    try {
      final health = await _apiService.getHealthz(forceResolve: autoDetect);
      if (!mounted) return;
      setState(() {
        _healthData = health;
        _urlController.text = ApiService.baseUrl;
        _isLoadingHealth = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _healthError = e.toString();
        _isLoadingHealth = false;
      });
    }
  }

  Widget _healthItem(String label, bool isOk, String subtitle) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(
            isOk ? Icons.check_circle : Icons.warning_amber_rounded,
            color: isOk ? Colors.green : Colors.amber.shade800,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                Text(subtitle, style: const TextStyle(color: Colors.grey, fontSize: 12)),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: (isOk ? Colors.green : Colors.amber).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              isOk ? 'READY' : 'STANDBY',
              style: TextStyle(
                color: isOk ? Colors.green : Colors.amber.shade800,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings & Diagnostics'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Backend Service Endpoint',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            const Text(
              'Specify host for local demo or device testing (ADR-0015 loopback bindings).',
              style: TextStyle(color: Colors.grey, fontSize: 13),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _urlController,
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      labelText: 'API Base URL',
                      contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: () {
                    ApiService.customBaseUrl = _urlController.text.trim();
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Updated Base URL: ${ApiService.baseUrl}')),
                    );
                    _checkHealth();
                  },
                  child: const Text('Save'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                ActionChip(
                  avatar: const Icon(Icons.auto_mode, size: 16),
                  label: const Text('Auto-Detect'),
                  onPressed: () => _checkHealth(autoDetect: true),
                ),
                ActionChip(
                  avatar: const Icon(Icons.usb, size: 16),
                  label: const Text('USB / Local (127.0.0.1)'),
                  onPressed: () {
                    _urlController.text = 'http://127.0.0.1:8000';
                    ApiService.customBaseUrl = 'http://127.0.0.1:8000';
                    _checkHealth();
                  },
                ),
                ActionChip(
                  avatar: const Icon(Icons.phone_android, size: 16),
                  label: const Text('Emulator (10.0.2.2)'),
                  onPressed: () {
                    _urlController.text = 'http://10.0.2.2:8000';
                    ApiService.customBaseUrl = 'http://10.0.2.2:8000';
                    _checkHealth();
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('System Readiness (/healthz)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _checkHealth,
                  tooltip: 'Refresh Health Check',
                ),
              ],
            ),
            const SizedBox(height: 6),

            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: _isLoadingHealth
                    ? const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()))
                    : _healthError != null
                        ? Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.error_outline, color: Colors.red),
                                  const SizedBox(width: 8),
                                  const Text('Service Unreachable', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red)),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(_healthError!, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                              const SizedBox(height: 12),
                              ElevatedButton(onPressed: _checkHealth, child: const Text('Retry Connection')),
                            ],
                          )
                        : Column(
                            children: [
                              _healthItem(
                                'Supabase Postgres Database',
                                _healthData?['database']?['connected'] == true,
                                _healthData?['database']?['connected'] == true ? 'Connected via asyncpg pool' : 'Offline / Mock mode active',
                              ),
                              const Divider(),
                              _healthItem(
                                'Supabase Private Storage',
                                _healthData?['storage']?['configured'] == true,
                                _healthData?['storage']?['configured'] == true ? 'Evidence bucket configured' : 'Using local scratch fallback',
                              ),
                              const Divider(),
                              _healthItem(
                                'Google Cloud Vision OCR',
                                _healthData?['cloud_vision']?['configured'] == true,
                                _healthData?['cloud_vision']?['configured'] == true ? 'ADC credentials active (primary)' : 'Fallback to PaddleOCR active (ADR-0004)',
                              ),
                              const Divider(),
                              _healthItem(
                                'Local PaddleOCR',
                                _healthData?['paddleocr']?['importable'] == true,
                                _healthData?['paddleocr']?['importable'] == true ? 'Local inference ready' : 'Adapter present',
                              ),
                              const Divider(),
                              _healthItem(
                                'Local Ollama Qwen2.5-VL',
                                _healthData?['ollama']?['reachable'] == true,
                                _healthData?['ollama']?['reachable'] == true
                                    ? 'Model ${_healthData?['ollama']?['model']} available'
                                    : 'Ollama daemon offline on localhost:11434',
                              ),
                            ],
                          ),
              ),
            ),
            const SizedBox(height: 24),

            const Text('Legal Metrology Engine', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Card(
              color: Colors.grey.shade50,
              child: const Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Specification: Legal Metrology (Packaged Commodities) Rules, 2011', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    SizedBox(height: 4),
                    Text('Amendment Baseline: G.S.R. 779(E) (2021) & G.S.R. 418(E) (2026)', style: TextStyle(fontSize: 12)),
                    Text('Active Rules: 23 statutory evaluation rules', style: TextStyle(fontSize: 12)),
                    Text('Absence Gate: ADR-0005 strictly enforced', style: TextStyle(fontSize: 12)),
                    Text('Provenance Taint: ADR-0004 evaluator-owned cap enforced', style: TextStyle(fontSize: 12)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
