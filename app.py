from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from db_setup import db, User, StickyNote, CalendarEvent, SavedRoadmap, QuizResult, LearningHistory
from modules.ai_engine import ai_engine
import os
import socket
from datetime import datetime, timedelta


def get_available_port(start_port=5003, end_port=5100):
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f'No free port found in range {start_port}-{end_port}')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')

database_url = os.getenv('DATABASE_URL')
if database_url:
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///learning_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from werkzeug.security import generate_password_hash, check_password_hash
from modules.auth_start import get_auth_help
from flask import jsonify

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Please check your login details and try again.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/auth-help', methods=['POST'])
def auth_help():
    data = request.json
    query = data.get('query')
    response = get_auth_help(query)
    return jsonify({'answer': response})

from modules.recommendation import get_recommendations

@app.route('/dashboard')
@login_required
def dashboard():
    # 1. Active Courses (Saved Roadmaps)
    active_courses = SavedRoadmap.query.filter_by(user_id=current_user.id).count()

    # 2. Quizzes Passed (>60%)
    quizzes_passed = QuizResult.query.filter_by(user_id=current_user.id).filter(QuizResult.score >= 60).count()

    # 3. Learning Hours (Estimate)
    # 20m per Quiz, 5m per Chat, 10m per Note/Roadmap
    quiz_count = QuizResult.query.filter_by(user_id=current_user.id).count()
    note_count = StickyNote.query.filter_by(user_id=current_user.id).count()
    chat_count = ChatMessage.query.filter_by(user_id=current_user.id, role='user').count()

    total_minutes = (quiz_count * 20) + (note_count * 10) + (chat_count * 5) + (active_courses * 30)
    learning_hours = round(total_minutes / 60, 1)

    # 4. Day Streak
    # Get distinct dates from LearningHistory & QuizResult
    history_dates = db.session.query(db.func.date(LearningHistory.date_accessed)).filter_by(user_id=current_user.id).all()
    quiz_dates = db.session.query(db.func.date(QuizResult.date_taken)).filter_by(user_id=current_user.id).all()

    # Flatten and unique
    all_dates = set([d[0] for d in history_dates] + [d[0] for d in quiz_dates])

    # Calculate Streak
    streak = 0
    today = datetime.utcnow().date()

    # Simple check for today/yesterday backwards
    # Convert strings 'YYYY-MM-DD' back to date objects if needed, depends on sqlite return
    # SQLite often returns strings. unique dates are likely strings.

    sorted_dates = sorted(all_dates, reverse=True)
    if not sorted_dates:
        streak = 0
    else:
        # Check if today or yesterday is present
        # Normalize today to string
        today_str = today.strftime('%Y-%m-%d')
        yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')

        current_check = today_str
        if today_str not in sorted_dates:
            if yesterday_str in sorted_dates:
                current_check = yesterday_str
            else:
                streak = 0 # Streak broken
                current_check = None

        if current_check:
            streak = 1
            check_date = datetime.strptime(current_check, '%Y-%m-%d').date()

            # Iterate backwards
            while True:
                check_date = check_date - timedelta(days=1)
                check_str = check_date.strftime('%Y-%m-%d')
                if check_str in sorted_dates:
                    streak += 1
                else:
                    break

    stats = {
        'active_courses': active_courses,
        'quizzes_passed': quizzes_passed,
        'learning_hours': learning_hours,
        'streak': streak
    }

    recommendations = get_recommendations(current_user)
    return render_template('dashboard.html', name=current_user.username, recommendations=recommendations, stats=stats)


from modules.chatbot_logic import get_chatbot_response

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')


# Quiz Routes
from modules.quiz_engine import generate_quiz, evaluate_quiz
import json

@app.route('/quiz', methods=['GET'])
@login_required
def quiz_setup():
    history = QuizResult.query.filter_by(user_id=current_user.id).order_by(QuizResult.date_taken.desc()).all()
    return render_template('quiz_setup.html', history=history)

@app.route('/quiz/take', methods=['POST'])
@login_required
def quiz_take():
    course_name = request.form.get('courses') # Using 'courses' based on typical form name, need to verify template.
    if not course_name:
        course_name = request.form.get('course_name') # Fallback

    difficulty = request.form.get('difficulty')
    num_questions = request.form.get('num_questions')

    questions = generate_quiz(course_name, difficulty, num_questions)
    questions_json = json.dumps(questions)

    return render_template('quiz_take.html', questions=questions, questions_json=questions_json, course_name=course_name)

