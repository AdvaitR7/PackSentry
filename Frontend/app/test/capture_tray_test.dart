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

    // All three panels start empty.
    expect(find.text('Tap to photograph panel'), findsNWidgets(3));
    expect(find.text('Retake Photo'), findsNothing);

    // Simulate the camera screen returning bytes for the PDP panel.
    controller.setPdpBytes(_tinyPng);
    await tester.pumpAndSettle();

    expect(find.text('Tap to photograph panel'), findsNWidgets(2));
    expect(find.byType(Image), findsOneWidget);
    expect(find.text('Remove'), findsOneWidget);
    expect(find.text('Retake Photo'), findsOneWidget);
  });

  testWidgets('Review & Submit unlocks only once PDP and BACK are captured',
      (tester) async {
    final controller = InspectionWizardController();

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();

    ElevatedButton reviewButton() => tester.widget<ElevatedButton>(
          find.widgetWithText(ElevatedButton, 'Review & Submit Inspection'),
        );

    expect(reviewButton().onPressed, isNull);
    expect(find.text('Capture both PDP and Back panel images to continue.'),
        findsOneWidget);

    controller.setPdpBytes(_tinyPng);
    await tester.pumpAndSettle();
    expect(reviewButton().onPressed, isNull,
        reason: 'BACK panel is still missing');

    controller.setBackBytes(_tinyPng);
    await tester.pumpAndSettle();
    expect(reviewButton().onPressed, isNotNull);
    expect(find.text('Capture both PDP and Back panel images to continue.'),
        findsNothing);
  });

  testWidgets('Removing a captured panel returns the card to its empty state',
      (tester) async {
    final controller = InspectionWizardController();
    controller.setPdpBytes(_tinyPng);

    await tester.pumpWidget(_wrap(controller));
    await tester.pumpAndSettle();
    expect(find.text('Remove'), findsOneWidget);

    await tester.tap(find.text('Remove'));
    await tester.pumpAndSettle();

    expect(controller.pdpBytes, isNull);
    expect(find.text('Tap to photograph panel'), findsNWidgets(3));
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
