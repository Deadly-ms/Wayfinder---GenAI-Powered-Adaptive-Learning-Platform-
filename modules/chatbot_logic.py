# Optimized Chatbot Logic
from .ai_engine import ai_engine

def get_chatbot_response(user_question, history=[]):
    """
    Fast & Efficient Chatbot Logic.
    Structure: System Prompt + History (Last 3) + User Question.
    """

    # 1. Concise Persona
    system_prompt = """You are an AI Learning Assistant for Wayfinder.
    - Be an encouraging Virtual Tutor.
    - Answer instantly & accurately.
    - Explain complex topics in simple terms (ELI5).
    - Use bolding and lists for readability.
    - If code is asked, use Markdown.
    """

    # 2. Optimized History (Last 3 exchanges only to save tokens/time)
    context = ""
    for msg in history[-3:]:
        role = "User" if msg['role'] == 'user' else "AI"
        context += f"{role}: {msg['content']}\n"

    # 3. Final Prompt
    prompt = f"{system_prompt}\n\nContext:\n{context}\n\nStudent: {user_question}\nTutor:"

    return ai_engine.generate_response(prompt)
