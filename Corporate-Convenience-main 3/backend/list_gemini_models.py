import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key was not found.")

client = genai.Client(api_key=api_key)

print("\nModels supporting text generation:\n")

found = False

for model in client.models.list():
    supported_actions = model.supported_actions or []

    if "generateContent" in supported_actions:
        found = True
        # Strip the "models/" prefix so the name can be pasted
        # straight into GEMINI_MODEL in your .env file.
        short_name = model.name.replace("models/", "")
        print(f"Model name (use this): {short_name}")
        print(f"Display name:          {model.display_name}")
        print("-" * 40)

if not found:
    print("No text generation models were returned for this API key.")