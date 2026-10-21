
from functools import lru_cache
from pathlib import Path

import joblib


# Locate the trained model relative to this file.
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.joblib"


@lru_cache(maxsize=1)
def load_model():
    """Load the trained classification model once."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at: {MODEL_PATH}. "
            "Run train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def predict_department(message: str) -> str:
    """Predict the department responsible for a request."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Please enter a workplace request.")

    model = load_model()
    prediction = model.predict([message.strip()])

    return str(prediction[0])
