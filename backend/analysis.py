from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json
import time

app = Flask(__name__)
CORS(app)
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

asked_topics = set()

def call_groq_api(prompt, max_retries=3):
    """Call Groq API with retry logic"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a Data Structures expert. You MUST respond ONLY with valid JSON. No markdown, no explanations, just pure JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 200
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content'].strip()
            
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            content = content.strip()
            parsed = json.loads(content)
            return parsed
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error (attempt {attempt + 1}): {e}")
            print(f"Content: {content}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise
        except Exception as e:
            print(f"Unexpected Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise
    
    raise Exception("Failed to get valid response from API")

def generate_question(question_num, previous_answers):
    """Generate adaptive questions based on previous answers using Groq LLM"""
    
    global asked_topics
    
    context = "You are an expert Data Structures and Algorithms educator.\n\n"
    
    if asked_topics:
        context += f"Topics already asked: {', '.join(asked_topics)}\n"
        context += "You MUST ask about DIFFERENT topics that have NOT been covered yet.\n\n"
    
    if previous_answers:
        context += "Previous Questions and Student Responses:\n"
        for i, ans in enumerate(previous_answers, 1):
            level_text = {
                2: "KNOWS WELL",
                1: "SOMEWHAT KNOWS", 
                0: "DOESN'T KNOW"
            }
            context += f"{i}. {ans['question']}\n   Answer: {level_text[ans['answer']]}\n\n"
        
        total_score = sum(a['answer'] for a in previous_answers)
        max_score = len(previous_answers) * 2
        performance_rate = total_score / max_score
        
        context += f"Current Performance: {total_score}/{max_score} points ({performance_rate*100:.0f}%)\n\n"
        
        if performance_rate >= 0.75:
            difficulty = "ADVANCED"
            context += "Student is performing EXCELLENTLY. Ask an ADVANCED/EXPERT level question.\n"
        elif performance_rate >= 0.5:
            difficulty = "INTERMEDIATE"
            context += "Student is performing MODERATELY. Ask an INTERMEDIATE level question.\n"
        elif performance_rate >= 0.25:
            difficulty = "BASIC"
            context += "Student is STRUGGLING. Ask a FUNDAMENTAL/BASIC question.\n"
        else:
            difficulty = "VERY BASIC"
            context += "Student knows very little. Ask the most FUNDAMENTAL question possible.\n"
    else:
        difficulty = "BASIC"
        context += "This is the FIRST question. Start with a BASIC foundational concept.\n"
    
    if difficulty == "VERY BASIC":
        topics = [
            "arrays and basic indexing",
            "what variables store",
            "basic list operations",
            "simple iteration/loops",
            "counting elements"
        ]
    elif difficulty == "BASIC":
        topics = [
            "arrays and array operations",
            "linked lists basics",
            "stack LIFO principle",
            "queue FIFO principle",
            "basic recursion",
            "linear search",
            "bubble sort basics"
        ]
    elif difficulty == "INTERMEDIATE":
        topics = [
            "binary search algorithm",
            "merge sort or quick sort",
            "binary trees structure",
            "hash tables and hashing",
            "doubly linked lists",
            "circular queues",
            "depth-first search (DFS)",
            "breadth-first search (BFS)",
            "heaps (min/max heap)"
        ]
    else:
        topics = [
            "AVL trees and rotations",
            "red-black trees",
            "B-trees and B+ trees",
            "graph algorithms (Dijkstra, Bellman-Ford)",
            "dynamic programming with data structures",
            "trie data structure",
            "segment trees",
            "disjoint set union (DSU)",
            "skip lists",
            "suffix arrays or suffix trees"
        ]
    
    available_topics = [t for t in topics if t not in asked_topics]
    if not available_topics:
        available_topics = topics
        asked_topics.clear()
    
    context += f"\nAvailable topics to choose from: {', '.join(available_topics)}\n"
    
    prompt = f"""{context}

CRITICAL INSTRUCTIONS:
1. Generate question {question_num} of 5 for Data Structures assessment
2. Pick ONE topic from the available topics list above that has NOT been asked yet
3. Ask about knowledge level: "How well do you know [concept]?"
4. Make it specific to the difficulty level: {difficulty}
5. The question MUST be completely DIFFERENT from all previous questions

