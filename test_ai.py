from dotenv import load_dotenv
load_dotenv()
from modules.ai_engine import ai_engine

print("Testing AI Engine...")
response = ai_engine.generate_response("Hello, are you working?")
print(f"Response: {response}")
