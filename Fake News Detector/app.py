from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import CrossEncoder
import numpy as np

app = Flask(__name__)
CORS(app)

# Load model ONCE (important)
model = CrossEncoder("D:\Sbert")

label_mapping = ['contradiction', 'entailment', 'neutral']


def ai_check(text):
    # Hypotheses (this is the key trick)
    hypotheses = [
        "This text is fake news.",
        "This text is real news."
    ]

    # Create sentence pairs
    pairs = [(text, h) for h in hypotheses]

    # Get scores
    scores = model.predict(pairs)
    scores = np.array(scores)

    # Convert logits → probabilities (softmax)
    probs = np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)

    # Extract entailment probability
    entailment_scores = probs[:, 1]  # index 1 = entailment

    fake_score = entailment_scores[0]
    real_score = entailment_scores[1]

    if fake_score > real_score:
        verdict = "Likely Fake News"
        confidence = float(fake_score)
    else:
        verdict = "Likely Real News"
        confidence = float(real_score)

    return {
        "verdict": verdict,
        "confidence": round(confidence * 100, 2),
        "details": f"Fake score: {fake_score:.3f}, Real score: {real_score:.3f}",
        "checked_text": text[:100] + ("..." if len(text) > 100 else "")
    }


@app.route('/check', methods=['POST'])
def check_text():
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = ai_check(text)
    return jsonify(result)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "API is running"})


if __name__ == '__main__':
    print("Starting AI Fake News Detector on http://localhost:5000")
    app.run(debug=True, port=5000)
