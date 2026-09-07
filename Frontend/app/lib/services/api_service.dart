import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class ApiService {
  static String customBaseUrl = '';

  static String get baseUrl {
    if (customBaseUrl.isNotEmpty) {
      return customBaseUrl;
    }
    if (kIsWeb) {
      return 'http://127.0.0.1:8000';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  /// Initiates a statutory packaging compliance inspection (POST /v1/inspections).
  /// Sends multipart request with context JSON, required PDP and BACK panels, and optional SIDE panel.
  Future<Map<String, dynamic>> createInspection({
    required CaptureContext context,
    required Uint8List pdpBytes,
    String pdpName = 'pdp.jpg',
    required Uint8List backBytes,
    String backName = 'back.jpg',
    Uint8List? sideBytes,
    String sideName = 'side.jpg',
    String? idempotencyKey,
  }) async {
    final uri = Uri.parse('$baseUrl/v1/inspections');
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

    // Add optional SIDE panel
    if (sideBytes != null && sideBytes.isNotEmpty) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'SIDE',
          sideBytes,
          filename: sideName,
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
    final uri = Uri.parse('$baseUrl/v1/inspections/$inspectionId');
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
    final queryParams = <String, String>{'limit': limit.toString()};
    if (cursor != null) {
      queryParams['cursor'] = cursor.toIso8601String();
    }
    if (status != null) {
      queryParams['status'] = status;
    }

    final uri = Uri.parse('$baseUrl/v1/inspections').replace(
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
    final queryParams = <String, String>{};
    if (asOf != null) {
      queryParams['as_of'] = asOf.toIso8601String().split('T').first;
    }

    final uri = Uri.parse('$baseUrl/v1/rules').replace(
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
  Future<Map<String, dynamic>> getHealthz() async {
    final uri = Uri.parse('$baseUrl/healthz');
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
