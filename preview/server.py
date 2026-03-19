"""
TwitterYoldas — Tweet Preview Server
Creator skill thread çıktısını tarayıcıda gösterir.
Çalıştır: python preview/server.py
"""

import json, os, sys, threading, webbrowser
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request

_HERE       = Path(__file__).resolve().parent   # D:/LLM/Twitter Skill/preview/
BASE_DIR    = _HERE.parent
STATIC      = _HERE / "static"
REACT_BUILD = _HERE / "static-react"           # Vite build çıktısı
LIBRARY_DIR = _HERE / "library"                # Thread Kütüphanesi
DATA_DIR    = _HERE / "data"
DATA_DIR.mkdir(exist_ok=True)
THREAD_FILE = DATA_DIR / "current_thread.json"
VISUALS_DIR = DATA_DIR / "visuals"
VISUALS_DIR.mkdir(exist_ok=True)

PORT = 7731
app  = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")


@app.route("/")
def index():
    # React build varsa onu sun, yoksa vanilla index.html
    if (REACT_BUILD / "index.html").exists():
        return send_from_directory(REACT_BUILD, "index.html")
    return send_from_directory(STATIC, "index.html")


@app.route("/assets/<path:filename>")
def serve_react_assets(filename):
    return send_from_directory(REACT_BUILD / "assets", filename)


@app.route("/library")
@app.route("/library/")
def library():
    return send_from_directory(LIBRARY_DIR, "index.html")


@app.route("/library/<path:filename>")
def library_static(filename):
    return send_from_directory(LIBRARY_DIR, filename)


@app.route("/api/thread")
def get_thread():
    if not THREAD_FILE.exists():
        return jsonify({"error": "Henüz thread yok. Creator skill'i çalıştırın."}), 404
    with open(THREAD_FILE, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/thread", methods=["POST"])
def save_thread():
    data = request.get_json(force=True)
    with open(THREAD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True})


