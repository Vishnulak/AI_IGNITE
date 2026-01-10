import 'package:flutter/material.dart';
import 'screens/auth/login_screen.dart';

void main() {
  runApp(const LearningCopilotApp());
}

class LearningCopilotApp extends StatelessWidget {
  const LearningCopilotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Learning Copilot',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primaryColor: const Color(0xFF2C5E8A),
        scaffoldBackgroundColor: Colors.grey[100],
        appBarTheme: const AppBarTheme(color: Color(0xFF2C5E8A)),
      ),
      home: const LoginScreen(),
    );
  }
}