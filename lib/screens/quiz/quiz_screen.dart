import 'package:flutter/material.dart';

class QuizScreen extends StatefulWidget {
  const QuizScreen({super.key});

  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> {
  int _questionIndex = 0;
  final List<Map<String, dynamic>> _questions = [
    {
      'question': 'What is the time complexity of a binary search?',
      'answers': ['O(n)', 'O(log n)', 'O(n^2)', 'O(1)'],
      'correctIndex': 1,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Knowledge Check")),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            LinearProgressIndicator(value: (_questionIndex + 1) / _questions.length),
            const SizedBox(height: 40),
            Text(
              _questions[_questionIndex]['question'],
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 30),
            ...(_questions[_questionIndex]['answers'] as List<String>).asMap().entries.map((entry) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.black,
                  ),
                  onPressed: () {
                    // Logic for answer checking would go here
                  },
                  child: Text(entry.value),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}