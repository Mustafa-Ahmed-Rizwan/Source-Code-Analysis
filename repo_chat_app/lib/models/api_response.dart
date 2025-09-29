class ApiResponse {
  final String response;
  final String? type;
  final bool success;

  ApiResponse({
    required this.response,
    this.type,
    required this.success,
  });

  factory ApiResponse.fromJson(Map<String, dynamic> json) {
    return ApiResponse(
      response: json['response'] ?? '',
      type: json['type'],
      success: true,
    );
  }

  factory ApiResponse.error(String message) {
    return ApiResponse(
      response: message,
      type: 'error',
      success: false,
    );
  }
}