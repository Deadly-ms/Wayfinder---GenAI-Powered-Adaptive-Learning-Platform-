from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()  # Ensure tables exist
    # Check if user exists
    user = User.query.filter_by(email='test@example.com').first()
    if not user:
        new_user = User(
            username='DemoUser', 
            email='test@example.com', 
            password=generate_password_hash('password123'),
            interests='Artificial Intelligence, Web Development',
            current_skills='Python (Basic), HTML',
            learning_style='Visual'
        )
        db.session.add(new_user)
        db.session.commit()
        print("Test user created.")
    else:
        print("Test user already exists.")