@app.route('/quiz/submit', methods=['POST'])
@login_required
def quiz_submit():
    questions_json = request.form.get('questions_data')
    questions = json.loads(questions_json)

    # Extract answers from form. Form keys are "q1", "q2", etc. or just "1", "2"?
    # Typically <input name="{{ q.id }}">
    user_answers = {}
    for q in questions:
        qid = str(q['id'])
        user_answers[qid] = request.form.get(qid)

    result = evaluate_quiz(questions, user_answers)

    # Save Result
    # Store full details: Questions, User Answers, Feedback
    details_data = {
        "questions": questions,
        "user_answers": user_answers,
        "feedback": result.get('ai_feedback'),
        "analysis": result.get('details')
    }

    new_result = QuizResult(
        user_id=current_user.id,
        topic=request.form.get('topic') or questions[0].get('topic', 'General Knowledge'),
        score=result['score'],
        total_questions=result['total'],
        details_json=json.dumps(details_data)
    )
    db.session.add(new_result)
    db.session.commit()

    return render_template('quiz_result.html', result=result)

@app.route('/quiz/view/<int:result_id>')
@login_required
def quiz_view(result_id):
    quiz = QuizResult.query.get_or_404(result_id)
    if quiz.user_id != current_user.id:
        return redirect(url_for('quiz_setup'))

    if quiz.details_json:
        data = json.loads(quiz.details_json)
        # Reconstruct result object for template
        result = {
            "score": quiz.score,
            "total": quiz.total_questions,
            "score_percentage": int((quiz.score / quiz.total_questions) * 100) if quiz.total_questions > 0 else 0,
            "ai_feedback": data.get('feedback', 'No feedback stored.'),
            "details": data.get('analysis', [])
        }
        return render_template('quiz_result.html', result=result, is_history=True)
    else:
        # Fallback for old records
        flash("Detailed history not available for this old quiz.", "info")
        return redirect(url_for('quiz_setup'))

@app.route('/resume', methods=['GET'])
@login_required
def resume_upload():
    return render_template('resume_upload.html')

from modules.resume_parser import analyze_resume, extract_text_from_pdf, extract_text_from_docx
import os
from werkzeug.utils import secure_filename

