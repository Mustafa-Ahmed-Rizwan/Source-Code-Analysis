import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/api_response.dart';

class ApiService {
  // Change this to your FastAPI server URL
  static const String baseUrl = 'http://192.168.100.9:8080'; // For Android emulator
  // For physical device, use your computer's IP: 'http://192.168.1.XXX:8080'
  
  static const Map<String, String> headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  Future<ApiResponse> ingestRepository(String repoUrl) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/repository'),
        headers: headers,
        body: jsonEncode({'question': repoUrl}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return ApiResponse.fromJson(data);
      } else {
        return ApiResponse.error('Server error: ${response.statusCode}');
      }
    } catch (e) {
      return ApiResponse.error('Connection error: $e');
    }
  }

  Future<ApiResponse> sendMessage(String message) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/chat'),
        headers: headers,
        body: jsonEncode({'msg': message}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return ApiResponse.fromJson(data);
      } else {
        return ApiResponse.error('Server error: ${response.statusCode}');
      }
    } catch (e) {
      return ApiResponse.error('Connection error: $e');
    }
  }

  Future<bool> checkHealth() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/health'),
        headers: headers,
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}