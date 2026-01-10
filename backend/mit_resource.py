from flask import Flask, render_template_string, jsonify, request
import feedparser
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# MIT OCW RSS Feed URLs
MIT_OCW_FEEDS = {
    'new_courses': 'https://ocw.mit.edu/feeds/new-courses.rss',
    'updated_courses': 'https://ocw.mit.edu/feeds/updated-courses.rss',
}

def get_mit_ocw_courses(feed_type='new_courses'):
    """Fetch courses from MIT OCW RSS feeds"""
    feed_url = MIT_OCW_FEEDS.get(feed_type)
    
    if not feed_url:
        return []
    
    try:
        feed = feedparser.parse(feed_url)
        courses = []
        
        for entry in feed.entries[:10]:
            course = {
                'title': entry.title,
                'url': entry.link,
                'description': entry.get('summary', 'No description'),
                'published': entry.get('published', 'N/A')
            }
            courses.append(course)
        
        return courses
    except Exception as e:
        print(f"Error fetching feed: {e}")
        return []

def search_mit_ocw(query):
    """Search MIT OCW courses with improved selectors"""
    search_url = f"https://ocw.mit.edu/search/?q={query}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        courses = []
        
        # Try multiple possible selectors for MIT OCW structure
        # The structure changes, so we try different patterns
        
        # Pattern 1: Look for article tags with resource class
        course_items = soup.find_all('article', class_='resource')
        
        # Pattern 2: Look for divs with course-related classes
        if not course_items:
            course_items = soup.find_all('div', class_=['course-item', 'resource-item'])
        
        # Pattern 3: Look for any article tags
        if not course_items:
            course_items = soup.find_all('article')
        
        # Pattern 4: Look for links in search results
        if not course_items:
            result_section = soup.find('div', class_='search-results') or soup.find('main')
            if result_section:
                links = result_section.find_all('a', href=re.compile(r'/courses/'))
                for link in links[:10]:
                    if link.text.strip():
                        courses.append({
                            'title': link.text.strip(),
                            'url': link['href'] if link['href'].startswith('http') else 'https://ocw.mit.edu' + link['href'],
                            'description': 'Click to view course details'
                        })
        
        # Process found course items
        for item in course_items[:10]:
            # Try to find title
            title_elem = item.find('h3') or item.find('h2') or item.find('h4')
            
            # Try to find link
            link_elem = item.find('a', href=True)
            
            if title_elem and link_elem:
                url = link_elem['href']
                if not url.startswith('http'):
                    url = 'https://ocw.mit.edu' + url
                
                # Try to find description
                desc_elem = item.find('p', class_=['description', 'summary']) or item.find('p')
                description = desc_elem.text.strip() if desc_elem else 'No description available'
                
                course = {
                    'title': title_elem.text.strip(),
                    'url': url,
                    'description': description[:200]
                }
                courses.append(course)
        
        # If still no courses found, return a helpful message
        if not courses:
            return []
        
        return courses
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []
    except Exception as e:
        print(f"Parsing error: {e}")
        return []

