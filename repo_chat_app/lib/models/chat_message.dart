class ChatMessage {
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final String type;

  ChatMessage({
    required this.content,
    required this.isUser,
    required this.timestamp,
    this.type = 'message',
  });

  Map<String, dynamic> toJson() {
    return {
      'content': content,
      'isUser': isUser,
      'timestamp': timestamp.toIso8601String(),
      'type': type,
    };
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      content: json['content'],
      isUser: json['isUser'],
      timestamp: DateTime.parse(json['timestamp']),
      type: json['type'] ?? 'message',
    );
  }
}