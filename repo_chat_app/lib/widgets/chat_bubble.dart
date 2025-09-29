import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../models/chat_message.dart';

class ChatBubble extends StatelessWidget {
  final ChatMessage message;

  const ChatBubble({Key? key, required this.message}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final isError = message.type == 'error';
    final isSystem = message.type == 'system';

    Color bubbleColor;
    Color textColor;
    
    if (isUser) {
      bubbleColor = Theme.of(context).primaryColor;
      textColor = Colors.white;
    } else if (isError) {
      bubbleColor = Colors.red[100]!;
      textColor = Colors.red[800]!;
    } else if (isSystem) {
      bubbleColor = Colors.green[100]!;
      textColor = Colors.green[800]!;
    } else {
      bubbleColor = Colors.grey[200]!;
      textColor = Colors.black87;
    }

    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4.0, horizontal: 8.0),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: isError ? Colors.red[300] : 
                               isSystem ? Colors.green[300] : 
                               Colors.blue[300],
              child: Icon(
                isError ? Icons.error : 
                isSystem ? Icons.info : 
                Icons.smart_toy,
                size: 18,
                color: Colors.white,
              ),
            ),
            SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: bubbleColor,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (isUser)
                    Text(
                      message.content,
                      style: TextStyle(color: textColor),
                    )
                  else
                    MarkdownBody(
                      data: message.content,
                      styleSheet: MarkdownStyleSheet(
                        p: TextStyle(color: textColor),
                        h1: TextStyle(color: textColor, fontWeight: FontWeight.bold),
                        h2: TextStyle(color: textColor, fontWeight: FontWeight.bold),
                        h3: TextStyle(color: textColor, fontWeight: FontWeight.bold),
                        code: TextStyle(
                          backgroundColor: Colors.black12,
                          color: textColor,
                        ),
                        codeblockDecoration: BoxDecoration(
                          color: Colors.black12,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  SizedBox(height: 4),
                  Text(
                    _formatTime(message.timestamp),
                    style: TextStyle(
                      color: textColor.withOpacity(0.7),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (isUser) ...[
            SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              backgroundColor: Colors.grey[300],
              child: Icon(
                Icons.person,
                size: 18,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);
    
    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else {
      return '${time.day}/${time.month} ${time.hour}:${time.minute.toString().padLeft(2, '0')}';
    }
  }
}