def get_course_materials(course_url):
    """Extract materials from a specific MIT OCW course page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(course_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        materials = {
            'lecture_notes': [],
            'assignments': [],
            'exams': [],
            'videos': [],
            'readings': []
        }
        
        # Find all links on the page
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            text = link.text.strip().lower()
            
            # Skip empty or navigation links
            if not text or any(skip in href for skip in ['#', 'javascript:', 'mailto:']):
                continue
            
            # Make URL absolute
            if href.startswith('/'):
                full_url = 'https://ocw.mit.edu' + href
            elif not href.startswith('http'):
                continue
            else:
                full_url = href
            
            # Categorize based on URL and text patterns
            if '.pdf' in href.lower():
                link_data = {
                    'title': link.text.strip() or 'Download PDF',
                    'url': full_url
                }
                
                if any(kw in text for kw in ['lecture', 'notes', 'note']):
                    materials['lecture_notes'].append(link_data)
                elif any(kw in text for kw in ['assignment', 'problem', 'pset', 'homework', 'hw']):
                    materials['assignments'].append(link_data)
                elif any(kw in text for kw in ['exam', 'quiz', 'test', 'midterm', 'final']):
                    materials['exams'].append(link_data)
                elif any(kw in text for kw in ['reading', 'textbook']):
                    materials['readings'].append(link_data)
            
            # Find video links
            elif any(vid in href for vid in ['youtube.com', 'youtu.be']):
                materials['videos'].append({
                    'title': link.text.strip() or 'Video Lecture',
                    'url': full_url
                })
        
        # Remove duplicates
        for key in materials:
            seen = set()
            unique = []
            for item in materials[key]:
                if item['url'] not in seen:
                    seen.add(item['url'])
                    unique.append(item)
            materials[key] = unique
        
        return materials
        
    except Exception as e:
        print(f"Error extracting materials: {e}")
        return {
            'lecture_notes': [],
            'assignments': [],
            'exams': [],
            'videos': [],
            'readings': []
        }

# HTML Template (same as before)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MIT OpenCourseWare Finder</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .search-box {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .tab-btn {
            flex: 1;
            padding: 12px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .tab-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .search-form {
            display: flex;
            gap: 10px;
        }
        
        .search-input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
        }
        
        .search-btn {
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .search-btn:hover {
            transform: translateY(-2px);
        }
        
        .loading {
            text-align: center;
            color: white;
            font-size: 1.2em;
            padding: 20px;
            display: none;
        }
        
        .results {
            display: none;
        }
        
        .course-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .course-card:hover {
            transform: translateY(-5px);
        }
        
        .course-card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.3em;
        }
        
        .course-card a {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }
        
        .course-card a:hover {
            text-decoration: underline;
        }
        
        .course-card p {
            color: #666;
            margin: 10px 0;
            line-height: 1.6;
        }
        
        .materials-btn {
            margin-top: 15px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .materials-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            display: none;
        }
        
        .material-category {
            margin-bottom: 15px;
        }
        
        .material-category h4 {
            color: #764ba2;
            margin-bottom: 8px;
        }
        
        .material-item {
            padding: 8px;
            background: #f8f9fa;
            margin: 5px 0;
            border-radius: 5px;
        }
        
        .material-item a {
            color: #667eea;
            font-size: 0.9em;
        }
        
        .no-results {
            background: white;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 MIT OpenCourseWare Finder</h1>
            <p>Access 2,500+ Free MIT Courses</p>
        </div>
        
        <div class="search-box">
            <div class="tabs">
                <button class="tab-btn active" data-tab="search">Search Courses</button>
                <button class="tab-btn" data-tab="new_courses">New Courses</button>
                <button class="tab-btn" data-tab="updated_courses">Updated Courses</button>
            </div>
            
            <form class="search-form" id="searchForm">
                <input 
                    type="text" 
                    class="search-input" 
                    id="queryInput" 
                    placeholder="Search for courses (e.g., Machine Learning, Calculus, Physics)"
                    required
                >
                <button type="submit" class="search-btn">Search</button>
            </form>
        </div>
        
        <div class="loading" id="loading">
            🔍 Loading courses... Please wait
        </div>
        
        <div class="results" id="results"></div>
    </div>

    <script>
        let currentTab = 'search';
        
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentTab = this.dataset.tab;
                
                if (currentTab !== 'search') {
                    loadFeed(currentTab);
                }
            });
        });
        
        // Search form
        document.getElementById('searchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const query = document.getElementById('queryInput').value;
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            
            loading.style.display = 'block';
            results.style.display = 'none';
            
            try {
                let response;
                if (currentTab === 'search') {
                    response = await fetch(`/search?q=${encodeURIComponent(query)}`);
                } else {
                    response = await fetch(`/feed?type=${currentTab}`);
                }
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                results.innerHTML = `<div class="no-results"><p>Error: ${error.message}</p></div>`;
                results.style.display = 'block';
            } finally {
                loading.style.display = 'none';
            }
        });
        
        async function loadFeed(type) {
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            
            loading.style.display = 'block';
            results.style.display = 'none';
            
            try {
                const response = await fetch(`/feed?type=${type}`);
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                results.innerHTML = `<div class="no-results"><p>Error: ${error.message}</p></div>`;
                results.style.display = 'block';
            } finally {
                loading.style.display = 'none';
            }
        }
        
        function displayResults(courses) {
            const results = document.getElementById('results');
            
            if (!Array.isArray(courses) || courses.length === 0) {
                results.innerHTML = '<div class="no-results"><p>No courses found. Try a different search term or browse new courses.</p></div>';
                results.style.display = 'block';
                return;
            }
            
            let html = '';
            courses.forEach((course, index) => {
                html += `
                    <div class="course-card">
                        <h3>${course.title}</h3>
                        <a href="${course.url}" target="_blank">View Course →</a>
                        ${course.description ? `<p>${course.description}</p>` : ''}
                        ${course.published ? `<p><small>Published: ${course.published}</small></p>` : ''}
                        <button class="materials-btn" onclick="loadMaterials('${encodeURIComponent(course.url)}', ${index})">
                            Load Course Materials
                        </button>
                        <div class="materials-section" id="materials-${index}"></div>
                    </div>
                `;
            });
            
            results.innerHTML = html;
            results.style.display = 'block';
        }
        
        async function loadMaterials(courseUrl, index) {
            const materialsDiv = document.getElementById(`materials-${index}`);
            materialsDiv.innerHTML = '<p>Loading materials...</p>';
            materialsDiv.style.display = 'block';
            
            try {
                const response = await fetch('/materials', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ course_url: decodeURIComponent(courseUrl) })
                });
                
                const materials = await response.json();
                displayMaterials(materials, index);
            } catch (error) {
                materialsDiv.innerHTML = `<p>Error loading materials: ${error.message}</p>`;
            }
        }
        
        function displayMaterials(materials, index) {
            const materialsDiv = document.getElementById(`materials-${index}`);
            
            let html = '';
            
            const categories = {
                'lecture_notes': '📝 Lecture Notes',
                'assignments': '📋 Assignments',
                'exams': '📝 Exams',
                'videos': '🎥 Videos'
            };
            
            for (const [key, title] of Object.entries(categories)) {
                const items = materials[key] || [];
                if (items.length > 0) {
                    html += `<div class="material-category">
                        <h4>${title}</h4>`;
                    
                    items.forEach(item => {
                        html += `<div class="material-item">
                            <a href="${item.url}" target="_blank">${item.title}</a>
                        </div>`;
                    });
                    
                    html += '</div>';
                }
            }
            
            if (html === '') {
                html = '<p>No downloadable materials found. Visit the course page for more information.</p>';
            }
            
            materialsDiv.innerHTML = html;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([]), 400
    
    courses = search_mit_ocw(query)
    return jsonify(courses)

@app.route('/feed')
def feed():
    feed_type = request.args.get('type', 'new_courses')
    courses = get_mit_ocw_courses(feed_type)
    return jsonify(courses)

@app.route('/materials', methods=['POST'])
def materials():
    data = request.get_json()
    course_url = data.get('course_url', '')
    
    if not course_url:
        return jsonify({
            'lecture_notes': [],
            'assignments': [],
            'exams': [],
            'videos': [],
            'readings': []
        }), 400
    
    materials = get_course_materials(course_url)
    return jsonify(materials)

if __name__ == '__main__':
    app.run(debug=True, port=5000)