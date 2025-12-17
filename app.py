#!/usr/bin/env python3
import json
import os
import socket
import threading
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from utilities.json_migration_utility import json_migr_util


BASE_DIR = Path(__file__).resolve().parent
APP_DATA = BASE_DIR / "app-data"
UPLOAD_DIR = APP_DATA / "uploads"
OUTPUT_DIR = APP_DATA / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(APP_DATA / "templates"),
    static_folder=str(APP_DATA / "static"),
)

# Optional: limit uploads to ~10MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _find_free_port(preferred: int = 5000) -> int:
    # Simple “try preferred, else pick a free one”
    for port in (preferred, preferred + 1, preferred + 2):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # Let OS pick a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/transform")
def transform():
    """
    Expects multipart form with:
      - mapping_file (json)
      - input_file (json)
    Returns:
      { ok: true, output_json: "<pretty>", download_url: "/download/<id>" }
    """
    if "mapping_file" not in request.files or "input_file" not in request.files:
        return jsonify(ok=False, error="Please upload both mapping.json and input.json"), 400

    mapping_f = request.files["mapping_file"]
    input_f = request.files["input_file"]

    if not mapping_f.filename or not input_f.filename:
        return jsonify(ok=False, error="Both files must have a filename."), 400

    job_id = str(uuid.uuid4())
    mapping_path = UPLOAD_DIR / f"{job_id}_mapping.json"
    input_path = UPLOAD_DIR / f"{job_id}_input.json"
    output_path = OUTPUT_DIR / f"{job_id}_output.json"

    # Save uploads
    mapping_f.save(mapping_path)
    input_f.save(input_path)

    # Quick validation: ensure they are JSON (gives nicer error messages)
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            json.load(f)
        with open(input_path, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        return jsonify(ok=False, error=f"Invalid JSON uploaded: {e}"), 400

    try:
        util = json_migr_util(strict=False)
        util.migrate_json(str(mapping_path), str(input_path), str(output_path))
    except Exception as e:
        return jsonify(ok=False, error=f"Migration failed: {e}"), 500

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            output_text = f.read()
    except Exception as e:
        return jsonify(ok=False, error=f"Could not read output: {e}"), 500

    return jsonify(
        ok=True,
        output_json=output_text,
        download_url=f"/download/{job_id}",
    )


@app.get("/download/<job_id>")
def download(job_id: str):
    output_path = OUTPUT_DIR / f"{job_id}_output.json"
    if not output_path.exists():
        return "Not found", 404
    return send_file(output_path, as_attachment=True, download_name="out.json")


def _open_browser(url: str):
    # Delay a moment so Flask starts first
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()


if __name__ == "__main__":
    port = _find_free_port(5000)
    url = f"http://127.0.0.1:{port}/"
    _open_browser(url)
    app.run(host="127.0.0.1", port=port, debug=False)
