from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, after_this_request, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from processor import build_output_name, is_supported_file, process_file

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "tmp"
UPLOAD_DIR = TEMP_DIR / "uploads"
OUTPUT_DIR = TEMP_DIR / "outputs"

for directory in (TEMP_DIR, UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/process")
def api_process():
    mode = request.form.get("mode", "").strip().lower()
    file = request.files.get("file")

    if mode not in {"encode", "decode"}:
        return jsonify({"error": "mode must be encode or decode"}), 400

    if file is None or not file.filename:
        return jsonify({"error": "missing file"}), 400

    if not is_supported_file(file.filename):
        return jsonify({"error": "unsupported file type"}), 400

    safe_name = secure_filename(file.filename)
    token = secrets.token_hex(8)
    input_path = UPLOAD_DIR / f"{token}_{safe_name}"
    output_name = build_output_name(safe_name, mode)
    output_path = OUTPUT_DIR / f"{token}_{output_name}"

    file.save(input_path)

    try:
        process_file(str(input_path), str(output_path), mode)
    except Exception as exc:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 500

    media_kind = "video"
    ext = output_path.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".gif"}:
        media_kind = "image"

    @after_this_request
    def cleanup(response):
        try:
            input_path.unlink(missing_ok=True)
        except OSError:
            pass
        return response

    return jsonify(
        {
            "ok": True,
            "download_url": f"/download/{output_path.name}",
            "preview_url": f"/preview/{output_path.name}",
            "filename": output_name,
            "media_kind": media_kind,
        }
    )


@app.get("/download/<path:filename>")
def download_file(filename: str):
    path = OUTPUT_DIR / Path(filename).name
    if not path.exists():
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)


@app.get("/preview/<path:filename>")
def preview_file(filename: str):
    path = OUTPUT_DIR / Path(filename).name
    if not path.exists():
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=False, download_name=path.name)


@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=False)
