"""Local-only HTTP report receiver, storing the most recent CI execution as JSON."""
import json
import os
import tempfile
from pathlib import Path
from flask import Flask, jsonify, request

app = Flask(__name__)
DESTINATION = Path(os.environ.get("REPORT_FILE", str(Path(__file__).with_name("test-report.json"))))
TOKEN = os.environ.get("REPORT_TOKEN", "")

@app.get("/health")
def health():
    return jsonify(status="ready", file=str(DESTINATION))

@app.post("/report")
def report():
    if TOKEN and request.headers.get("X-Report-Token") != TOKEN:
        return jsonify(error="Unauthorized"), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("tests"), list) or not isinstance(data.get("summary"), dict):
        return jsonify(error="Invalid report JSON"), 400
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replace, so an observer never sees a half-written report.
    handle, staging = tempfile.mkstemp(prefix="report-", suffix=".json", dir=DESTINATION.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(staging, DESTINATION)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)
    return jsonify(saved=True, path=str(DESTINATION)), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("RECEIVER_PORT", 8765)), debug=False)
