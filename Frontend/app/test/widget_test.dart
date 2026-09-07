import 'package:flutter_test/flutter_test.dart';

import 'package:app/main.dart';

void main() {
  testWidgets('LegalMetrologyApp smoke test renders home screen', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const LegalMetrologyApp());
    await tester.pumpAndSettle();

    // Verify that the Legal Metrology home screen title is rendered.
    expect(find.text('Legal Metrology'), findsWidgets);
  });
}
