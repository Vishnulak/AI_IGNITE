import 'package:ai_ignite/screens/course_details/widgets/chatbot_widget.dart';
import 'package:flutter/material.dart';
import '../quiz/quiz_screen.dart';

class CourseDetailsScreen extends StatelessWidget {
  final String title;
  const CourseDetailsScreen({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 200,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.blueGrey[100],
                borderRadius: BorderRadius.circular(15),
              ),
              child: const Icon(Icons.play_circle_fill, size: 60, color: Color(0xFF2C5E8A)),
            ),
            const SizedBox(height: 20),
            Text(title, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            const Text("Instructor: Dr. Sarah Smith", style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 15),
            const Text("Course Modules", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Expanded(
              child: ListView(
                children: [
                  _moduleTile("1. Introduction to $title"),
                  _moduleTile("2. Core Concepts & Architecture"),
                  _moduleTile("3. Advanced Implementation"),
                ],
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.orange[700]),
                    onPressed: () => _showChatbot(context),
                    icon: const Icon(Icons.smart_toy, color: Colors.white),
                    label: const Text("Launch AI Tutor", style: TextStyle(color: Colors.white)),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2C5E8A)),
                    onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const QuizScreen())),
                    icon: const Icon(Icons.quiz, color: Colors.white),
                    label: const Text("Take Quiz", style: TextStyle(color: Colors.white)),
                  ),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }

  Widget _moduleTile(String title) {
    return ListTile(
      leading: const Icon(Icons.check_circle_outline, color: Colors.green),
      title: Text(title),
      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
    );
  }

  void _showChatbot(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => ChatbotWidget(),
    );
  }
}