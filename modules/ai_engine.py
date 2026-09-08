import os
import google.generativeai as genai


class AIEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        # Configure Gemini
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

    def call_gemini(self, prompt, model_name="gemini-2.5-flash"):
        if not self.gemini_key:
            raise Exception("Gemini API Key not found")

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text

    def generate_response(self, prompt):
        """
        Uses Gemini (primary)
        """
        print("AI Engine: Using Gemini...")

        try:
            return self.call_gemini(prompt)
        except Exception as e:
            print(f"AI Engine: Gemini failed. Error: {e}")

        return "[AI System Message]: AI is currently unavailable. Check API key or internet."


ai_engine = AIEngine()
