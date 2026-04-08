from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def predict(text):
    if "shocking" in text.lower():
        return {
            "label": "FAKE",
            "confidence": 0.7,
            "explanation": "Sensational wording detected"
        }
    return {
        "label": "REAL",
        "confidence": 0.6,
        "explanation": "No obvious issues"
    }

@app.route("/predict", methods=["POST"])
def predict_api():
    data = request.json
    text = data.get("text", "")
    result = predict(text)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)