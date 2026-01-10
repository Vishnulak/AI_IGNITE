from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
import json
import time

load_dotenv()

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', os.getenv('GROQ_API_KEY'))
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Global state for tracking asked topics
asked_topics = set()

# ============================================================================
# SECTION 1: QUESTION GENERATION (Assessment Phase)
# ============================================================================

def call_groq_api(prompt, max_tokens=200, temperature=0.8, max_retries=3):
    """Call Groq API with retry logic"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a Data Structures and Algorithms expert. You MUST respond ONLY with valid JSON. No markdown, no explanations, just pure JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content'].strip()
            
            # Clean up markdown if present
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
        
        emergency_questions = [
            "How well do you understand arrays and array operations?",
            "How familiar are you with linked lists?",
            "How well do you know stacks and the LIFO principle?",
            "How comfortable are you with queues and the FIFO principle?",
            "How well do you understand basic recursion?"
        ]
        
        return emergency_questions[min(question_num - 1, len(emergency_questions) - 1)]

# ============================================================================
# SECTION 2: ROADMAP GENERATION (After Assessment)
# ============================================================================

def create_enhanced_roadmap_prompt(answers):
    """Create a detailed, user-friendly prompt for roadmap generation based on assessment"""
    
    # Calculate performance metrics
    total_questions = len(answers)
    total_score = sum(a['answer'] for a in answers)
    max_score = total_questions * 2
    performance_percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Determine user level based on performance
    if performance_percentage >= 75:
        user_level = "Advanced"
        focus_area = "mastery, optimization, and expert-level topics"
    elif performance_percentage >= 50:
        user_level = "Intermediate"
        focus_area = "strengthening core concepts and exploring advanced topics"
    elif performance_percentage >= 25:
        user_level = "Beginner-Intermediate"
        focus_area = "building solid fundamentals and basic implementations"
    else:
        user_level = "Beginner"
        focus_area = "establishing strong foundational understanding"
    
    # Categorize answers
    known_well = [a for a in answers if a['answer'] == 2]
    somewhat_known = [a for a in answers if a['answer'] == 1]
    not_known = [a for a in answers if a['answer'] == 0]
    
    prompt = f"""You are an expert Data Structures and Algorithms educator creating a personalized learning roadmap.

STUDENT ASSESSMENT RESULTS:
- Total Score: {total_score}/{max_score} points ({performance_percentage:.1f}%)
- Assessed Level: {user_level}
- Learning Focus: {focus_area}

CONCEPTS STUDENT KNOWS WELL:
{chr(10).join(f"✓ {a['question']}" for a in known_well) if known_well else "• Building foundational knowledge"}

CONCEPTS STUDENT SOMEWHAT KNOWS:
{chr(10).join(f"◐ {a['question']}" for a in somewhat_known) if somewhat_known else "• No partial knowledge areas"}

CONCEPTS STUDENT NEEDS TO LEARN:
{chr(10).join(f"✗ {a['question']}" for a in not_known) if not_known else "• Continue advancing knowledge"}

CREATE A COMPREHENSIVE PERSONALIZED LEARNING ROADMAP with these sections:

1. **overview**: A brief, encouraging 2-3 sentence summary of the student's current position and learning journey ahead

2. **currentLevel**: A clear, specific assessment with constructive feedback

3. **phases**: An array of 3-4 learning phases, each containing:
   - name: Phase name (e.g., "Foundation Building", "Intermediate Concepts", "Advanced Mastery")
   - duration: Realistic timeframe (e.g., "2-3 weeks", "1 month")
   - concepts: Array of 4-6 specific topics to master in this phase
   - goals: Array of 2-4 concrete, measurable learning objectives
   - description: 1-2 sentences explaining why this phase is important

4. **weeklyPlan**: A detailed 4-week study schedule, each week containing:
   - week: Week number (1-4)
   - focus: Main topic/theme for the week
   - dailyTasks: Array of 4-5 specific daily activities (30-60 min each)
   - practiceProblems: 3-4 types of coding exercises to complete
   - milestone: Clear achievement target by week's end

5. **resources**: Categorized learning materials:
   - videos: 4-5 specific video tutorial recommendations
   - articles: 4-5 blog posts, documentation, or tutorial links
   - practice: 4-5 coding platforms or specific problem sets
   - books: 2-3 recommended books or online resources

6. **priorityConcepts**: Array of 5-8 concepts ordered by learning priority, each with:
   - concept: Clear name of the data structure/algorithm
   - why: One sentence explaining its importance
   - timeToLearn: Realistic estimate (e.g., "2-3 hours", "1-2 days")
   - prerequisites: What to learn first (or "None" if foundational)

