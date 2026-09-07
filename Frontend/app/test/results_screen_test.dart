import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/models/models.dart';
import 'package:app/screens/results_screen.dart';

void main() {
  testWidgets('ResultsScreen renders real InspectionResponse with non-compliance and citation', (WidgetTester tester) async {
    const sampleJson = '''
    {
      "inspection_id": "insp_01H8XQ",
      "status": "COMPLETE",
      "created_at": "2026-09-04T11:22:03+05:30",
      "completed_at": "2026-09-04T11:22:11+05:30",
      "overall": "NON_COMPLIANT",
      "overall_ui_bucket": "POTENTIAL_NON_COMPLIANCE",
      "summary": {
        "compliant": 8,
        "potential_non_compliance": 2,
        "manual_review": 1,
        "insufficient_evidence": 0,
        "not_applicable": 4,
        "not_evaluated": 3
      },
      "context": {
        "package_type": "RETAIL",
        "commodity_category": "TEXTILE",
        "import_status": "DOMESTIC",
        "scan_date": "2026-09-04",
        "ruleset_as_of": "2026-09-04"
      },
      "images": [],
      "declarations": [],
      "rule_results": [
        {
          "rule_id": "R13_UNIT_THRESHOLD",
          "provision": "Rule 13(2), 13(3)",
          "title": "Correct unit for declared magnitude",
          "verdict": "NON_COMPLIANT",
          "ui_bucket": "POTENTIAL_NON_COMPLIANCE",
          "reason_code": "MAGNITUDE_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE",
          "message": "Net quantity is declared as 1200 g in sub-multiple unit instead of kg.",
          "observed": "1200 gms",
          "expected": "1.2 kg",
          "evidence": [],
          "confidence": { "ocr": 0.943, "extraction": 0.97, "rule": 1.0 },
          "applicability": { "status": "APPLICABLE" },
          "citation": {
            "provision": "Rule 13(2), 13(3)",
            "instrument": "Legal Metrology (Packaged Commodities) Rules, 2011",
            "gsr": "G.S.R. 202(E)",
            "gazette_date": "2011-03-07",
            "source_url": "https://egazette.gov.in/sample"
          }
        }
      ],
      "configured_rule_ids": ["R13_UNIT_THRESHOLD"],
      "evaluated_rule_ids": ["R13_UNIT_THRESHOLD"],
      "excluded_rule_ids": [],
      "engine": {
        "rule_engine_version": "2026.09.01",
        "ruleset_as_of": "2026-09-04",
        "ocr_engine": "paddleocr 2.8.0",
        "alias_table_version": "2026.09.01"
      }
    }
    ''';

    final data = jsonDecode(sampleJson) as Map<String, dynamic>;
    final response = InspectionResponse.fromJson(data);

    await tester.pumpWidget(
      MaterialApp(
        home: ResultsScreen(response: response),
      ),
    );
    await tester.pumpAndSettle();

    // Verify overall verdict banner text
    expect(find.text('POTENTIAL NON COMPLIANCE'), findsAtLeastNWidgets(1));
    expect(find.text('Inspection ID: insp_01H8XQ'), findsOneWidget);

    // Verify summary count chips
    expect(find.text('8'), findsOneWidget); // Passed
    expect(find.text('2'), findsOneWidget); // Violations
    expect(find.text('1'), findsOneWidget); // Review

    // Verify rule finding tile
    expect(find.text('Rule 13(2), 13(3)'), findsOneWidget);
    expect(find.text('Correct unit for declared magnitude'), findsOneWidget);

    // Verify engine metadata
    expect(find.text('Audit & Engine Provenance'), findsOneWidget);
    expect(find.textContaining('paddleocr 2.8.0'), findsOneWidget);
  });
}
