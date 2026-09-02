import 'dart:convert';

import 'package:http/http.dart'  as http;

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:8000';

  Future<List<dynamic>> getHistory() async {
    final response = await http.get(Uri.parse('$baseUrl/api/history'));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load history');
    }
  }
}
  