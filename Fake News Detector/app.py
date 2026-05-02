from flask import Flask, request, jsonify
from flask_cors import CORS
from triplet_extractor import extract_triplets_general, compare_with_kb, add_text_to_kb, get_kb
from apscheduler.schedulers.background import BackgroundScheduler
from crawler import update_knowledge_base
import atexit

scheduler = BackgroundScheduler()
scheduler.add_job(func=update_knowledge_base, trigger="interval", hours=1, id="crawler_job")
scheduler.start()

# Shutdown scheduler when app exits
atexit.register(lambda: scheduler.shutdown())
app = Flask(__name__)
CORS(app)

# ------------------------------------------------------------
# Route 1: Add a text to the knowledge base (extract & store)
# ------------------------------------------------------------
@app.route('/add_text', methods=['POST'])
def add_text():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    added_triplets = add_text_to_kb(text)
    triplets, neg = extract_triplets_general(text)  # all triplets (including duplicates)

    return jsonify({
        "message": f"Added {len(added_triplets)} new triplets to KB",
        "all_triplets_found": triplets,
        "new_triplets_added": added_triplets,
        "total_kb_size": len(get_kb()["triplets"])
    })

# ------------------------------------------------------------
# Route 2: Check a claim against the KB (no storage)
# ------------------------------------------------------------
@app.route('/check', methods=['POST'])
def check_text():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    triplets, neg_triplets = extract_triplets_general(text)
    comparison = compare_with_kb(triplets, neg_triplets)

    if comparison["contradictions"]:
        verdict = "Contradiction Found"
        confidence = min(95, 60 + len(comparison["contradictions"]) * 10)
        details = f"Found {len(comparison['contradictions'])} contradiction(s) with existing facts."
    elif comparison["matches"]:
        verdict = "Supported by Knowledge Base"
        confidence = min(95, 65 + len(comparison["matches"]) * 8)
        details = f"Matches {len(comparison['matches'])} known fact(s)."
    else:
        verdict = "No Information"
        confidence = 30
        details = "No matching or contradicting facts found. Add more texts to KB."

    return jsonify({
        "verdict": verdict,
        "confidence": round(confidence, 1),
        "details": details,
        "triplets_extracted": triplets + [{"negated": nt} for nt in neg_triplets],
        "comparison": comparison,
        "checked_text": text[:200] + ("..." if len(text) > 200 else "")
    })

# Helper endpoints
@app.route('/knowledge_base', methods=['GET'])
def show_kb():
    return jsonify(get_kb())

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "running", "kb_size": len(get_kb()["triplets"])})

def run_crawler_once():
    """Run crawler in a separate thread after a short delay to avoid blocking startup."""
    import threading
    import time
    def delayed_crawl():
        time.sleep(5)  # give Flask a moment to start
        update_knowledge_base()
    threading.Thread(target=delayed_crawl, daemon=True).start()

if __name__ == '__main__':
    run_crawler_once()
    app.run(debug=True, port=5000)
