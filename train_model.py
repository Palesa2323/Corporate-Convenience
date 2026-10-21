"""
Corporate Convenience — Member 1: Machine-learning model training.

Usage:
    python train_model.py

Input:
    tickets.csv with columns: request_text, department

Output:
    model.joblib (a saved scikit-learn Pipeline containing TF-IDF + Logistic Regression)
"""

from pathlib import Path
import sys

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "tickets.csv"
MODEL_PATH = BASE_DIR / "model.joblib"

REQUIRED_COLUMNS = {"request_text", "department"}
EXPECTED_LABELS = {"HR", "IT", "Finance", "Operations"}


def load_dataset(path: Path) -> pd.DataFrame:
    """Load the CSV and check that it has usable text and valid labels."""
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path.name}. Put tickets.csv beside train_model.py."
        )

    data = pd.read_csv(path)

    missing_columns = REQUIRED_COLUMNS - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing required CSV columns: {sorted(missing_columns)}")

    data = data.dropna(subset=["request_text", "department"]).copy()
    data["request_text"] = data["request_text"].astype(str).str.strip()
    data["department"] = data["department"].astype(str).str.strip()

    data = data[(data["request_text"] != "") & (data["department"] != "")]

    found_labels = set(data["department"].unique())
    unexpected = found_labels - EXPECTED_LABELS
    missing_labels = EXPECTED_LABELS - found_labels

    if unexpected:
        raise ValueError(f"Unexpected department labels: {sorted(unexpected)}")
    if missing_labels:
        raise ValueError(f"Dataset is missing department labels: {sorted(missing_labels)}")

    if data["department"].value_counts().min() < 2:
        raise ValueError("Each department needs at least two examples for a stratified split.")

    return data


def build_pipeline() -> Pipeline:
    """Build the text-processing and classification pipeline."""
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def main() -> int:
    data = load_dataset(DATA_PATH)

    print("Corporate Convenience — Member 1 model training")
    print(f"Total labelled requests: {len(data)}")
    print("\nExamples per department:")
    print(data["department"].value_counts().reindex(sorted(EXPECTED_LABELS), fill_value=0).to_string())

    X_train, X_test, y_train, y_test = train_test_split(
        data["request_text"],
        data["department"],
        test_size=0.25,
        random_state=42,
        stratify=data["department"],
    )

    model = build_pipeline()
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    print(f"\nTraining examples: {len(X_train)}")
    print(f"Testing examples: {len(X_test)}")
    print(f"Held-out test accuracy: {accuracy:.3f}")
    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=sorted(EXPECTED_LABELS),
            zero_division=0,
        )
    )

    print("Confusion matrix (rows = actual, columns = predicted):")
    print(sorted(EXPECTED_LABELS))
    print(confusion_matrix(y_test, predictions, labels=sorted(EXPECTED_LABELS)))

    # Refit the pipeline on all labelled examples for use by the application.
    # The score above remains based on the held-out split.
    model.fit(data["request_text"], data["department"])
    joblib.dump(model, MODEL_PATH)

    print(f"\nSaved trained pipeline to: {MODEL_PATH.name}")
    print("Note: this small demonstration dataset is not sufficient to prove production-level accuracy.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
