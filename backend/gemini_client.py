
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()


def generate_test_response():
    """Test Gemini using the recommended Interactions API."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini API key was not found.")

    client = genai.Client(api_key=api_key)

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=(
            "Write a short, professional greeting for "
            "a workplace support system."
        ),
        store=False
    )

    if not interaction.output_text:
        raise RuntimeError("Gemini returned an empty response.")

    return interaction.output_text


if __name__ == "__main__":
    try:
        result = generate_test_response()

        print("\nGemini connection successful!")
        print("Generated response:")
        print(result)

    except Exception as error:
        print("\nGemini connection failed.")
        print(f"Error: {error}")
