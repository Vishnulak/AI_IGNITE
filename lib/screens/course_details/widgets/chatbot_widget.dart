import 'package:flutter/material.dart';

class ChatbotWidget extends StatelessWidget {
  const ChatbotWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const Text("AI Learning Copilot", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const Divider(),
          Expanded(
            child: ListView(
              children: const [
                _ChatBubble(message: "Hello! I'm your AI Tutor. What can I help you learn today?", isUser: false),
                _ChatBubble(message: "Explain the Big O notation for search algorithms.", isUser: true),
                _ChatBubble(message: "Certainly! Big O notation describes the execution time...", isUser: false),
              ],
            ),
          ),
          TextField(
            decoration: InputDecoration(
              hintText: "Ask a question...",
              suffixIcon: const Icon(Icons.send),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(20)),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  const _ChatBubble({required this.message, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 5),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF2C5E8A) : Colors.grey[300],
          borderRadius: BorderRadius.circular(15),
        ),
        child: Text(message, style: TextStyle(color: isUser ? Colors.white : Colors.black)),
      ),
    );
  }
}