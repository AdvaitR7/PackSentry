import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/ps_card.dart';
import '../widgets/status_chip.dart';

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
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: isOk ? AppColors.compliant : AppColors.review,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(color: AppColors.textSecondary, fontSize: 11),
                ),
              ],
            ),
          ),
          isOk ? StatusChip.ready('READY') : StatusChip.standby('STANDBY'),
        ],
      ),
    );
  }

  Widget _presetChip({
    required String label,
    required String url,
    bool isAutoDetect = false,
  }) {
    final isSelected = !isAutoDetect && _urlController.text.trim() == url;

    return GestureDetector(
      onTap: () {
        if (isAutoDetect) {
          _checkHealth(autoDetect: true);
        } else {
          _urlController.text = url;
          ApiService.customBaseUrl = url;
          _checkHealth();
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFF0F5FF) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            color: isSelected ? const Color(0xFF1A4DBF) : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          children: const [
            Text(
              'Settings & Diagnostics',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            Text(
              'Server connection • Inspector identity • Engine health',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w400,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section: Backend Service Endpoint
            const Text(
              'BACKEND SERVICE ENDPOINT',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: AppColors.textSecondary,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),

            // URL input with inline Save button
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _urlController,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                      decoration: const InputDecoration(
                        hintText: 'http://127.0.0.1:8000',
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: SizedBox(
                      width: 72,
                      height: 34,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                        onPressed: () {
                          ApiService.customBaseUrl = _urlController.text.trim();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Updated Base URL: ${ApiService.baseUrl}')),
                          );
                          _checkHealth();
                        },
                        child: const Text(
                          'Save',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),

            // Preset chips
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                _presetChip(
                  label: '⚡ Auto-Detect',
                  url: '',
                  isAutoDetect: true,
                ),
                _presetChip(
                  label: '🔌 USB Local',
                  url: 'http://127.0.0.1:8000',
                ),
                _presetChip(
                  label: '📱 Emulator',
                  url: 'http://10.0.2.2:8000',
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Section: System Readiness
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'SYSTEM READINESS (/healthz)',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textSecondary,
                    letterSpacing: 0.5,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 18),
                  onPressed: () => _checkHealth(),
                  tooltip: 'Refresh Health Check',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
            const SizedBox(height: 8),

            PsCard(
              padding: const EdgeInsets.all(14),
              child: _isLoadingHealth
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: CircularProgressIndicator(color: AppColors.primary),
                      ),
                    )
                  : _healthError != null
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: const [
                                Icon(Icons.error_outline, color: AppColors.violation, size: 18),
                                SizedBox(width: 8),
                                Text(
                                  'Service Unreachable',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.violation,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              _healthError!,
                              style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                            ),
                            const SizedBox(height: 12),
                            SizedBox(
                              height: 36,
                              child: OutlinedButton(
                                onPressed: () => _checkHealth(),
                                child: const Text('Retry Connection', style: TextStyle(fontSize: 12)),
                              ),
                            ),
                          ],
                        )
                      : Column(
                          children: [
                            _healthItem(
                              'Supabase Postgres Database',
                              _healthData?['database']?['connected'] == true,
                              _healthData?['database']?['connected'] == true
                                  ? 'Connected via asyncpg pool'
                                  : 'Offline / Mock mode active',
                            ),
                            const Divider(height: 1),
                            _healthItem(
                              'Supabase Private Storage',
                              _healthData?['storage']?['configured'] == true,
                              _healthData?['storage']?['configured'] == true
                                  ? 'Evidence bucket configured'
                                  : 'Using local scratch fallback',
                            ),
                            const Divider(height: 1),
                            _healthItem(
                              'Google Cloud Vision OCR',
                              _healthData?['cloud_vision']?['configured'] == true,
                              _healthData?['cloud_vision']?['configured'] == true
                                  ? 'ADC credentials active (primary)'
                                  : 'Fallback to PaddleOCR active (ADR-0004)',
                            ),
                            const Divider(height: 1),
                            _healthItem(
                              'PaddleOCR Local Fallback',
                              _healthData?['paddleocr']?['importable'] == true,
                              _healthData?['paddleocr']?['importable'] == true
                                  ? 'Local inference ready'
                                  : 'Adapter present',
                            ),
                            const Divider(height: 1),
                            _healthItem(
                              'Ollama Qwen2.5-VL (GPU)',
                              _healthData?['ollama']?['reachable'] == true,
                              _healthData?['ollama']?['reachable'] == true
                                  ? 'Model ${_healthData?['ollama']?['model']} available'
                                  : 'Ollama daemon offline on localhost:11434',
                            ),
                          ],
                        ),
            ),
            const SizedBox(height: 20),

            // Section: Legal Metrology Engine
            const Text(
              'LEGAL METROLOGY ENGINE',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: AppColors.textSecondary,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF5F7FA),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    '• Spec: LMPC Rules, 2011',
                    style: TextStyle(fontSize: 12, color: Color(0xFF4D5973)),
                  ),
                  SizedBox(height: 4),
                  Text(
                    '• Baseline: G.S.R. 779(E) (2021) & 418(E) (2026)',
                    style: TextStyle(fontSize: 12, color: Color(0xFF4D5973)),
                  ),
                  SizedBox(height: 4),
                  Text(
                    '• Active Rules: 23 statutory provisions',
                    style: TextStyle(fontSize: 12, color: Color(0xFF4D5973)),
                  ),
                  SizedBox(height: 4),
                  Text(
                    '• Absence Gate: ADR-0005 enforced',
                    style: TextStyle(fontSize: 12, color: Color(0xFF4D5973)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Section: Inspector Identity
            PsCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
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
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Inspector: LMO-0042 (Sharma)',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: () {},
                    child: const Text(
                      'Edit',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppColors.primary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