7. **milestones**: Array of 5-7 achievement checkpoints, each with:
   - title: Milestone name (e.g., "Master Array Manipulation")
   - description: What this achievement means (1-2 sentences)
   - timeframe: When to expect reaching this (e.g., "Week 2", "End of Month 1")
   - criteria: Specific way to verify achievement

8. **practiceStrategy**: An object containing:
   - approach: Overall practice philosophy (2-3 sentences)
   - easyProblems: 3-4 types of beginner-friendly exercises
   - mediumProblems: 3-4 intermediate challenge types
   - hardProblems: 3-4 advanced problem categories
   - projects: 3-4 hands-on project ideas to apply learning

9. **motivationalTips**: Array of 4-6 specific, actionable tips to maintain motivation and effective learning

10. **strengths**: Array of 2-4 identified strengths based on assessment
11. **improvements**: Array of 3-5 specific areas needing work
12. **recommendations**: Array of 3-5 immediate actionable recommendations

CRITICAL REQUIREMENTS:
- Be HIGHLY SPECIFIC to Data Structures & Algorithms (mention exact concepts: arrays, linked lists, trees, graphs, sorting, searching, etc.)
- Match ALL content to the student's {user_level} level
- Build progressively from their known concepts to unknown ones
- Use clear, encouraging, non-technical language where possible
- Provide ACTIONABLE steps with concrete time estimates
- Order everything from foundational to advanced
- Make it feel personalized based on their specific answers
- Focus on practical application and problem-solving
- Include variety in learning methods (visual, hands-on, theoretical)

