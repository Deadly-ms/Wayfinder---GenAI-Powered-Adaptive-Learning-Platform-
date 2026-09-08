from .ai_engine import ai_engine

def get_auth_help(user_query):
    # Prompt 1: AI Assistant for Login/Signup
    base_prompt = """
    You are an AI assistant helping users during login and sign-up. 
    Explain sign-up or login steps clearly if the user asks. 
    Keep instructions simple and concise. 
    Do NOT ask for sensitive data like passwords.
    User Query: {query}
    """
    
    prompt = base_prompt.format(query=user_query)
    response = ai_engine.generate_response(prompt)
    return response
