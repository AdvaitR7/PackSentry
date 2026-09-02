enum ComplianceStatus {
  compliant,
  violation,
  manualReview,
}

class ScanField {
  final String name;
  final String value;
  final double confidence;

  ScanField({
    required this.name,
    required this.value,
    required this.confidence,
  });
}

class ScanViolation {
  final String fieldName;
  final String detectedValue;
  final String requiredValue;
  final String description;

  ScanViolation({
    required this.fieldName,
    required this.detectedValue,
    required this.requiredValue,
    required this.description,
  });
}

class ScanResult {
  final String productName;
  final ComplianceStatus status;
  final List<ScanField> fields;
  final List<ScanViolation> violations;
  final DateTime date;

  ScanResult({
    required this.productName,
    required this.status,
    required this.fields,
    required this.violations,
    required this.date,
  });
}