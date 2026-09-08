import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app/controllers/inspection_wizard_controller.dart';
import 'package:app/screens/inspect/capture_step.dart';
import 'package:app/services/api_service.dart';

/// Minimal valid 1x1 PNG so Image.memory can actually decode in tests.
final Uint8List _tinyPng = Uint8List.fromList(<int>[
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, //
  0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
  0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
  0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
  0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
  0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
  0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
  0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
  0x42, 0x60, 0x82,
]);

Widget _wrap(InspectionWizardController controller) {
  return MaterialApp(
    home: ChangeNotifierProvider<InspectionWizardController>.value(
      value: controller,
      child: const CaptureStep(),
    ),
  );
}

void main() {
  testWidgets('Captured panel bytes render in the image tray', (tester) async {
    final controller = InspectionWizardController();

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();

    // The two required panels start empty; additional panels appear only once added.
    expect(find.text('Tap to photograph panel'), findsNWidgets(2));
    expect(find.text('Retake Photo'), findsNothing);

    // Simulate the camera screen returning bytes for the PDP panel.
    controller.setPdpBytes(_tinyPng);
    await tester.pumpAndSettle();

    expect(find.text('Tap to photograph panel'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);
    expect(find.text('Remove'), findsOneWidget);
    expect(find.text('Retake Photo'), findsOneWidget);
  });

  testWidgets('Review & Submit unlocks only once PDP and BACK are captured', (
    tester,
  ) async {
    final controller = InspectionWizardController();

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();

    ElevatedButton reviewButton() => tester.widget<ElevatedButton>(
      find.widgetWithText(ElevatedButton, 'Review & Submit Inspection'),
    );

    expect(reviewButton().onPressed, isNull);
    expect(
      find.text('Capture both PDP and Back panel images to continue.'),
      findsOneWidget,
    );

    controller.setPdpBytes(_tinyPng);
    await tester.pumpAndSettle();
    expect(
      reviewButton().onPressed,
      isNull,
      reason: 'BACK panel is still missing',
    );

    controller.setBackBytes(_tinyPng);
    await tester.pumpAndSettle();
    expect(reviewButton().onPressed, isNotNull);
    expect(
      find.text('Capture both PDP and Back panel images to continue.'),
      findsNothing,
    );
  });

  testWidgets('Removing a captured panel returns the card to its empty state', (
    tester,
  ) async {
    final controller = InspectionWizardController();
    controller.setPdpBytes(_tinyPng);

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();
    expect(find.text('Remove'), findsOneWidget);

    await tester.tap(find.text('Remove'));
    await tester.pumpAndSettle();

    expect(controller.pdpBytes, isNull);
    expect(find.text('Tap to photograph panel'), findsNWidgets(2));
  });

  testWidgets('Additional panels can be added up to the cap, then the button hides', (
    tester,
  ) async {
    final controller = InspectionWizardController();

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();

    // No additional panel cards exist until one is added.
    expect(find.text('Additional Panel 1 (SIDE) (Optional)'), findsNothing);
    expect(find.text('Add Additional Panel (Optional)'), findsOneWidget);

    for (var i = 1; i <= InspectionWizardController.maxSideImages; i++) {
      controller.addSideImage(_tinyPng);
      await tester.pumpAndSettle();
      expect(find.text('Additional Panel $i (SIDE) (Optional)'), findsOneWidget);
    }

    // At the cap the add button is replaced by an explanatory line.
    expect(controller.canAddSideImage, isFalse);
    expect(find.textContaining('Add Another Panel'), findsNothing);
    expect(
      find.text('Maximum of ${InspectionWizardController.maxSideImages} additional panels attached.'),
      findsOneWidget,
    );

    // The cap is enforced in the controller, not just the UI.
    controller.addSideImage(_tinyPng);
    expect(controller.sideImages.length, InspectionWizardController.maxSideImages);

    // Removing one frees a slot and renumbers the remaining cards.
    controller.removeSideImageAt(0);
    await tester.pumpAndSettle();
    expect(controller.sideImages.length, InspectionWizardController.maxSideImages - 1);
    expect(
      find.text('Additional Panel ${InspectionWizardController.maxSideImages} (SIDE) (Optional)'),
      findsNothing,
    );
  });

  testWidgets('Additional panels do not gate Review & Submit', (tester) async {
    final controller = InspectionWizardController();
    controller.setPdpBytes(_tinyPng);
    controller.setBackBytes(_tinyPng);

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();

    // PDP + BACK alone still unlock submission; extra panels stay optional.
    expect(controller.sideImages, isEmpty);
    expect(
      tester
          .widget<ElevatedButton>(
            find.widgetWithText(ElevatedButton, 'Review & Submit Inspection'),
          )
          .onPressed,
      isNotNull,
    );
  });

  test('Built capture context sends required boolean fields, not null', () {
    final context = InspectionWizardController().buildCaptureContext().toJson();

    expect(context['package_capacity_le_5cm3'], isFalse);
    expect(context['all_panels_captured'], isTrue);
  });

  test('Base URL candidates cover emulator and USB-reverse loopback', () {
    ApiService.customBaseUrl = '';
    addTearDown(() => ApiService.customBaseUrl = '');

    // On the Flutter test VM (non-Android host) loopback is the only candidate.
    expect(ApiService.candidateBaseUrls, contains(ApiService.loopbackBaseUrl));
    expect(ApiService.baseUrl, ApiService.loopbackBaseUrl);

    // An operator override always wins over platform defaults.
    ApiService.customBaseUrl = 'http://192.168.1.42:8000';
    expect(ApiService.baseUrl, 'http://192.168.1.42:8000');
  });
}
