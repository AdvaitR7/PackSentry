import 'package:flutter_test/flutter_test.dart';
import 'package:app/main.dart';

void main() {
  testWidgets('PackSentryApp smoke test renders app shell', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const PackSentryApp());
    await tester.pumpAndSettle();

    // Verify that the AppShell renders the Inspect tab and title.
    expect(find.text('New Inspection — 1/3 Details'), findsOneWidget);
    expect(find.text('Package Context'), findsOneWidget);
  });
}
