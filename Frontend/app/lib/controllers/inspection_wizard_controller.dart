import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../models/models.dart';

class InspectionWizardController extends ChangeNotifier {
  PackageType _packageType = PackageType.RETAIL;
  CommodityCategory _commodityCategory = CommodityCategory.GENERAL;
  ImportStatus _importStatus = ImportStatus.DOMESTIC;
  bool _allPanelsCaptured = true;
  String? _fourthScheduleKey;
  String _inspectorId = 'insp_officer_01';

  /// Additional SIDE panels accepted beyond PDP and BACK. Mirrors
  /// `MAX_SIDE_PANELS` in Backend/app/panels.py — the backend rejects more.
  static const int maxSideImages = 4;

  Uint8List? _pdpBytes;
  Uint8List? _backBytes;
  final List<Uint8List> _sideImages = [];

  int _currentStep = 0;

  // Getters
  PackageType get packageType => _packageType;
  CommodityCategory get commodityCategory => _commodityCategory;
  ImportStatus get importStatus => _importStatus;
  bool get allPanelsCaptured => _allPanelsCaptured;
  String? get fourthScheduleKey => _fourthScheduleKey;
  String get inspectorId => _inspectorId;

  Uint8List? get pdpBytes => _pdpBytes;
  Uint8List? get backBytes => _backBytes;
  List<Uint8List> get sideImages => List.unmodifiable(_sideImages);

  int get currentStep => _currentStep;

  // Panel check
  bool get hasPdp => _pdpBytes != null && _pdpBytes!.isNotEmpty;
  bool get hasBack => _backBytes != null && _backBytes!.isNotEmpty;
  bool get hasSide => _sideImages.isNotEmpty;
  bool get canAddSideImage => _sideImages.length < maxSideImages;

  bool get canProceedToCapture => true;
  bool get canProceedToReview => hasPdp && hasBack;
  bool get canSubmit => hasPdp && hasBack;

  // Mutators
  void setPackageType(PackageType type) {
    _packageType = type;
    notifyListeners();
  }

  void setCommodityCategory(CommodityCategory category) {
    _commodityCategory = category;
    notifyListeners();
  }

  void setImportStatus(ImportStatus status) {
    _importStatus = status;
    notifyListeners();
  }

  void setAllPanelsCaptured(bool value) {
    _allPanelsCaptured = value;
    notifyListeners();
  }

  void setFourthScheduleKey(String? key) {
    _fourthScheduleKey = key;
    notifyListeners();
  }

  void setInspectorId(String id) {
    _inspectorId = id;
    notifyListeners();
  }

  void setPdpBytes(Uint8List? bytes) {
    _pdpBytes = bytes;
    notifyListeners();
  }

  void setBackBytes(Uint8List? bytes) {
    _backBytes = bytes;
    notifyListeners();
  }

  /// Appends an additional panel. Silently ignores empty bytes and anything
  /// beyond [maxSideImages], which the backend would reject with a 422.
  void addSideImage(Uint8List bytes) {
    if (bytes.isEmpty || !canAddSideImage) return;
    _sideImages.add(bytes);
    notifyListeners();
  }

  void replaceSideImageAt(int index, Uint8List bytes) {
    if (index < 0 || index >= _sideImages.length || bytes.isEmpty) return;
    _sideImages[index] = bytes;
    notifyListeners();
  }

  void removeSideImageAt(int index) {
    if (index < 0 || index >= _sideImages.length) return;
    _sideImages.removeAt(index);
    notifyListeners();
  }

  void setStep(int step) {
    _currentStep = step;
    notifyListeners();
  }

  Future<void> loadSampleImages() async {
    try {
      final frontData = await rootBundle.load('assets/images/front.png');
      final backData = await rootBundle.load('assets/images/back.png');
      final sideData = await rootBundle.load('assets/images/side.png');

      _pdpBytes = frontData.buffer.asUint8List();
      _backBytes = backData.buffer.asUint8List();
      _sideImages
        ..clear()
        ..add(sideData.buffer.asUint8List());
      notifyListeners();
    } catch (e) {
      debugPrint('Could not preload sample images: $e');
    }
  }

  void reset() {
    _pdpBytes = null;
    _backBytes = null;
    _sideImages.clear();
    _currentStep = 0;
    _allPanelsCaptured = true;
    notifyListeners();
  }

  CaptureContext buildCaptureContext() {
    return CaptureContext(
      packageType: _packageType,
      commodityCategory: _commodityCategory,
      importStatus: _importStatus,
      fourthScheduleKey: _fourthScheduleKey,
      packageCapacityLe5Cm3: false,
      allPanelsCaptured: _allPanelsCaptured,
      inspectorId: _inspectorId,
      capturedAt: DateTime.now(),
    );
  }
}
