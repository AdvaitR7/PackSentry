import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiService {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:8000';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  Future<Map<String, dynamic>> analyzeImages({
    required Uint8List frontBytes,
    String frontName = 'front.png',
    Uint8List? backBytes,
    String backName = 'back.png',
    Uint8List? sideBytes,
    String sideName = 'side.png',
  }) async {
    final uri = Uri.parse('$baseUrl/api/analyze');
    final request = http.MultipartRequest('POST', uri);

    request.files.add(
      http.MultipartFile.fromBytes(
        'front_image',
        frontBytes,
        filename: frontName,
      ),
    );

    if (backBytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'back_image',
          backBytes,
          filename: backName,
        ),
      );
    }
    if (sideBytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'side_image',
          sideBytes,
          filename: sideName,
        ),
      );
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception(
        'Failed to analyze images: ${response.statusCode} - ${response.body}',
      );
    }
  }
}