@app.route('/resume/analyze', methods=['POST'])
@login_required
def resume_analyze():
    target_role = request.form.get('target_role')
    level = request.form.get('level')

    resume_text = ""

    if 'resume_file' in request.files:
        file = request.files['resume_file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.root_path, 'instance', filename) # Temp save
            # Ensure instance dir exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file.save(file_path)

            if filename.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(file_path)
            elif filename.lower().endswith('.docx') or filename.lower().endswith('.doc'):
                resume_text = extract_text_from_docx(file_path)
            else:
                resume_text = "Unsupported file format."

            # Clean up
            try:
                os.remove(file_path)
            except:
                pass

    if not resume_text or len(resume_text) < 10:
        flash("Could not extract text from the uploaded file.", "error")
        return redirect(url_for('resume_upload'))

    # Cache for other tools
    session['resume_text'] = resume_text
    session['target_role'] = target_role # Also useful

    result = analyze_resume(resume_text, target_role, level)

    # Log Activity with Score
    score = result['ats'].get('score', 0)
    log = LearningHistory(user_id=current_user.id, topic=f"Resume Analysis: {target_role} (Score: {score})", score=score)
    db.session.add(log)
    db.session.commit()

    return render_template('resume_result.html', result=result)

from modules.resume_parser import generate_better_bullets, generate_cover_letter, generate_rewrite_suggestions, create_cover_letter_docx

@app.route('/resume/rewrite_bullet', methods=['POST'])
@login_required
def api_rewrite_bullet():
    # Keep this for backward compatibility or single-use if needed
    data = request.json
    bullet = data.get('bullet')
    role = data.get('role') or session.get('target_role') or "General Professional"
    variations = generate_better_bullets(bullet, role)
    return jsonify({"variations": variations})

@app.route('/resume/full_rewrite', methods=['POST'])
@login_required
def api_full_rewrite():
    role = session.get('target_role') or "General Professional"
    resume_text = session.get('resume_text')
    if not resume_text:
        return jsonify({"error": "No resume found"}), 400

    suggestions = generate_rewrite_suggestions(resume_text, role)
    return jsonify({"suggestions": suggestions})

@app.route('/resume/cover_letter', methods=['POST'])
@login_required
def api_cover_letter():
    data = request.json
    jd = data.get('jd')
    resume_text = session.get('resume_text')

    if not resume_text:
        return jsonify({"error": "No resume found. Please upload resume first."}), 400

    letter = generate_cover_letter(resume_text, jd)
    return jsonify({"letter": letter})

@app.route('/resume/download_cover_letter', methods=['POST'])
@login_required
def download_cover_letter():
    letter_text = request.form.get('letter_text')
    if not letter_text:
         return redirect(url_for('resume_upload'))

    # Create Docx
    file_path = create_cover_letter_docx(letter_text, filename=f"Cover_Letter_{current_user.id}.docx")

    return send_file(file_path, as_attachment=True, download_name="Cover_Letter.docx")

# Path Generator Routes
from modules.path_generator import generate_learning_path, create_word_doc
from flask import send_file

@app.route('/learning-path', methods=['GET', 'POST'])
@login_required
def learning_path_form():
    if request.method == 'POST':
        data = {
            'course_name': request.form.get('course_name'),
            'current_skills': request.form.get('current_skills'),
            'duration': request.form.get('duration'),
            'level': request.form.get('level')
        }
        roadmap_json = generate_learning_path(data)

        # Save to DB (Persist the full object including metadata)
        full_save_data = {
            'roadmap': roadmap_json,
            'meta': data
        }

        new_roadmap = SavedRoadmap(
            user_id=current_user.id,
            title=data['course_name'],
            roadmap_json=json.dumps(full_save_data)
        )
        db.session.add(new_roadmap)

        # Also Log Activity
        log = LearningHistory(user_id=current_user.id, topic=f"Generated Path: {data['course_name']}", score=0)
        db.session.add(log)
        db.session.commit()

        # Serialize for hidden input
        roadmap_str = json.dumps(roadmap_json)

        return render_template('learning_path_result.html',
                               roadmap=roadmap_json,
                               roadmap_str=roadmap_str,
                               course_name=data['course_name'],
                               level=data['level'],
                               duration=data['duration'])

    # GET: Fetch User History
    history = SavedRoadmap.query.filter_by(user_id=current_user.id).order_by(SavedRoadmap.created_at.desc()).all()
    return render_template('learning_path_form.html', history=history)

@app.route('/learning-path/view/<int:roadmap_id>')
@login_required
def learning_path_view(roadmap_id):
    saved = SavedRoadmap.query.get_or_404(roadmap_id)
    if saved.user_id != current_user.id:
        return redirect(url_for('learning_path_form'))

    # wrapper dict with 'roadmap' and 'meta'
    full_data = json.loads(saved.roadmap_json)

    roadmap = full_data.get('roadmap')
    meta = full_data.get('meta', {})

    # Re-serialize for download using the inner roadmap object
    roadmap_str = json.dumps(roadmap)

    return render_template('learning_path_result.html',
                           roadmap=roadmap,
                           roadmap_str=roadmap_str,
                           course_name=saved.title,
                           level=meta.get('level', 'N/A'),
                           duration=meta.get('duration', 'N/A'))

# Analytics API
from sqlalchemy import func
from datetime import timedelta

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    # 1. Chart Data: Activity over last 7 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=6)

    # Initialize dictionary for last 7 days
    daily_counts = {}
    for i in range(7):
        day_str = (start_date + timedelta(days=i)).strftime('%a') # Mon, Tue...
        daily_counts[day_str] = 0

    # Query Quiz Results
    quiz_activity = db.session.query(func.date(QuizResult.date_taken), func.count(QuizResult.id))\
        .filter(QuizResult.user_id == current_user.id, QuizResult.date_taken >= start_date)\
        .group_by(func.date(QuizResult.date_taken)).all()

    for date_str, count in quiz_activity:
        # date_str might be string or obj depending on DB adapter, SQLite returns string YYYY-MM-DD
        d = datetime.strptime(date_str, '%Y-%m-%d')
        daily_counts[d.strftime('%a')] += count

    # Query Learning History
    learn_activity = db.session.query(func.date(LearningHistory.date_accessed), func.count(LearningHistory.id))\
        .filter(LearningHistory.user_id == current_user.id, LearningHistory.date_accessed >= start_date)\
        .group_by(func.date(LearningHistory.date_accessed)).all()

    for date_str, count in learn_activity:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        daily_counts[d.strftime('%a')] += count

    chart_labels = list(daily_counts.keys())
    chart_data = list(daily_counts.values())

    # 2. Recent Timeline (Combine Quiz + Learning + Notes)
    timeline = []

    quizzes = QuizResult.query.filter_by(user_id=current_user.id).order_by(QuizResult.date_taken.desc()).limit(5).all()
    for q in quizzes:
        timeline.append({
            'type': 'quiz',
            'title': f"Completed Quiz: {q.topic}",
            'desc': f"Score: {q.score}/{q.total_questions}",
            'time': q.date_taken,
            'color': 'purple'
        })

    history = LearningHistory.query.filter_by(user_id=current_user.id).order_by(LearningHistory.date_accessed.desc()).limit(5).all()
    for h in history:
        timeline.append({
            'type': 'learning',
            'title': h.topic,
            'desc': 'Learning Activity',
            'time': h.date_accessed,
            'color': 'blue'
        })

    # Sort combined timeline
    timeline.sort(key=lambda x: x['time'], reverse=True)

    # Format time for JSON
    final_timeline = []
    for item in timeline[:5]: # Top 5
        # Calculate human readable time diff locally or just string
        item['time_str'] = item['time'].strftime("%Y-%m-%d %H:%M")
        del item['time'] # remove obj to make serializable
        final_timeline.append(item)

    return jsonify({
        'chart': {'labels': chart_labels, 'data': chart_data},
        'timeline': final_timeline
    })

@app.route('/download-path', methods=['POST'])
@login_required
def download_path():
    course_name = request.form.get('course_name')
    roadmap_str = request.form.get('roadmap_str')

    # Parse back to dict
    try:
        roadmap_data = json.loads(roadmap_str)
    except:
        roadmap_data = roadmap_str # Fallback

    file_stream = create_word_doc(roadmap_data, course_name)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=f'{course_name}_Roadmap.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


# Sticky Notes Routes
@app.route('/api/notes', methods=['GET', 'POST'])
@login_required
def notes_api():
    if request.method == 'GET':
        notes = StickyNote.query.filter_by(user_id=current_user.id).order_by(StickyNote.created_at.desc()).all()
        return jsonify([{'id': n.id, 'content': n.content, 'is_completed': n.is_completed} for n in notes])
    elif request.method == 'POST':
        data = request.json
        new_note = StickyNote(user_id=current_user.id, content=data.get('content'))
        db.session.add(new_note)
        db.session.commit()
        return jsonify({'message': 'Note added', 'id': new_note.id})

@app.route('/api/notes/<int:note_id>', methods=['PUT', 'DELETE'])
@login_required
def note_action(note_id):
    note = StickyNote.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'PUT':
        note.is_completed = not note.is_completed
        db.session.commit()
        return jsonify({'message': 'Note updated'})
    elif request.method == 'DELETE':
        db.session.delete(note)
        db.session.commit()
        return jsonify({'message': 'Note deleted'})

# Calendar Routes
@app.route('/api/events', methods=['GET', 'POST'])
@login_required
def events_api():
    if request.method == 'GET':
        events = CalendarEvent.query.filter_by(user_id=current_user.id).all()
        return jsonify([{'id': e.id, 'title': e.title, 'start': e.event_date} for e in events])
    elif request.method == 'POST':
        data = request.json
        new_event = CalendarEvent(user_id=current_user.id, title=data.get('title'), event_date=data.get('date'))
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'message': 'Event added', 'id': new_event.id})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    event = CalendarEvent.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(event)
    db.session.commit()
    return jsonify({'message': 'Event deleted'})

