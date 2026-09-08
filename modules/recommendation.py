from .ai_engine import ai_engine
import json
from db_setup import QuizResult

def get_recommendations(user):
    # Fetch recent quiz performance
    recent_quizzes = QuizResult.query.filter_by(user_id=user.id).order_by(QuizResult.date_taken.desc()).limit(5).all()
    
    quiz_summary = []
    if recent_quizzes:
        for q in recent_quizzes:
            quiz_summary.append(f"Topic: {q.topic}, Score: {q.score}%")
    else:
        quiz_summary.append("No quizzes taken yet.")

    user_data_str = f"""
    User Interest: {user.interests or 'General Technology'}
    Recent Activity: {"; ".join(quiz_summary)}
    """

    prompt = f"""
    You are an AI Learning Mentor.
    User Profile:
    {user_data_str}

    Task: Recommend 3 specific "Next Topics" to learn based on their interests and recent performance (especially if scores are low).
    
    Format: Return ONLY a JSON object with this key: "next_topics": ["Topic 1", "Topic 2", "Topic 3"].
    Do not add markdown formatting.
    """
    
    try:
        response_text = ai_engine.generate_response(prompt)
        # Clean response if AI adds markdown
        # Find start and end of JSON content
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            clean_json = response_text[json_start:json_end]
            data = json.loads(clean_json)
            return data
        else:
             # Fallback
             data = json.loads(response_text.replace('```json', '').replace('```', '').strip())
             return data
    except Exception as e:
        print(f"Start Rec Error: {e}")
        # Fallback
        return {
            "next_topics": ["Python Fundamentals", "Data Science 101", "Web Development Basics"], 
            "revision_topics": [], 
            "learning_domains": []
        }
