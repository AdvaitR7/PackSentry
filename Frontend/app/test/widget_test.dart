import 'package:flutter_test/flutter_test.dart';
import 'package:app/main.dart';

void main() {
  testWidgets('PackSentryApp smoke test renders app shell', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const PackSentryApp());
    await tester.pumpAndSettle();

    // Verify that the AppShell renders the Inspect home tab (Figma 01).
    expect(find.text('New Package Inspection'), findsOneWidget);
    expect(find.text('Start Inspection →'), findsOneWidget);
  });
}
