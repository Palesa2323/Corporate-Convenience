
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key was not found.")

client = genai.Client(api_key=api_key)

print("\nModels supporting text generation:\n")

for model in client.models.list():
    supported_actions = model.supported_actions or []

    if "generateContent" in supported_actions:
        print(f"Model: {model.name}")
        print(f"Display name: {model.display_name}")
        print("-" * 40)