OUTPUT: Return ONLY valid JSON. No markdown formatting, no code blocks, no explanations - just pure JSON that matches the structure above."""

    return prompt

def create_fallback_roadmap(answers):
    """Create a structured fallback roadmap if API fails"""
    total_questions = len(answers)
    total_score = sum(a['answer'] for a in answers)
    max_score = total_questions * 2
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 75:
        level = "Advanced"
        phases = [
            {
                "name": "Algorithm Optimization & Analysis",
                "duration": "2-3 weeks",
                "concepts": ["Time complexity mastery", "Space optimization", "Algorithm design patterns", "Trade-off analysis"],
                "goals": ["Master Big O notation", "Optimize existing algorithms", "Analyze complex algorithms"],
                "description": "Deep dive into algorithmic efficiency and optimization techniques"
            },
            {
                "name": "Expert Data Structures",
                "duration": "3-4 weeks",
                "concepts": ["AVL trees", "Red-black trees", "B-trees", "Advanced graph algorithms", "Segment trees"],
                "goals": ["Implement advanced trees", "Solve expert-level problems", "Build production-ready structures"],
                "description": "Master complex data structures used in real-world applications"
            },
            {
                "name": "System Design & Applications",
                "duration": "2-3 weeks",
                "concepts": ["Cache implementation", "Database indexing", "Distributed systems", "Real-world applications"],
                "goals": ["Design scalable systems", "Apply DS knowledge to architecture"],
                "description": "Apply data structures to system design and architecture"
            }
        ]
    elif percentage >= 50:
        level = "Intermediate"
        phases = [
            {
                "name": "Core Structures Mastery",
                "duration": "2-3 weeks",
                "concepts": ["Binary trees", "Hash tables", "Heaps", "Advanced recursion"],
                "goals": ["Implement core structures from scratch", "Solve medium difficulty problems"],
                "description": "Solidify understanding of fundamental data structures"
            },
            {
                "name": "Algorithm Fundamentals",
                "duration": "2-3 weeks",
                "concepts": ["Binary search", "Merge sort", "Quick sort", "DFS and BFS", "Dynamic programming intro"],
                "goals": ["Master common algorithms", "Understand time/space complexity"],
                "description": "Learn essential algorithms and their applications"
            },
            {
                "name": "Advanced Concepts Bridge",
                "duration": "2 weeks",
                "concepts": ["BST operations", "Graph representations", "Priority queues", "Backtracking"],
                "goals": ["Connect concepts together", "Solve complex problems"],
                "description": "Bridge to advanced topics and problem-solving"
            }
        ]
    elif percentage >= 25:
        level = "Beginner-Intermediate"
        phases = [
            {
                "name": "Fundamental Structures",
                "duration": "2 weeks",
                "concepts": ["Arrays", "Linked lists", "Stacks", "Queues"],
                "goals": ["Understand basic structures", "Implement from scratch", "Solve easy problems"],
                "description": "Build strong foundation with core data structures"
            },
            {
                "name": "Basic Algorithms",
                "duration": "2 weeks",
                "concepts": ["Linear search", "Bubble sort", "Selection sort", "Basic recursion"],
                "goals": ["Understand algorithm basics", "Write clean implementations"],
                "description": "Learn fundamental algorithms and problem-solving approaches"
            },
            {
                "name": "Intermediate Preparation",
                "duration": "2 weeks",
                "concepts": ["Two pointers", "Sliding window", "Hash map usage", "Simple trees"],
                "goals": ["Apply basic structures", "Prepare for intermediate topics"],
                "description": "Bridge gap between basics and intermediate concepts"
            }
        ]
    else:
        level = "Beginner"
        phases = [
            {
                "name": "Programming Fundamentals",
                "duration": "1-2 weeks",
                "concepts": ["Variables and data types", "Loops and conditions", "Functions", "Basic problem solving"],
                "goals": ["Understand basic programming", "Write simple programs"],
                "description": "Establish programming fundamentals needed for data structures"
            },
            {
                "name": "Introduction to Data Structures",
                "duration": "2-3 weeks",
                "concepts": ["What are data structures", "Arrays basics", "Lists", "Simple operations"],
                "goals": ["Understand why data structures matter", "Work with arrays"],
                "description": "Gentle introduction to data structures concepts"
            },
            {
                "name": "Basic Structures Practice",
                "duration": "2 weeks",
                "concepts": ["Array manipulation", "String operations", "Introduction to stacks and queues"],
                "goals": ["Gain confidence with basics", "Solve beginner problems"],
                "description": "Build confidence through practice with fundamental structures"
            }
        ]
    
    # Determine strengths and improvements
    known_well = [a['question'] for a in answers if a['answer'] == 2]
    not_known = [a['question'] for a in answers if a['answer'] == 0]
    
    return {
        "overview": f"Based on your assessment score of {percentage:.1f}%, you're at the {level} level in Data Structures and Algorithms. This personalized roadmap will guide you through systematic improvement tailored to your current knowledge.",
        "currentLevel": f"{level} - You've demonstrated solid understanding in {len(known_well)} concepts and have room to grow in {len(not_known)} areas. With focused practice, you'll make significant progress.",
        "phases": phases,
        "weeklyPlan": [
            {
                "week": 1,
                "focus": phases[0]["concepts"][0] if phases else "Foundation",
                "dailyTasks": ["Watch tutorial videos", "Read documentation", "Code basic examples", "Solve 2-3 easy problems"],
                "practiceProblems": ["Basic operations", "Simple implementations", "Walkthrough examples"],
                "milestone": f"Understand core concepts of {phases[0]['concepts'][0]}"
            },
            {
                "week": 2,
                "focus": phases[0]["concepts"][1] if len(phases[0]["concepts"]) > 1 else "Practice",
                "dailyTasks": ["Review previous concepts", "Learn new structure", "Implement from scratch", "Practice problems"],
                "practiceProblems": ["Mixed difficulty", "Real-world scenarios", "Code optimization"],
                "milestone": "Implement structures independently"
            },
            {
                "week": 3,
                "focus": phases[1]["concepts"][0] if len(phases) > 1 else "Advanced Practice",
                "dailyTasks": ["Study algorithms", "Analyze complexity", "Solve medium problems", "Review and debug"],
                "practiceProblems": ["Algorithm challenges", "Efficiency problems", "Edge cases"],
                "milestone": "Move to intermediate complexity"
            },
            {
                "week": 4,
                "focus": "Integration and Projects",
                "dailyTasks": ["Combine concepts", "Build mini-project", "Review weak areas", "Take practice tests"],
                "practiceProblems": ["Multi-concept problems", "Project tasks", "Interview questions"],
                "milestone": "Complete first project using learned structures"
            }
        ],
        "priorityConcepts": [
            {"concept": c, "why": "Essential foundation", "timeToLearn": "2-3 days", "prerequisites": "None"}
            for c in (phases[0]["concepts"][:5] if phases else ["Arrays", "Linked Lists"])
        ],
        "resources": {
            "videos": [
                "FreeCodeCamp - Data Structures Full Course",
                "CS50 - Data Structures lectures",
                "Abdul Bari - Algorithms",
                "MIT OpenCourseWare - Introduction to Algorithms",
                "mycodeschool - Data Structures"
            ],
            "articles": [
                "GeeksforGeeks Data Structures tutorials",
                "Programiz DS tutorials",
                "Visualgo - Algorithm visualizations",
                "Big-O Cheat Sheet",
                "LeetCode Explore Cards"
            ],
            "practice": [
                "LeetCode (start with Easy)",
                "HackerRank (Data Structures track)",
                "CodeSignal",
                "Codewars",
                "Exercism"
            ],
            "books": [
                "Introduction to Algorithms (CLRS)",
                "Cracking the Coding Interview",
                "Data Structures and Algorithms in Python"
            ]
        },
        "milestones": [
            {"title": "Foundation Complete", "description": "Understand and implement basic structures", "timeframe": "Week 2", "criteria": "Can implement array, list, stack, queue from scratch"},
            {"title": "Algorithm Basics", "description": "Grasp fundamental algorithms", "timeframe": "Week 3", "criteria": "Can explain and code basic sorting and searching"},
            {"title": "Problem Solver", "description": "Solve problems independently", "timeframe": "Week 4", "criteria": "Solve 10+ easy problems without hints"},
            {"title": "Intermediate Ready", "description": "Ready for advanced topics", "timeframe": "Month 2", "criteria": "Comfortable with trees and graphs basics"}
        ],
        "practiceStrategy": {
            "approach": "Start with understanding concepts visually, then implement from scratch, finally solve problems. Focus on one structure at a time before combining them.",
            "easyProblems": ["Array manipulations", "String operations", "Basic stack/queue usage", "Simple linked list operations"],
            "mediumProblems": ["Tree traversals", "Hash map applications", "Two-pointer techniques", "Binary search variations"],
            "hardProblems": ["Dynamic programming", "Complex graph problems", "Advanced tree operations", "Optimization challenges"],
            "projects": [
                "Build a text editor with undo/redo (stack)",
                "Implement autocomplete (trie)",
                "Create a task scheduler (priority queue)",
                "Build a social network graph analyzer"
            ]
        },
        "motivationalTips": [
            "Practice coding daily, even if just 30 minutes - consistency beats intensity",
            "Visualize data structures using drawings or online tools before coding",
            "Don't just memorize - understand WHY each structure works the way it does",
            "Start with problems slightly above your comfort zone",
            "Review and redo problems you found challenging",
            "Join online communities to discuss solutions and approaches"
        ],
        "strengths": known_well[:4] if known_well else ["Building foundational knowledge", "Taking proactive steps to learn"],
        "improvements": not_known[:5] if not_known else ["Continue building knowledge systematically"],
        "recommendations": [
            f"Focus on {level.lower()} level concepts appropriate for your current knowledge",
            "Implement each data structure from scratch at least once",
            "Solve problems daily to reinforce learning",
            "Use visualization tools to understand structure behavior",
            "Review time and space complexity for each operation"
        ]
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/start', methods=['POST'])
def start_assessment():
    """Start a new assessment - generates first question"""
    global asked_topics
    asked_topics.clear()
    
    try:
        first_question = generate_question(1, [])
        return jsonify({
            'success': True,
            'question': first_question,
            'question_number': 1,
            'total_questions': 5
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
                'message': 'Assessment completed - ready for roadmap generation'
            })
        
        next_q = generate_question(question_number, previous_answers)
        
        return jsonify({
            'success': True,
            'question': next_q,
            'question_number': question_number,
            'total_questions': 5,
            'completed': False
        })
    
    except Exception as e:
        print(f"Error in next_question: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/complete-assessment', methods=['POST'])
def complete_assessment():
    """Complete assessment and return score summary"""
    try:
        data = request.json
        answers = data.get('answers', [])
        
        if not answers or not isinstance(answers, list):
            return jsonify({
                'success': False,
                'error': 'Invalid answers data'
            }), 400
        
        # Calculate score
        total_score = sum(int(ans.get('answer', 0)) for ans in answers if isinstance(ans, dict))
        max_score = len(answers) * 2
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Determine level
        if percentage >= 75:
            level = "Advanced"
        elif percentage >= 50:
            level = "Intermediate"
        elif percentage >= 25:
            level = "Beginner-Intermediate"
        else:
            level = "Beginner"
        
        print(f"Assessment Complete - Score: {total_score}/{max_score} ({percentage:.1f}%) - Level: {level}")
        
        return jsonify({
            'success': True,
            'score': total_score,
            'max_score': max_score,
            'percentage': round(percentage, 1),
            'level': level,
            'message': 'Assessment completed successfully'
        })
    
    except Exception as e:
        print(f"Error in complete_assessment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-roadmap', methods=['POST'])
def generate_roadmap():
    """Generate personalized learning roadmap based on assessment results"""
    try:
        if not GROQ_API_KEY:
            return jsonify({
                'error': 'GROQ_API_KEY not configured',
                'success': False
            }), 500
        
        data = request.get_json()
        answers = data.get('answers', [])
        
        if not answers:
            return jsonify({
                'error': 'No assessment answers provided',
                'success': False
            }), 400
        
        print(f"Generating roadmap for {len(answers)} assessment answers")
        
        # Generate enhanced prompt
        prompt = create_enhanced_roadmap_prompt(answers)
        
        try:
            # Call Groq API for roadmap generation
            roadmap_data = call_groq_api(prompt, max_tokens=4000, temperature=0.7)
            
            return jsonify({
                'success': True,
                'roadmap': roadmap_data,
                'course': 'Data Structures and Algorithms',
                'generated_by': 'groq_api'
            }), 200
            
        except Exception as api_error:
            print(f"API Error, using fallback: {api_error}")
            # Use fallback roadmap
            fallback_roadmap = create_fallback_roadmap(answers)
            
            return jsonify({
                'success': True,
                'roadmap': fallback_roadmap,
                'course': 'Data Structures and Algorithms',
                'generated_by': 'fallback',
                'note': 'Generated using structured fallback due to API issue'
            }), 200
    
    except Exception as e:
        print(f"Error in generate_roadmap: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'ai': 'groq-llama-3.1-70b',
        'api_configured': bool(GROQ_API_KEY),
        'service': 'Integrated Assessment & Roadmap Generator'
    })

@app.route('/', methods=['GET'])
def home():
    """API documentation"""
    return jsonify({
        'message': 'Integrated Data Structures Assessment & Roadmap Generator API',
        'version': '3.0',
        'flow': 'Assessment (5 questions) → Score Analysis → Personalized Roadmap',
        'endpoints': {
            '/api/start': {
                'method': 'POST',
                'description': 'Start new assessment - returns first question',
                'response': 'First question with 3 choices (0=Don\'t know, 1=Somewhat, 2=Know well)'
            },
            '/api/next-question': {
                'method': 'POST',
                'description': 'Get next adaptive question based on previous answers',
                'required': 'previous_answers array',
                'response': 'Next question or completion status'
            },
            '/api/complete-assessment': {
                'method': 'POST',
                'description': 'Complete assessment and get score summary',
                'required': 'answers array',
                'response': 'Score, percentage, level assessment'
            },
            '/api/generate-roadmap': {
                'method': 'POST',
                'description': 'Generate personalized learning roadmap from assessment',
                'required': 'answers array from assessment',
                'response': 'Comprehensive personalized learning roadmap'
            },
            '/health': {
                'method': 'GET',
                'description': 'Check API health and configuration status'
            }
        },
        'assessment_flow': {
            'step1': 'POST /api/start → Get first question',
            'step2': 'POST /api/next-question (repeat for questions 2-5)',
            'step3': 'POST /api/complete-assessment → Get score summary',
            'step4': 'POST /api/generate-roadmap → Get personalized roadmap'
        },
        'answer_format': {
            'question': 'The generated question text',
            'answer': 'Integer value: 0 (Don\'t know) | 1 (Somewhat know) | 2 (Know well)',
            'example': {
                'question': 'How well do you know arrays?',
                'answer': 2
            }
        }
    }), 200

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 INTEGRATED ASSESSMENT & ROADMAP GENERATOR API")
    print("=" * 70)
    print(f"✓ AI Model: Groq Llama 3.1 70B Versatile")
    print(f"✓ Server: http://0.0.0.0:5000")
    print(f"✓ Health Check: http://localhost:5000/health")
    print(f"✓ Documentation: http://localhost:5000/")
    print(f"✓ API Key Configured: {'Yes ✓' if GROQ_API_KEY else 'No ✗ (Set GROQ_API_KEY)'}")
    print("=" * 70)
    print("\n📋 WORKFLOW:")
    print("  1. POST /api/start → Begin assessment")
    print("  2. POST /api/next-question → Get questions 2-5 (adaptive)")
    print("  3. POST /api/complete-assessment → Get final score")
    print("  4. POST /api/generate-roadmap → Generate personalized roadmap")
    print("=" * 70)
    print("\n🎯 ANSWER VALUES:")
    print("  0 = I don't know this")
    print("  1 = I somewhat know this")
    print("  2 = I know this well")
    print("=" * 70)
    print("\n🔥 Starting Flask server...\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)