@app.route("/api/formats")
def get_formats():
    fmt_file = BASE_DIR / "data" / "tweet_formats.json"
    if not fmt_file.exists():
        return jsonify({"error": "tweet_formats.json bulunamadı"}), 404
    with open(fmt_file, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/visuals/<path:filename>")
def serve_visual(filename):
    return send_from_directory(VISUALS_DIR, filename)


FEEDBACK_FILE = DATA_DIR / "feedback.json"


def _load_feedback() -> dict:
    if not FEEDBACK_FILE.exists():
        return {"items": []}
    with open(FEEDBACK_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_feedback(data: dict):
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    return jsonify(_load_feedback())


@app.route("/api/feedback", methods=["POST"])
def post_feedback():
    body   = request.get_json(force=True)
    action = body.get("action", "add")
    data   = _load_feedback()

    if action == "add":
        data["items"].append(body.get("item", {}))
        _save_feedback(data)

    elif action == "send_all":
        # Inline tweet yorumlarını da ekle
        inline = body.get("inline_items", [])
        data["items"].extend(inline)
        _save_feedback(data)

    elif action == "clear":
        data["items"] = []
        _save_feedback(data)

    elif action == "delete":
        idx = body.get("idx", -1)
        if 0 <= idx < len(data["items"]):
            data["items"].pop(idx)
        _save_feedback(data)

    return jsonify({"ok": True})


@app.route("/api/ping")
def ping():
    return jsonify({"status": "ok", "port": PORT})


# ════════════════════════════════════════════════════════════
# DRAFT + PERFORMANCE API
# ════════════════════════════════════════════════════════════

def _get_db():
    """db_manager'ı lazy import eder (server başlarken DB yoksa crash olmasın)."""
    try:
        import importlib, sys as _sys
        # Modülün güncel versiyonunu kullan
        if "db_manager" in _sys.modules:
            return _sys.modules["db_manager"]
        import sys as _sys2
        _sys2.path.insert(0, str(_HERE))
        import db_manager
        return db_manager
    except Exception as e:
        return None


@app.route("/api/drafts", methods=["GET"])
def list_drafts():
    db = _get_db()
    if not db:
        return jsonify({"error": "DB modülü yüklenemedi"}), 500
    status = request.args.get("status")  # ?status=öneri veya ?status=atılmış
    drafts = db.list_drafts(status=status)
    # UUID ve datetime JSON serializable değil → string'e çevir
    return jsonify({"drafts": _serialize(drafts)})


@app.route("/api/drafts/<draft_id>", methods=["GET"])
def get_draft(draft_id):
    db = _get_db()
    if not db:
        return jsonify({"error": "DB modülü yüklenemedi"}), 500
    draft = db.get_draft(draft_id)
    if not draft:
        return jsonify({"error": "Draft bulunamadı"}), 404
    return jsonify(_serialize(draft))


@app.route("/api/drafts/by-key/<path:draft_key>", methods=["GET"])
def get_draft_by_key(draft_key):
    """thread_title + tarih hash'iyle draft ara (thread yüklenince durum kontrolü)."""
    db = _get_db()
    if not db:
        return jsonify({"error": "DB modülü yüklenemedi"}), 500
    draft = db.get_draft_by_key(draft_key)
    if not draft:
        return jsonify({"exists": False}), 200
    return jsonify({"exists": True, **_serialize(draft)})


@app.route("/api/drafts", methods=["POST"])
def save_draft():
    """Mevcut current_thread.json'u 'öneri' olarak DB'ye kaydeder."""
    db = _get_db()
    if not db:
        return jsonify({"error": "DB modülü yüklenemedi"}), 500
    if not THREAD_FILE.exists():
        return jsonify({"error": "current_thread.json yok. Önce Creator skill çalıştır."}), 404
    with open(THREAD_FILE, encoding="utf-8") as f:
        thread_data = json.load(f)
    result = db.save_draft(thread_data)
    if result.get("conflict"):
        return jsonify({"conflict": True, **result}), 409
    return jsonify(result), 201


@app.route("/api/post", methods=["POST"])
def mark_posted():
    """
    Tweet URL'ini kaydeder ve draft'ı 'atılmış' olarak işaretler.
    Body: {"draft_id": "uuid", "tweet_url": "https://x.com/.../status/123..."}
    """
    db = _get_db()
    if not db:
        return jsonify({"error": "DB modülü yüklenemedi"}), 500
    body     = request.get_json(force=True)
    draft_id = body.get("draft_id", "")
    tweet_url = body.get("tweet_url", "")
    if not draft_id or not tweet_url:
        return jsonify({"error": "draft_id ve tweet_url gerekli"}), 400
    result = db.mark_posted(draft_id, tweet_url)
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/performance/<draft_id>", methods=["GET"])
def get_performance(draft_id):
    db = _get_db()
    if not db:
        return jsonify({"error": "DB modülü yüklenemedi"}), 500
    snaps = db.get_snapshots(draft_id)
    return jsonify({"snapshots": _serialize(snaps)})


@app.route("/api/performance/<draft_id>/fetch", methods=["POST"])
def fetch_performance(draft_id):
    """Manuel performans çekimi tetikler (performance_checker.py çağırır)."""
    import subprocess, sys as _sys
    checker = _HERE / "performance_checker.py"
    if not checker.exists():
        return jsonify({"error": "performance_checker.py bulunamadı"}), 404
    try:
        result = subprocess.run(
            [_sys.executable, str(checker), "--draft-id", draft_id],
            capture_output=True, text=True, timeout=30
        )
        return jsonify({"ok": True, "output": result.stdout[-500:], "err": result.stderr[-300:]})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout (30s)"}), 504


def _serialize(obj):
    """UUID, datetime gibi JSON-incompatible tipleri string'e çevirir."""
    import uuid as _uuid
    from datetime import datetime as _dt
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, _uuid.UUID):
        return str(obj)
    if isinstance(obj, _dt):
        return obj.isoformat()
    return obj


def open_browser():
    import time; time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    auto_open = "--no-browser" not in sys.argv
    if auto_open:
        threading.Thread(target=open_browser, daemon=True).start()
    print(f"\nTwitterYoldas Preview -> http://localhost:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
