
"""Corporate Convenience - Member 3: Flask backend."""

from flask import Flask, jsonify, request
from classifier import predict_department

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    """Check that the API is running."""
    return jsonify({
        "message": "Corporate Convenience API is running."
    }), 200


@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    """Classify a ticket and return its details."""
    data = request.get_json(silent=True) or {}
    message = data.get("message")

    if not isinstance(message, str) or not message.strip():
        return jsonify({
            "error": "Please provide a valid ticket message."
        }), 400

    try:
        department = predict_department(message)

        return jsonify({
            "ticket_id": None,
            "message": message.strip(),
            "department": department,
            "status": "Open"
        }), 200

    except FileNotFoundError:
        return jsonify({
            "error": "The trained model is not available yet."
        }), 503

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Ticket classification failed.")
        return jsonify({
            "error": "An unexpected server error occurred."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
