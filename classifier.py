
"""Corporate Convenience - Member 3: Ticket classification."""

from pathlib import Path

import joblib

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.joblib"

# Keep the model loaded after the first successful load.
_model = None


def load_model():
    """Load the trained model once and reuse it."""
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "The trained model was not found. "
                "Please run train_model.py first."
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def predict_department(message: str) -> str:
    """Predict the department responsible for a ticket."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Ticket message cannot be empty.")

    model = load_model()
    prediction = model.predict([message.strip()])

    return str(prediction[0])
