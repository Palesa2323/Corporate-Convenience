# Corporate Convenience — Smart Ticket Classification Engine

## Member 1: Dataset and Machine Learning

This part of the project prepares labelled employee requests and trains a text classifier for four departments: HR, IT, Finance, and Operations.

## Files

- `tickets.csv` — example labelled ticket requests.
- `train_model.py` — validates the data, trains a TF-IDF + Logistic Regression pipeline, evaluates it on a held-out split, and saves `model.joblib`.
- `model.joblib` — generated when training succeeds; not included by default in this starter package.

## Setup

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run training:

```bash
python train_model.py
```

The script prints a held-out evaluation report and creates `model.joblib`.

## Dataset format

The CSV must contain these columns:

- `request_text`
- `department`

Allowed department labels: `HR`, `IT`, `Finance`, `Operations`.

## Notes

The included dataset contains synthetic example requests for a prototype. Its evaluation results are only an initial check; real-world performance requires a larger, more varied and carefully reviewed dataset.
