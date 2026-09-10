import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app/controllers/inspection_wizard_controller.dart';
import 'package:app/screens/inspect/inspect_home.dart';

void main() {
  testWidgets(
    'InspectHomeScreen renders dynamic dashboard metrics and Start Inspection CTA',
    (WidgetTester tester) async {
      final controller = InspectionWizardController();

      await tester.pumpWidget(
        MaterialApp(
          home: ChangeNotifierProvider<InspectionWizardController>.value(
            value: controller,
            child: const InspectHomeScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify header and CTA
      expect(find.text('New Package Inspection'), findsOneWidget);
      expect(find.text('Start Inspection →'), findsOneWidget);

      // Verify dynamic metrics cards exist
      expect(find.text('Completed Today'), findsOneWidget);
      expect(find.text('Violations Flagged'), findsOneWidget);

      // Verify recent inspections section
      expect(find.text('Recent Inspections'), findsOneWidget);
    },
  );
}
