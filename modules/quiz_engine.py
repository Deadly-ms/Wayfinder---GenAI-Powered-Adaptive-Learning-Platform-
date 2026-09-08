from .ai_engine import ai_engine
import json
import re

def generate_quiz(course_name, difficulty, num_questions):
    # Prompt 6: Smart Quiz & Assessment – Question Generation Prompt
    base_prompt = """
    You are an AI Quiz Generator.

    User Inputs:
    - Topic: {course_name}
    - Difficulty: {difficulty}
    - Count: {num_questions}

    Tasks:
    - Generate {num_questions} multiple-choice questions (MCQs).
    - Ensure questions are relevant to the topic and difficulty.
    - Provide 4 options for each question.
    - Clearly indicate the correct answer (exact option text).
    - Provide a brief explanation for why the answer is correct.

    Output Format:
    Return valid JSON (array of objects) ONLY. No markdown.
    [
        {{
            "id": 1, 
            "question": "Question text...", 
            "options": ["Option A", "Option B", "Option C", "Option D"], 
            "correct_answer": "Option A",
            "explanation": "Because..."
        }},
        ...
    ]
    """
    
    prompt = base_prompt.format(course_name=course_name, difficulty=difficulty, num_questions=num_questions)
    
    raw_response = ai_engine.generate_response(prompt)
    
    try:
        # Find start and end of JSON list
        json_start = raw_response.find('[')
        json_end = raw_response.rfind(']') + 1
        
        if json_start != -1 and json_end != -1:
            clean_json = raw_response[json_start:json_end]
            questions = json.loads(clean_json)
        else:
            raise Exception("No JSON array found in response")
        # Ensure ID generation if missing
        for idx, q in enumerate(questions):
            q['id'] = idx + 1
        return questions
    except Exception as e:
        print(f"Quiz Generation Error: {e}")
        # Fallback Mock
        return [
            {"id": 1, "question": f"Failed to generate real quiz for {course_name}. (Error: {str(e)})", "options": ["Retry"], "correct_answer": "Retry", "explanation": "AI Error"}
        ]

def evaluate_quiz(questions, user_answers):
    # 1. Calculate Score Locally
    score = 0
    total = len(questions)
    results_detailed = []
    
    for q in questions:
        # User answer might be distinct based on form (e.g. "Option A")
        # Ensure we compare correctly. 
        selected = user_answers.get(str(q['id']))
        is_correct = (selected == q['correct_answer'])
        
        if is_correct:
            score += 1
            
        results_detailed.append({
            "id": q['id'],
            "question": q['question'],
            "selected": selected,
            "correct_answer": q['correct_answer'],
            "is_correct": is_correct,
            "explanation": q.get('explanation', 'No explanation provided.')
        })
        
    # 2. Generate AI Feedback for Weak Areas
    weak_areas_prompt = """
    You are an AI Tutor. A student just took a quiz on {topic}.
    Score: {score}/{total}
    
    Mistakes made:
    {mistakes}
    
    Provide a brief, encouraging feedback summary:
    1. Identify weak areas based on the mistakes.
    2. Suggest 2-3 specific tips to improve.
    3. Keep it under 150 words.
    """
    
    mistakes_text = "\n".join([f"- Q: {r['question']}\n  Expected: {r['correct_answer']}\n  Selected: {r['selected']}" for r in results_detailed if not r['is_correct']])
    
    if not mistakes_text and score == total:
        mistakes_text = "None! Perfect score."
        
    feedback_prompt = weak_areas_prompt.format(
        topic=questions[0].get('topic', 'General'), # Fallback topic
        score=score,
        total=total,
        mistakes=mistakes_text
    )
    
    ai_feedback = ai_engine.generate_response(feedback_prompt)
    
    return {
        "score": score,
        "total": total,
        "score_percentage": int((score/total)*100),
        "ai_feedback": ai_feedback,
        "details": results_detailed
    }
