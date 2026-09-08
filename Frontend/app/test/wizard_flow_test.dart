import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app/controllers/inspection_wizard_controller.dart';
import 'package:app/screens/inspect/details_step.dart';

void main() {
  testWidgets('Wizard flow: All Images Captured toggle is on CaptureStep after image panels', (WidgetTester tester) async {
    final controller = InspectionWizardController();

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<InspectionWizardController>.value(
          value: controller,
          child: const DetailsStep(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Verify DetailsStep does NOT have the toggle
    expect(find.text('Package Context'), findsOneWidget);
    expect(find.text('All Images / Panels Captured'), findsNothing);
    expect(find.text('All Packaging Panels Captured'), findsNothing);

    // Scroll to and tap "Proceed to Image Capture"
    final proceedButton = find.text('Proceed to Image Capture');
    await tester.ensureVisible(proceedButton);
    await tester.pumpAndSettle();
    await tester.tap(proceedButton);
    await tester.pumpAndSettle();

    // Verify CaptureStep is displayed
    expect(find.text('New Inspection — 2/3 Capture'), findsOneWidget);
    expect(find.text('Principal Display Panel (PDP) *'), findsOneWidget);
    expect(find.text('Back Panel (BACK) *'), findsOneWidget);
    expect(find.text('Add Additional Panel (Optional)'), findsOneWidget);

    // Verify that "All Images / Panels Captured" toggle is now present on CaptureStep
    expect(find.text('All Images / Panels Captured'), findsOneWidget);
    expect(find.byType(SwitchListTile), findsOneWidget);

    // Verify default value is true
    expect(controller.allPanelsCaptured, isTrue);

    // Toggle switch off
    final switchTile = find.byType(SwitchListTile);
    await tester.ensureVisible(switchTile);
    await tester.pumpAndSettle();
    await tester.tap(switchTile);
    await tester.pumpAndSettle();
    expect(controller.allPanelsCaptured, isFalse);
  });
}
