import 'package:flutter/material.dart';
import 'app_shell.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const PackSentryApp());
}

class PackSentryApp extends StatelessWidget {
  const PackSentryApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'PackSentry — Legal Metrology Scanner',
      theme: AppTheme.lightTheme,
      home: const AppShell(),
    );
  }
}
