import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/models/models.dart';

void main() {
  group('InspectionResponse Model Deserialization (ADR-0003)', () {
    test('deserializes a complete InspectionResponse payload cleanly', () {
      const sampleJson = '''
      {
        "inspection_id": "insp_01H8XQ",
        "status": "COMPLETE",
        "created_at": "2026-09-04T11:22:03+05:30",
        "completed_at": "2026-09-04T11:22:11+05:30",
        "overall": "NON_COMPLIANT",
        "overall_ui_bucket": "POTENTIAL_NON_COMPLIANCE",
        "summary": {
          "compliant": 7,
          "potential_non_compliance": 2,
          "manual_review": 1,
          "insufficient_evidence": 0,
          "not_applicable": 5,
          "not_evaluated": 2
        },
        "context": {
          "package_type": "RETAIL",
          "package_type_source": "INSPECTOR",
          "commodity_category": "TEXTILE",
          "commodity_category_source": "INSPECTOR",
          "commodity_category_confidence": 1.0,
          "fourth_schedule_key": "READY_MADE_GARMENTS",
          "import_status": "DOMESTIC",
          "net_quantity": { "magnitude": 1200.0, "unit_canonical": "g", "dimension": "MASS" },
          "net_quantity_in_base_units": { "value": 1.2, "unit": "kg" },
          "is_food_article": false,
          "is_cosmetic": false,
          "is_alcoholic": false,
          "is_certified_seed": false,
          "package_capacity_le_5cm3": false,
          "declaration_required_by_other_law": false,
          "scan_date": "2026-09-04",
          "ruleset_as_of": "2026-09-04",
          "ai_suggestions": []
        },
        "images": [
          {
            "image_id": "img_01H8X",
            "role": "PDP",
            "original_url": "https://storage.example.com/original/img_01H8X.jpg",
            "analysis_url": "https://storage.example.com/analysis/img_01H8X.jpg",
            "original_width": 3024,
            "original_height": 4032
          }
        ],
        "declarations": [
          {
            "field": "NET_QUANTITY",
            "status": "FOUND",
            "raw_value": "1200 gms",
            "parsed": {
              "kind": "QUANTITY",
              "magnitude": 1200.0,
              "unit_raw": "gms",
              "unit_canonical": "g",
              "dimension": "MASS",
              "is_si": true,
              "symbol_is_prescribed": false,
              "qualifier": null,
              "multi_unit": null
            },
            "evidence": [
              {
                "image_id": "img_01H8X",
                "line_id": "img_01H8X:l007",
                "polygon_normalized": [[0.257, 0.412], [0.583, 0.411], [0.585, 0.432], [0.259, 0.433]],
                "raw_text": "Net Qty.: 1200 gms"
              }
            ],
            "ocr_confidence": 0.943,
            "extraction_confidence": 0.97,
            "method": "ALIAS_ANCHOR"
          }
        ],
        "rule_results": [
          {
            "rule_id": "R13_UNIT_THRESHOLD",
            "provision": "Rule 13(2), 13(3)",
            "title": "Correct unit for declared magnitude",
            "verdict": "NON_COMPLIANT",
            "ui_bucket": "POTENTIAL_NON_COMPLIANCE",
            "reason_code": "MAGNITUDE_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE",
            "message": "Net quantity is declared as 1200 g.",
            "observed": "1200 gms",
            "expected": "1.2 kg",
            "evidence": [
              {
                "image_id": "img_01H8X",
                "line_id": "img_01H8X:l007",
                "polygon_normalized": [[0.257, 0.412], [0.583, 0.411], [0.585, 0.432], [0.259, 0.433]],
                "raw_text": "Net Qty.: 1200 gms"
              }
            ],
            "confidence": { "ocr": 0.943, "extraction": 0.97, "rule": 1.0 },
            "applicability": { "status": "APPLICABLE", "gate": null, "reason_code": null, "message": null },
            "citation": {
              "provision": "Rule 13(2), 13(3)",
              "instrument": "Legal Metrology (Packaged Commodities) Rules, 2011",
              "gsr": "G.S.R. 202(E)",
              "gazette_date": "2011-03-07",
              "source_url": "https://egazette.gov.in/sample"
            }
          }
        ],
        "configured_rule_ids": ["R13_UNIT_THRESHOLD", "R06_MRP_DECLARATION"],
        "evaluated_rule_ids": ["R13_UNIT_THRESHOLD"],
        "excluded_rule_ids": [ { "rule_id": "R07_FONT_HEIGHT", "reason_code": "ABSOLUTE_SCALE_UNAVAILABLE" } ],
        "engine": {
          "rule_engine_version": "2026.09.01",
          "ruleset_as_of": "2026-09-04",
          "ocr_engine": "paddleocr 2.8.0",
          "alias_table_version": "2026.09.01"
        }
      }
      ''';

      final Map<String, dynamic> data = jsonDecode(sampleJson) as Map<String, dynamic>;
      final response = InspectionResponse.fromJson(data);

      expect(response.inspectionId, equals('insp_01H8XQ'));
      expect(response.status, equals(InspectionStatus.COMPLETE));
      expect(response.overall, equals(InternalVerdict.NON_COMPLIANT));
      expect(response.overallUiBucket, equals(UiBucket.POTENTIAL_NON_COMPLIANCE));
      expect(response.summary.compliant, equals(7));
      expect(response.summary.potentialNonCompliance, equals(2));
      expect(response.context.packageType, equals(PackageType.RETAIL));
      expect(response.context.commodityCategory, equals(CommodityCategory.TEXTILE));
      expect(response.images?.length, equals(1));
      expect(response.images?.first.role, equals(PanelRole.PDP));
      expect(response.declarations?.length, equals(1));
      expect(response.declarations?.first.field, equals(Field.NET_QUANTITY));
      expect(response.declarations?.first.parsed?.magnitude, equals(1200.0));
      expect(response.ruleResults?.length, equals(1));
      expect(response.ruleResults?.first.ruleId, equals('R13_UNIT_THRESHOLD'));
      expect(response.ruleResults?.first.verdict, equals(InternalVerdict.NON_COMPLIANT));
      expect(response.ruleResults?.first.citation.provision, equals('Rule 13(2), 13(3)'));
      expect(response.ruleResults?.first.citation.gsr, equals('G.S.R. 202(E)'));
      expect(response.engine.ocrEngine, equals('paddleocr 2.8.0'));
    });
  });
}
