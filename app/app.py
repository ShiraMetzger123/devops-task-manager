import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sqlalchemy.exc
import openai

app = Flask(__name__)

# Database configuration
def get_database_uri():
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', 'password')
    db_name = os.getenv('DB_NAME', 'taskmanager')
    
    return f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# OpenAI configuration
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    openai.api_key = openai_api_key
    print("OpenAI API key configured")
else:
    print("WARNING: OPENAI_API_KEY not found. AI suggestions will not work.")

db = SQLAlchemy(app)

def wait_for_db(max_attempts=20):
    """Wait for database to be ready with retry logic"""
    for attempt in range(max_attempts):
        try:
            # Try to connect to the database
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            print("Database connection successful!")
            return
        except sqlalchemy.exc.OperationalError as e:
            print(f"Database not ready (attempt {attempt + 1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                print("Retrying in 3 seconds...")
                time.sleep(3)
            else:
                print("Failed to connect to database after all attempts")
                raise

# Task model
class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default='medium')
    category = db.Column(db.String(50), default='general')
    status = db.Column(db.String(20), default='pending')
    group_name = db.Column(db.String(100), default='default')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

# Routes
@app.route('/')
def home():
    query = Task.query
    
    # Group filter
    current_group = request.args.get('group', 'default')
    query = query.filter(Task.group_name == current_group)
    
    # Search filter
    search_term = request.args.get('q', '').strip()
    if search_term:
        query = query.filter(
            db.or_(
                Task.title.ilike(f'%{search_term}%'),
                Task.description.ilike(f'%{search_term}%')
            )
        )
    
    # Other filters
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    priority_filter = request.args.get('priority')
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    category_filter = request.args.get('category')
    if category_filter:
        query = query.filter(Task.category == category_filter)
    
    tasks = query.all()
    
    # Find tasks due today for notifications
    today = datetime.now().date()
    tasks_due_today = [
        task for task in tasks 
        if task.due_date == today and task.status != 'done'
    ]
    
    return render_template('index.html', tasks=tasks, search_term=search_term, current_group=current_group, tasks_due_today=tasks_due_today)

@app.route('/add', methods=['POST'])
def add_task():
    title = request.form.get('title')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'general')
    group_name = request.form.get('group', 'default')
    
    due_date = None
    if due_date_str:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
    
    task = Task(title=title, description=description, due_date=due_date, priority=priority, category=category, group_name=group_name)
    db.session.add(task)
    db.session.commit()
    
    return redirect(url_for('home', group=group_name))

@app.route('/complete/<int:id>', methods=['POST'])
def complete_task(id):
    task = Task.query.get_or_404(id)
    group_name = task.group_name
    task.status = 'done'
    task.completed_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('home', group=group_name))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_task(id):
    task = Task.query.get_or_404(id)
    group_name = task.group_name
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('home', group=group_name))

@app.route('/api/tasks/suggest', methods=['POST'])
def suggest_task():
    try:
        data = request.get_json()
        title = data.get('title', '')
        description = data.get('description', '')
        
        if not openai_api_key:
            return jsonify({"error": "OpenAI API key not configured"}), 500
        
        # Create OpenAI client
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Prepare prompt
        prompt = f"""Based on this task:
Title: {title}
Description: {description}

Suggest:
1. A better description (if the current one is empty or could be improved)
2. Priority level (high, medium, or low) based on urgency and importance

Respond in this exact format:
Description: [your suggestion]
Priority: [high/medium/low]"""
        
        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful task management assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        # Parse response
        ai_response = response.choices[0].message.content
        lines = ai_response.strip().split('\n')
        
        suggested_description = ""
        suggested_priority = "medium"
        
        for line in lines:
            if line.startswith("Description:"):
                suggested_description = line.replace("Description:", "").strip()
            elif line.startswith("Priority:"):
                priority = line.replace("Priority:", "").strip().lower()
                if priority in ['high', 'medium', 'low']:
                    suggested_priority = priority
        
        return jsonify({
            "suggested_description": suggested_description,
            "suggested_priority": suggested_priority
        })
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return jsonify({"error": "Failed to get AI suggestions"}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/tasks')
def api_tasks():
    query = Task.query
    
    # Group filter
    group_filter = request.args.get('group', 'default')
    query = query.filter(Task.group_name == group_filter)
    
    # Search filter
    search_term = request.args.get('q', '').strip()
    if search_term:
        query = query.filter(
            db.or_(
                Task.title.ilike(f'%{search_term}%'),
                Task.description.ilike(f'%{search_term}%')
            )
        )
    
    # Other filters
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    priority_filter = request.args.get('priority')
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    category_filter = request.args.get('category')
    if category_filter:
        query = query.filter(Task.category == category_filter)
    
    tasks = query.all()
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'priority': task.priority,
        'category': task.category,
        'status': task.status,
        'group_name': task.group_name,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    } for task in tasks])

if __name__ == '__main__':
    with app.app_context():
        wait_for_db()
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)