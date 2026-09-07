import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'controllers/inspection_wizard_controller.dart';
import 'screens/history_screen.dart';
import 'screens/inspect/details_step.dart';
import 'screens/rules_screen.dart';
import 'screens/settings_screen.dart';

/// Four-tab root shell per ADR-0014: Inspect, History, Rules, Settings.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;

  final List<Widget> _tabs = const [
    _InspectTabHost(),
    HistoryScreen(),
    RulesScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _tabs,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.document_scanner_outlined),
            selectedIcon: Icon(Icons.document_scanner),
            label: 'Inspect',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history),
            label: 'History',
          ),
          NavigationDestination(
            icon: Icon(Icons.gavel_outlined),
            selectedIcon: Icon(Icons.gavel),
            label: 'Rules',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

/// Hosts the Inspect tab's own wizard controller, isolated per-tab so
/// switching away and back doesn't lose History/Rules/Settings state.
class _InspectTabHost extends StatelessWidget {
  const _InspectTabHost();

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => InspectionWizardController(),
      child: const DetailsStep(),
    );
  }
}
