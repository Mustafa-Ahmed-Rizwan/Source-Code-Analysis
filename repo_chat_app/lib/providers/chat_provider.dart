import 'package:flutter/foundation.dart';
import '../models/chat_message.dart';
import '../models/api_response.dart';
import '../models/api_service.dart';

class ChatProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  List<ChatMessage> _messages = [];
  bool _isLoading = false;
  bool _isRepositoryLoaded = false;
  String? _currentRepository;
  String? _error;

  List<ChatMessage> get messages => _messages;
  bool get isLoading => _isLoading;
  bool get isRepositoryLoaded => _isRepositoryLoaded;
  String? get currentRepository => _currentRepository;
  String? get error => _error;

  void setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void setError(String? error) {
    _error = error;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  Future<bool> checkConnection() async {
    return await _apiService.checkHealth();
  }

  Future<void> ingestRepository(String repoUrl) async {
    setLoading(true);
    clearError();

    try {
      final response = await _apiService.ingestRepository(repoUrl);
      
      if (response.success) {
        _isRepositoryLoaded = true;
        _currentRepository = repoUrl;
        _messages.clear();
        
        // Add system message
        _messages.add(ChatMessage(
          content: response.response,
          isUser: false,
          timestamp: DateTime.now(),
          type: 'system',
        ));
      } else {
        setError(response.response);
      }
    } catch (e) {
      setError('Failed to ingest repository: $e');
    } finally {
      setLoading(false);
    }
  }

  Future<void> sendMessage(String message) async {
    if (message.trim().isEmpty) return;

    // Add user message
    _messages.add(ChatMessage(
      content: message,
      isUser: true,
      timestamp: DateTime.now(),
    ));
    notifyListeners();

    setLoading(true);
    clearError();

    try {
      final response = await _apiService.sendMessage(message);
      
      if (response.success) {
        // Handle special commands
        if (message == "clear_chat" && response.response.isEmpty) {
          _messages.clear();
        } else if (message == "new_chat" || message == "clear_repo") {
          _messages.clear();
          _isRepositoryLoaded = false;
          _currentRepository = null;
        } else if (response.response.isNotEmpty) {
          // Add bot response
          _messages.add(ChatMessage(
            content: response.response,
            isUser: false,
            timestamp: DateTime.now(),
            type: response.type ?? 'answer',
          ));
        }
      } else {
        setError(response.response);
        // Add error message to chat
        _messages.add(ChatMessage(
          content: response.response,
          isUser: false,
          timestamp: DateTime.now(),
          type: 'error',
        ));
      }
    } catch (e) {
      setError('Failed to send message: $e');
      _messages.add(ChatMessage(
        content: 'Error: $e',
        isUser: false,
        timestamp: DateTime.now(),
        type: 'error',
      ));
    } finally {
      setLoading(false);
    }
  }

  void clearChat() {
    sendMessage("clear_chat");
  }

  void newChat() {
    sendMessage("new_chat");
  }

  void clearRepository() {
    sendMessage("clear_repo");
  }
}