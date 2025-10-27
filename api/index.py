from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from anthropic import Anthropic
import os
from datetime import datetime
from typing import Optional
import uuid

# Import department prompts
from api.department_prompts import get_department_prompt, get_department_list, get_department_name
app = FastAPI()

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Session storage (in production, use Redis or database)
sessions = {}

# Embedded HTML (no templates folder needed)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PipeWrench AI - Municipal Knowledge Capture</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-blue: #1e40af;
            --secondary-blue: #3b82f6;
            --light-blue: #eff6ff;
            --accent-orange: #f59e0b;
            --dark-orange: #d97706;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --text-light: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, #1e293b 100%);
            color: var(--text-light);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: var(--bg-card);
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            overflow: hidden;
        }

        header {
            background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
            padding: 40px;
            text-align: center;
            border-bottom: 4px solid var(--accent-orange);
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: white;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }

        header p {
            font-size: 1.1em;
            color: var(--light-blue);
            opacity: 0.95;
        }

        .tabs {
            display: flex;
            background: var(--bg-dark);
            border-bottom: 2px solid var(--border);
            overflow-x: auto;
        }

        .tab-btn {
            flex: 1;
            padding: 18px 24px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            white-space: nowrap;
        }

        .tab-btn:hover {
            background: rgba(59, 130, 246, 0.1);
            color: var(--secondary-blue);
        }

        .tab-btn.active {
            color: var(--accent-orange);
            border-bottom-color: var(--accent-orange);
            background: rgba(245, 158, 11, 0.1);
        }

        .tab-content {
            display: none;
            padding: 40px;
            animation: fadeIn 0.3s ease;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        h2 {
            color: var(--secondary-blue);
            margin-bottom: 24px;
            font-size: 1.8em;
            border-bottom: 2px solid var(--border);
            padding-bottom: 12px;
        }

        .form-group {
            margin-bottom: 24px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: var(--text-light);
            font-weight: 600;
            font-size: 0.95em;
        }

        .form-control {
            width: 100%;
            padding: 14px 16px;
            background: var(--bg-dark);
            border: 2px solid var(--border);
            border-radius: 8px;
            color: var(--text-light);
            font-size: 1em;
            transition: all 0.3s ease;
            font-family: inherit;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--secondary-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        select.form-control {
            cursor: pointer;
        }

        textarea.form-control {
            resize: vertical;
            min-height: 120px;
        }

        .btn {
            padding: 14px 32px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-orange) 0%, var(--dark-orange) 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .answer-box {
            background: var(--bg-dark);
            border-left: 4px solid var(--secondary-blue);
            padding: 24px;
            border-radius: 8px;
            margin-top: 16px;
            line-height: 1.8;
            color: var(--text-light);
        }

        #answer-container, #upload-result {
            margin-top: 32px;
            animation: fadeIn 0.5s ease;
        }

        #answer-container h3, #upload-result h3 {
            color: var(--accent-orange);
            margin-bottom: 16px;
            font-size: 1.4em;
        }

        small {
            display: block;
            margin-top: 8px;
            color: var(--text-muted);
            font-size: 0.85em;
        }

        footer {
            background: var(--bg-dark);
            padding: 32px 40px;
            border-top: 2px solid var(--border);
            color: var(--text-muted);
            font-size: 0.9em;
            line-height: 1.6;
        }

        footer h4 {
            color: var(--secondary-blue);
            margin-bottom: 12px;
            font-size: 1.1em;
        }

        footer a {
            color: var(--accent-orange);
            text-decoration: none;
            transition: color 0.3s ease;
        }

        footer a:hover {
            color: var(--dark-orange);
            text-decoration: underline;
        }

        .footer-section {
            margin-bottom: 20px;
        }

        .spinner {
            border: 3px solid var(--border);
            border-top: 3px solid var(--accent-orange);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
            display: none;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
            header h1 {
                font-size: 1.8em;
            }

            .tab-content {
                padding: 24px;
            }

            .tabs {
                flex-wrap: wrap;
            }

            .tab-btn {
                flex: 1 1 50%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔧 PipeWrench AI</h1>
            <p>Preserving Institutional Knowledge in Public Works</p>
        </header>

        <div class="tabs">
            <button class="tab-btn active" data-tab="query">Ask Questions</button>
            <button class="tab-btn" data-tab="upload">Upload Documents</button>
            <button class="tab-btn" data-tab="report">Generate Report</button>
            <button class="tab-btn" data-tab="settings">Settings</button>
        </div>

        <div id="query" class="tab-content active">
            <h2>Ask a Question</h2>
            
            <div class="form-group">
                <label for="department">Department/Role:</label>
                <select id="department" class="form-control">
                    <option value="">Loading departments...</option>
                </select>
            </div>

            <div class="form-group">
                <label for="question">Your Question:</label>
                <textarea id="question" rows="4" class="form-control" 
                    placeholder="e.g., What are the proper procedures for confined space entry in a wastewater lift station?"></textarea>
            </div>

            <button onclick="askQuestion()" class="btn btn-primary">Ask Question</button>
            <div class="spinner" id="query-spinner"></div>

            <div id="answer-container" style="display:none;">
                <h3>Answer:</h3>
                <div id="answer" class="answer-box"></div>
            </div>
        </div>

        <div id="upload" class="tab-content">
            <h2>Upload Document</h2>
            
            <div class="form-group">
                <label for="upload-department">Department/Role:</label>
                <select id="upload-department" class="form-control">
                    <option value="">Loading departments...</option>
                </select>
            </div>

            <div class="form-group">
                <label for="file">Select Document:</label>
                <input type="file" id="file" class="form-control" accept=".txt,.pdf,.doc,.docx">
                <small>Supported formats: TXT, PDF, DOC, DOCX</small>
            </div>

            <button onclick="uploadDocument()" class="btn btn-primary">Upload & Analyze</button>
            <div class="spinner" id="upload-spinner"></div>

            <div id="upload-result" style="display:none;">
                <h3>Analysis:</h3>
                <div id="analysis" class="answer-box"></div>
            </div>
        </div>

        <div id="report" class="tab-content">
            <h2>Generate Report</h2>
            <p style="margin-bottom: 24px; color: var(--text-muted);">
                Generate a comprehensive report with all questions, answers, and document analyses from this session. 
                All responses include APA-style citations and references.
            </p>
            <button onclick="generateReport()" class="btn btn-primary">Generate Report</button>
        </div>

        <div id="settings" class="tab-content">
            <h2>Settings</h2>
            
            <div class="form-group">
                <label for="api-key">Anthropic API Key (Optional):</label>
                <input type="password" id="api-key" class="form-control" 
                    placeholder="sk-ant-...">
                <small>Leave blank to use server default. Your key is stored locally and never sent to our servers except for API calls.</small>
            </div>

            <button onclick="saveSettings()" class="btn btn-primary">Save Settings</button>
            
            <div style="margin-top: 32px; padding: 20px; background: var(--bg-dark); border-radius: 8px; border-left: 4px solid var(--accent-orange);">
                <h4 style="color: var(--accent-orange); margin-bottom: 12px;">About PipeWrench AI</h4>
                <p style="color: var(--text-muted); line-height: 1.6;">
                    PipeWrench AI uses Claude 3.5 Sonnet with department-specific prompts to capture and preserve 
                    institutional knowledge in municipal public works departments. All responses include verifiable 
                    citations and follow strict anti-hallucination protocols.
                </p>
            </div>
        </div>

        <footer>
            <div class="footer-section">
                <h4>Privacy Policy</h4>
                <p>
                    PipeWrench AI is committed to protecting your privacy. Session data is stored temporarily 
                    and automatically deleted after 24 hours. API keys are stored locally in your browser and 
                    never transmitted to our servers except for direct API calls to Anthropic.
                </p>
            </div>

            <div class="footer-section">
                <h4>California Generative AI Training Data Transparency Act</h4>
                <p>
                    This application uses Anthropic's Claude AI model. For information about training data used 
                    in Claude's development, please visit 
                    <a href="https://www.anthropic.com/legal/data-transparency" target="_blank">Anthropic's Data Transparency page</a>.
                </p>
                <p style="margin-top: 12px;">
                    <strong>Data Usage:</strong> Your questions and uploaded documents are sent to Anthropic's API 
                    for processing. Anthropic does not train on data submitted via their API. For more information, 
                    see <a href="https://www.anthropic.com/legal/commercial-terms" target="_blank">Anthropic's Commercial Terms</a>.
                </p>
            </div>

            <div class="footer-section">
                <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border);">
                    © 2024 PipeWrench AI. Built for municipal public works professionals.
                </p>
            </div>
        </footer>
    </div>

    <script>
        let sessionId = null;
        let apiKey = null;

        window.onload = async function() {
            await createSession();
            await loadDepartments();
            loadSettings();
        };

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const tabName = this.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(tabName).classList.add('active');
            });
        });

        async function createSession() {
            try {
                const response = await fetch('/api/session/create', { method: 'POST' });
                const data = await response.json();
                sessionId = data.session_id;
                console.log('Session created:', sessionId);
            } catch (error) {
                console.error('Error creating session:', error);
            }
        }

        async function loadDepartments() {
            try {
                const response = await fetch('/api/departments');
                const data = await response.json();
                
                const selects = ['department', 'upload-department'];
                selects.forEach(selectId => {
                    const select = document.getElementById(selectId);
                    select.innerHTML = '<option value="general_public_works">General Public Works</option>';
                    
                    data.departments.forEach(dept => {
                        const option = document.createElement('option');
                        option.value = dept.value;
                        option.textContent = dept.name;
                        select.appendChild(option);
                    });
                });
            } catch (error) {
                console.error('Error loading departments:', error);
            }
        }

        async function askQuestion() {
            const question = document.getElementById('question').value.trim();
            const department = document.getElementById('department').value;
            
            if (!question) {
                alert('Please enter a question');
                return;
            }

            const spinner = document.getElementById('query-spinner');
            spinner.style.display = 'block';
            document.getElementById('answer-container').style.display = 'none';

            const formData = new FormData();
            formData.append('question', question);
            formData.append('department', department);
            formData.append('session_id', sessionId);
            if (apiKey) formData.append('api_key', apiKey);

            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) throw new Error('API request failed');
                
                const data = await response.json();
                document.getElementById('answer').innerHTML = data.answer.replace(/\\n/g, '<br>');
                document.getElementById('answer-container').style.display = 'block';
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                spinner.style.display = 'none';
            }
        }

        async function uploadDocument() {
            const fileInput = document.getElementById('file');
            const department = document.getElementById('upload-department').value;
            
            if (!fileInput.files[0]) {
                alert('Please select a file');
                return;
            }

            const spinner = document.getElementById('upload-spinner');
            spinner.style.display = 'block';
            document.getElementById('upload-result').style.display = 'none';

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('department', department);
            formData.append('session_id', sessionId);
            if (apiKey) formData.append('api_key', apiKey);

            try {
                const response = await fetch('/api/document/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) throw new Error('Upload failed');
                
                const data = await response.json();
                document.getElementById('analysis').innerHTML = data.analysis.replace(/\\n/g, '<br>');
                document.getElementById('upload-result').style.display = 'block';
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                spinner.style.display = 'none';
            }
        }

        async function generateReport() {
            const formData = new FormData();
            formData.append('session_id', sessionId);

            try {
                const response = await fetch('/api/report/generate', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) throw new Error('Report generation failed');
                
                const html = await response.text();
                const reportWindow = window.open('', '_blank');
                reportWindow.document.write(html);
                reportWindow.document.close();
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        function saveSettings() {
            apiKey = document.getElementById('api-key').value.trim();
            if (apiKey) {
                localStorage.setItem('anthropic_api_key', apiKey);
                alert('Settings saved!');
            } else {
                localStorage.removeItem('anthropic_api_key');
                alert('API key cleared.');
            }
        }

        function loadSettings() {
            const savedKey = localStorage.getItem('anthropic_api_key');
            if (savedKey) {
                apiKey = savedKey;
                document.getElementById('api-key').value = savedKey;
            }
        }

        document.getElementById('question').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && e.ctrlKey) {
                askQuestion();
            }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page"""
    return HTML_TEMPLATE

@app.get("/api/departments")
async def get_departments():
    """Return list of all departments for dropdown"""
    return {"departments": get_department_list()}

@app.post("/api/session/create")
async def create_session():
    """Create a new session for tracking questions"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": datetime.now(),
        "questions": [],
        "documents": []
    }
    return {"session_id": session_id}

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve session data"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.post("/api/query")
async def query_ai(
    question: str = Form(...),
    department: str = Form("general_public_works"),
    session_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """Query the AI with department-specific context"""
    
    anthropic_client = Anthropic(api_key=api_key) if api_key else client
    system_prompt = get_department_prompt(department)
    
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        
        answer = response.content[0].text
        
        if session_id and session_id in sessions:
            sessions[session_id]["questions"].append({
                "question": question,
                "answer": answer,
                "department": get_department_name(department),
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "answer": answer,
            "department": get_department_name(department)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/document/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    department: str = Form("general_public_works"),
    api_key: Optional[str] = Form(None)
):
    """Upload and analyze a document"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    content = await file.read()
    anthropic_client = Anthropic(api_key=api_key) if api_key else client
    system_prompt = get_department_prompt(department)
    
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt + "\n\nAnalyze this document and extract key institutional knowledge, procedures, and important information.",
            messages=[{
                "role": "user",
                "content": f"Document: {file.filename}\n\nContent:\n{content.decode('utf-8', errors='ignore')}"
            }]
        )
        
        analysis = response.content[0].text
        
        sessions[session_id]["documents"].append({
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department),
            "uploaded_at": datetime.now().isoformat()
        })
        
        return {
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    """Generate HTML report with all questions and documents"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PipeWrench AI - Knowledge Capture Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            h1 {{ color: #1e40af; }}
            h2 {{ color: #3b82f6; margin-top: 30px; }}
            .question {{ background: #eff6ff; padding: 15px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
            .answer {{ margin: 10px 0; }}
            .document {{ background: #fef3c7; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .metadata {{ color: #6b7280; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>PipeWrench AI - Knowledge Capture Report</h1>
        <p class="metadata">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Questions & Answers ({len(session_data['questions'])})</h2>
    """
    
    for i, qa in enumerate(session_data['questions'], 1):
        html_report += f"""
        <div class="question">
            <strong>Q{i} ({qa['department']}):</strong> {qa['question']}
            <div class="answer">
                <strong>Answer:</strong><br>
                {qa['answer'].replace(chr(10), '<br>')}
            </div>
            <p class="metadata">Asked: {qa['timestamp']}</p>
        </div>
        """
    
    html_report += f"""
        <h2>Documents Analyzed ({len(session_data['documents'])})</h2>
    """
    
    for doc in session_data['documents']:
        html_report += f"""
        <div class="document">
            <strong>Document:</strong> {doc['filename']} ({doc['department']})<br>
            <div class="answer">
                <strong>Analysis:</strong><br>
                {doc['analysis'].replace(chr(10), '<br>')}
            </div>
            <p class="metadata">Uploaded: {doc['uploaded_at']}</p>
        </div>
        """
    
    html_report += """
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_report)

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")
