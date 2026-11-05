import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Use the same model name as response_generator.py (set GEMINI_MODEL in .env).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_test_response():
    """Check that the API key and model name work."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini API key was not found.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=(
            "Write a short, professional greeting for "
            "a workplace support system."
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text.strip()


if __name__ == "__main__":
    print(f"Testing model: {GEMINI_MODEL}")

    try:
        result = generate_test_response()

        print("\nGemini connection successful!")
        print("Generated response:")
        print(result)

    except Exception as error:
        print("\nGemini connection failed.")
        print(f"Error: {error}")