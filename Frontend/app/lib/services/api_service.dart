import 'dart:io';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiService {
  // Use 10.0.2.2 for Android Emulator to connect to localhost:8000
  static const String baseUrl = 'http://10.0.2.2:8000';
  Future<Map<String, dynamic>> analyzeImages({
    required File frontImage,
    File? backImage,
    File? sideImage,
  }) async {
    final uri = Uri.parse('$baseUrl/api/analyze');
    final request = http.MultipartRequest('POST', uri);
    // Add front image (mandatory)
    request.files.add(
      await http.MultipartFile.fromPath('front_image', frontImage.path),
    );
    // Add optional back and side images if present
    if (backImage != null) {
      request.files.add(
        await http.MultipartFile.fromPath('back_image', backImage.path),
      );
    }
    if (sideImage != null) {
      request.files.add(
        await http.MultipartFile.fromPath('side_image', sideImage.path),
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
