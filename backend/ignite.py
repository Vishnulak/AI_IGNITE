from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# Configuration
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
  # Get free API key from https://console.groq.com
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Subject definition
SUBJECT = "Data Structures"
SUBJECT_TOPICS = [
    "arrays", "linked lists", "stacks", "queues", "trees", "graphs",
    "hash tables", "heaps", "sorting algorithms", "searching algorithms",
    "big o notation", "time complexity", "space complexity",
    "binary search tree", "AVL tree", "red-black tree", "B-tree",
    "depth-first search", "breadth-first search", "dijkstra",
    "dynamic programming", "recursion", "data structure"
]

def check_relevance_strict(user_query):
    """
    STRICT relevance check - only Data Structure questions allowed
    Returns: (is_relevant: bool, reason: str)
    """
    system_prompt = f"""You are a STRICT classifier for {SUBJECT} questions ONLY.

RELEVANT topics: arrays, linked lists, stacks, queues, trees, graphs, hash tables, heaps, sorting, searching, Big-O, time/space complexity, BST, AVL, recursion, algorithms related to data structures.

IRRELEVANT topics: EVERYTHING ELSE including geography, history, cooking, sports, general knowledge, math (unless specifically about algorithm complexity), programming languages (unless asking about implementing data structures).

Examples:
- "What is a binary tree?" → RELEVANT
- "Explain bubble sort" → RELEVANT  
- "What is the capital of France?" → IRRELEVANT
- "How to cook pasta?" → IRRELEVANT
- "Who is the president?" → IRRELEVANT
- "Explain quantum physics" → IRRELEVANT

Question: "{user_query}"

Respond with ONLY ONE WORD - either "RELEVANT" or "IRRELEVANT". Nothing else."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": system_prompt}
        ],
        "temperature": 0.0,  # More deterministic
        "max_tokens": 5
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        classification = result['choices'][0]['message']['content'].strip().upper()
        
        is_relevant = 'RELEVANT' in classification and 'IRRELEVANT' not in classification
        return is_relevant, classification
    except Exception as e:
        print(f"Error in relevance check: {str(e)}")
        # Strict fallback: keyword matching
        query_lower = user_query.lower()
        is_relevant = any(topic in query_lower for topic in SUBJECT_TOPICS)
        return is_relevant, "FALLBACK_CHECK"

def get_chatbot_response(user_query):
    """
    Get response from LLM for Data Structure questions ONLY
    """
    system_prompt = f"""You are a specialized {SUBJECT} tutor. You ONLY answer questions about data structures and algorithms.

STRICT RULES:
1. ONLY discuss: arrays, linked lists, stacks, queues, trees, graphs, hash tables, heaps, sorting, searching, Big-O notation, time/space complexity, and related algorithms
2. If question is NOT about data structures, respond: "I can only answer Data Structures questions."
3. Never answer geography, history, general knowledge, or off-topic questions
4. Be educational and provide examples for data structure concepts

Answer this question ONLY if it's about Data Structures:"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"Error communicating with LLM: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@app.route('/')
def home():
    return jsonify({
        "message": f"Welcome to {SUBJECT} Chatbot API",
        "subject": SUBJECT,
        "guardrails": "STRICT MODE - Only Data Structures questions allowed",
        "endpoints": {
            "/chat": "POST - Send your question",
            "/health": "GET - Check API health"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "subject": SUBJECT,
        "model": "Groq Llama-3.3-70b",
        "guardrails": "STRICT"
    })

@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint with STRICT guardrails
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "error": "Missing 'message' field in request body"
            }), 400
        
        user_message = data['message'].strip()
        
        if not user_message:
            return jsonify({
                "error": "Message cannot be empty"
            }), 400
        
        # STRICT Guardrail Check
        is_relevant, classification = check_relevance_strict(user_message)
        
        if not is_relevant:
            return jsonify({
                "response": f"❌ IRRELEVANT QUESTION DETECTED\n\nI am a specialized {SUBJECT} tutor. I can ONLY answer questions about:\n• Arrays, Linked Lists, Stacks, Queues\n• Trees (Binary Trees, BST, AVL, B-Trees)\n• Graphs (DFS, BFS, Dijkstra)\n• Hash Tables, Heaps\n• Sorting & Searching Algorithms\n• Time & Space Complexity (Big-O)\n• Recursion & Dynamic Programming\n\nPlease ask me a question related to Data Structures!",
                "relevant": False,
                "subject": SUBJECT,
                "classification": classification
            }), 200
        
        # Get response only if relevant
        bot_response = get_chatbot_response(user_message)
        
        return jsonify({
            "response": bot_response,
            "relevant": True,
            "subject": SUBJECT
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/configure', methods=['POST'])
def configure():
    """
    Change subject and topics dynamically
    """
    try:
        data = request.get_json()
        global SUBJECT, SUBJECT_TOPICS
        
        if 'subject' in data:
            SUBJECT = data['subject']
        if 'topics' in data:
            SUBJECT_TOPICS = data['topics']
        
        return jsonify({
            "message": "Configuration updated successfully",
            "subject": SUBJECT,
            "topics_count": len(SUBJECT_TOPICS)
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Configuration error: {str(e)}"
        }), 500

if __name__ == '__main__':
    if GROQ_API_KEY == "your_groq_api_key_here":
        print("\n" + "="*60)
        print("⚠️  WARNING: Please set your GROQ_API_KEY!")
        print("="*60)
        print("\nSteps to get FREE API key:")
        print("1. Visit: https://console.groq.com")
        print("2. Sign up for free account")
        print("3. Go to API Keys section")
        print("4. Create new API key")
        print("5. Replace 'your_groq_api_key_here' in the code")
        print("\n" + "="*60 + "\n")
    
    print(f"\n🤖 {SUBJECT} Chatbot Starting...")
    print(f"📚 Subject: {SUBJECT}")
    print(f"🔒 Guardrails: STRICT MODE ENABLED")
    print(f"❌ Irrelevant questions will be REJECTED")
    print(f"🌐 Server: http://localhost:5000\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)