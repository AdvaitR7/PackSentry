import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class ApiService {
  static String customBaseUrl = '';

  /// Host that the Android emulator maps to the developer machine's loopback.
  static const String emulatorBaseUrl = 'http://10.0.2.2:8000';

  /// Loopback on the device itself — reachable from a USB-attached phone once
  /// `adb reverse tcp:8000 tcp:8000` is running, and from desktop/web builds.
  static const String loopbackBaseUrl = 'http://127.0.0.1:8000';

  static Future<String>? _resolution;

  static String get baseUrl {
    if (customBaseUrl.isNotEmpty) {
      return customBaseUrl;
    }
    if (!kIsWeb && Platform.isAndroid) {
      return emulatorBaseUrl;
    }
    return loopbackBaseUrl;
  }

  /// Candidate hosts probed by [resolveBaseUrl], in priority order.
  static List<String> get candidateBaseUrls {
    if (!kIsWeb && Platform.isAndroid) {
      return const [emulatorBaseUrl, loopbackBaseUrl];
    }
    return const [loopbackBaseUrl];
  }

  /// Picks the first candidate host whose `/healthz` answers, and pins it as
  /// [customBaseUrl]. This is what lets the same build work on an emulator
  /// (10.0.2.2) and on a USB-attached phone using `adb reverse` (127.0.0.1)
  /// without the inspector editing anything.
  ///
  /// Runs at most once per app session unless [force] is set. Falls back to
  /// [baseUrl] when nothing responds, so callers still surface a real error.
  static Future<String> resolveBaseUrl({bool force = false}) {
    if (force) {
      _resolution = null;
      customBaseUrl = '';
    } else if (customBaseUrl.isNotEmpty) {
      return Future.value(customBaseUrl);
    }
    return _resolution ??= _probeCandidates();
  }

  static Future<String> _probeCandidates() async {
    if (customBaseUrl.isNotEmpty) return customBaseUrl;

    for (final candidate in candidateBaseUrls) {
      try {
        final response = await http
            .get(Uri.parse('$candidate/healthz'))
            .timeout(const Duration(seconds: 2));
        if (response.statusCode == 200) {
          customBaseUrl = candidate;
          return candidate;
        }
      } catch (_) {
        // Candidate unreachable — try the next one.
      }
    }
    // Don't pin a failed resolution so a backend started after app launch can
    // still be discovered on the next call.
    _resolution = null;
    return baseUrl;
  }

  /// Initiates a statutory packaging compliance inspection (POST /v1/inspections).
  /// Sends multipart request with context JSON, required PDP and BACK panels, and
  /// up to four optional additional panels sent as repeated SIDE parts.
  Future<Map<String, dynamic>> createInspection({
    required CaptureContext context,
    required Uint8List pdpBytes,
    String pdpName = 'pdp.jpg',
    required Uint8List backBytes,
    String backName = 'back.jpg',
    List<Uint8List> sideImages = const [],
    String? idempotencyKey,
  }) async {
    final resolvedBaseUrl = await resolveBaseUrl();
    final uri = Uri.parse('$resolvedBaseUrl/v1/inspections');
    final request = http.MultipartRequest('POST', uri);

    if (idempotencyKey != null && idempotencyKey.isNotEmpty) {
      request.headers['Idempotency-Key'] = idempotencyKey;
    }

    // Add JSON context part
    request.fields['context'] = jsonEncode(context.toJson());

    // Add required PDP panel
    request.files.add(
      http.MultipartFile.fromBytes(
        'PDP',
        pdpBytes,
        filename: pdpName,
      ),
    );

    // Add required BACK panel
    request.files.add(
      http.MultipartFile.fromBytes(
        'BACK',
        backBytes,
        filename: backName,
      ),
    );

    // Add each additional panel as a repeated SIDE part. The shared field name
    // is what lets the backend collect them into one ordered list.
    for (var i = 0; i < sideImages.length; i++) {
      final bytes = sideImages[i];
      if (bytes.isEmpty) continue;
      request.files.add(
        http.MultipartFile.fromBytes(
          'SIDE',
          bytes,
          filename: 'side_${i + 1}.jpg',
        ),
      );
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 202 || response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception(
        'Failed to initiate inspection: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Polls inspection state or retrieves finished inspection (GET /v1/inspections/{id}).
  /// Returns dynamic: either Map for in-flight status or InspectionResponse for COMPLETE.
  Future<dynamic> getInspection(String inspectionId) async {
    final resolvedBaseUrl = await resolveBaseUrl();
    final uri = Uri.parse('$resolvedBaseUrl/v1/inspections/$inspectionId');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final status = data['status'];
      if (status == 'COMPLETE') {
        return InspectionResponse.fromJson(data);
      }
      // In-flight or failed status map
      return data;
    } else if (response.statusCode == 404) {
      throw Exception('Inspection $inspectionId not found.');
    } else {
      throw Exception(
        'Failed to query inspection: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Lists past inspections (GET /v1/inspections).
  Future<List<dynamic>> listInspections({
    int limit = 20,
    DateTime? cursor,
    String? status,
  }) async {
    final resolvedBaseUrl = await resolveBaseUrl();
    final queryParams = <String, String>{'limit': limit.toString()};
    if (cursor != null) {
      queryParams['cursor'] = cursor.toIso8601String();
    }
    if (status != null) {
      queryParams['status'] = status;
    }

    final uri = Uri.parse('$resolvedBaseUrl/v1/inspections').replace(
      queryParameters: queryParams,
    );
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception(
        'Failed to list inspections: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Queries active statutory rules catalog (GET /v1/rules?as_of=).
  Future<List<dynamic>> getRules({DateTime? asOf}) async {
    final resolvedBaseUrl = await resolveBaseUrl();
    final queryParams = <String, String>{};
    if (asOf != null) {
      queryParams['as_of'] = asOf.toIso8601String().split('T').first;
    }

    final uri = Uri.parse('$resolvedBaseUrl/v1/rules').replace(
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception(
        'Failed to fetch rules catalog: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Queries server health and readiness (GET /healthz).
  Future<Map<String, dynamic>> getHealthz({bool forceResolve = false}) async {
    final resolvedBaseUrl = await resolveBaseUrl(force: forceResolve);
    final uri = Uri.parse('$resolvedBaseUrl/healthz');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception(
        'Failed healthz check: ${response.statusCode} - ${response.body}',
      );
    }
  }
}