OUTPUT FORMAT (respond with ONLY this JSON, nothing else):
{{
  "question": "How well do you know [specific concept]?",
  "topic": "topic_name"
}}

Generate the question NOW:"""

    try:
        result = call_groq_api(prompt)
        
        question_text = result.get('question', '')
        topic = result.get('topic', 'unknown')
        
        asked_topics.add(topic)
        
        print(f"Generated Question {question_num}: {question_text}")
        print(f"Topic: {topic}")
        
        return question_text
    
    except Exception as e:
        print(f"ERROR generating question: {e}")
        print("Using emergency fallback")
        
        if previous_answers:
            total_score = sum(a['answer'] for a in previous_answers)
            max_score = len(previous_answers) * 2
            if total_score >= max_score * 0.7:
                emergency_questions = [
                    "How well do you know self-balancing binary search trees?",
                    "How familiar are you with graph traversal algorithms like Dijkstra's?",
                    "How well do you understand trie data structures?",
                    "How comfortable are you with dynamic programming optimizations?",
                    "How well do you know segment trees for range queries?"
                ]
            elif total_score >= max_score * 0.4:
                emergency_questions = [
                    "How well do you know binary search trees?",
                    "How familiar are you with hash tables?",
                    "How well do you understand depth-first search?",
                    "How comfortable are you with heaps?",
                    "How well do you know merge sort?"
                ]
            else:
                emergency_questions = [
                    "How well do you understand arrays?",
                    "How familiar are you with linked lists?",
                    "How well do you know stacks?",
                    "How comfortable are you with queues?",
                    "How well do you understand loops?"
                ]
        else:
            emergency_questions = [
                "How well do you understand arrays?",
                "How familiar are you with linked lists?",
                "How well do you know stacks?",
                "How comfortable are you with queues?",
                "How well do you understand recursion?"
            ]
        
        return emergency_questions[question_num - 1] if question_num <= len(emergency_questions) else emergency_questions[0]

@app.route('/api/start', methods=['POST'])
def start_assessment():
    """Start a new assessment"""
    global asked_topics
    asked_topics.clear()
    
    try:
        first_question = generate_question(1, [])
        return jsonify({
            'success': True,
            'question': first_question,
            'question_number': 1
        })
    except Exception as e:
        print(f"Error in start_assessment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/next-question', methods=['POST'])
def next_question():
    """Get next question based on previous answers"""
    try:
        data = request.json
        previous_answers = data.get('previous_answers', [])
        question_number = len(previous_answers) + 1
        
        if question_number > 5:
            return jsonify({
                'success': True,
                'completed': True,
                'message': 'Assessment completed'
            })
        
        next_q = generate_question(question_number, previous_answers)
        
        return jsonify({
            'success': True,
            'question': next_q,
            'question_number': question_number,
            'completed': False
        })
    
    except Exception as e:
        print(f"Error in next_question: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_results():
    """Calculate and return only the final score"""
    try:
        data = request.json
        answers = data.get('answers', [])
        
        # Validate answers data
        if not answers or not isinstance(answers, list):
            print("Invalid answers data")
            return jsonify({
                'success': True,
                'score': 0,
                'max_score': 10,
                'percentage': 0.0
            })
        
        # Calculate score: Know well = 2, Somewhat = 1, Don't know = 0
        total_score = 0
        for ans in answers:
            if isinstance(ans, dict) and 'answer' in ans:
                answer_val = ans['answer']
                if isinstance(answer_val, (int, float)):
                    total_score += int(answer_val)
        
        max_score = len(answers) * 2
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        print(f"Analysis - Score: {total_score}/{max_score} = {percentage}%")
        
        return jsonify({
            'success': True,
            'score': total_score,
            'max_score': max_score,
            'percentage': round(percentage, 1)
        })
    
    except Exception as e:
        print(f"Error in analyze_results: {e}")
        import traceback
        traceback.print_exc()
        
        # Return default score on error
        return jsonify({
            'success': True,
            'score': 0,
            'max_score': 10,
            'percentage': 0.0
        })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'ai': 'groq-llama'})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Data Structures Assessment API Started!")
    print("=" * 60)
    print(f"✓ Using Groq AI (Llama 3.1 70B)")
    print(f"✓ Server running on http://0.0.0.0:5000")
    print(f"✓ Health check: http://localhost:5000/health")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)