from flask_socketio import SocketIO, emit, join_room
from db_setup import ChatMessage

socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

with app.app_context():
    db.create_all()

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    if current_user.is_authenticated:
        print(f"User authenticated: {current_user.id}")
        join_room(f"user_{current_user.id}")
        # Send recent history
        with app.app_context():
            recent_msgs = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.asc()).all()[-50:]
            history = [{'role': m.role, 'content': m.content} for m in recent_msgs]
            emit('history_loaded', {'history': history})
    else:
        print("User NOT authenticated during connect")

@app.route('/chat/message', methods=['POST'])
@login_required
def chat_message_api():
    """
    Faster, Direct HTTP Chat Endpoint.
    Replaces SocketIO for message sending to reduce overhead.
    """
    data = request.json
    question = data.get('question')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # 1. Save User Message
    user_msg = ChatMessage(user_id=current_user.id, role='user', content=question)
    db.session.add(user_msg)
    db.session.commit()

    # 2. Get Context
    recent_msgs = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.asc()).all()[-5:]
    history = [{'role': m.role, 'content': m.content} for m in recent_msgs]

    # 3. Generate Response (Direct Call)
    # Using the optimized chatbot_logic
    response_text = get_chatbot_response(question, history)

    # 4. Save AI Response
    ai_msg = ChatMessage(user_id=current_user.id, role='ai', content=response_text)
    db.session.add(ai_msg)
    db.session.commit()

    return jsonify({"answer": response_text})


if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    preferred_port = os.getenv('PORT')
    port = int(preferred_port) if preferred_port else get_available_port()

    with app.app_context():
        db.create_all()

    print(f"Starting SocketIO server on {host}:{port}...")
    print(f"Open this in your browser: http://{host}:{port}/")
    socketio.run(app, host=host, port=port, debug=False)



