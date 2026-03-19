"""
TwitterYoldas — Creator Preview Launcher
Creator skill thread çıktısını JSON'a yazar, görsel üretir, tarayıcıda açar.

Kullanım:
  python preview/creator_preview.py                    # Mevcut thread'i aç
  python preview/creator_preview.py --generate-visual  # Görsel de üret
  python preview/creator_preview.py --write <json>     # Yeni thread yaz + aç
"""

import sys, json, os, time, subprocess, webbrowser, requests
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
PREVIEW_DIR = Path(__file__).parent
DATA_DIR    = PREVIEW_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
THREAD_FILE = DATA_DIR / "current_thread.json"
PORT        = 7731
SERVER_URL  = f"http://localhost:{PORT}"


def is_server_running() -> bool:
    try:
        r = requests.get(f"{SERVER_URL}/api/ping", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_server():
    """Preview server'ı arka planda başlatır."""
    server_script = PREVIEW_DIR / "server.py"
    subprocess.Popen(
        [sys.executable, str(server_script), "--no-browser"],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    print("[Preview] Server başlatılıyor...")
    for _ in range(12):
        time.sleep(0.8)
        if is_server_running():
            print(f"[Preview] Server hazır → {SERVER_URL}")
            return True
    print("[Preview] Server başlatılamadı. Manuel çalıştır: python preview/server.py")
    return False


def write_thread(thread_data: dict):
    """Thread verisini JSON dosyasına yazar."""
    with open(THREAD_FILE, "w", encoding="utf-8") as f:
        json.dump(thread_data, f, ensure_ascii=False, indent=2)
    print(f"[Preview] Thread yazıldı: {THREAD_FILE}")


def open_preview():
    """Server hazırsa tarayıcıyı aç."""
    if not is_server_running():
        start_server()
    webbrowser.open(SERVER_URL)
    print(f"[Preview] Tarayıcı açıldı: {SERVER_URL}")


def generate_visual_for_current():
    """Mevcut thread için Wiro.ai görsel üretir."""
    sys.path.insert(0, str(BASE_DIR / "ingestion"))
    from visual_generator import generate_for_thread  # type: ignore

    if not THREAD_FILE.exists():
        print("[Preview] Thread dosyası bulunamadı. Önce thread yaz.")
        return

    with open(THREAD_FILE, encoding="utf-8") as f:
        data = json.load(f)

    print("[Preview] Wiro.ai görsel üretiliyor...")
    result = generate_for_thread(data)

    if result["success"]:
        # Thread dosyasını görsel bilgisiyle güncelle
        write_thread(data)
        print(f"[Preview] Görsel hazır: {result['local_path']}")
        # Server'a reload sinyali gönder (5sn'de otomatik poll yapıyor ama hızlandıralım)
        try:
            requests.post(f"{SERVER_URL}/api/thread", json=data, timeout=5)
        except Exception:
            pass
    else:
        print(f"[Preview] Görsel üretilemedi: {result['error']}")


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--write" in args:
        idx = args.index("--write")
        if idx + 1 < len(args):
            thread_json = json.loads(args[idx + 1])
            write_thread(thread_json)

    if "--generate-visual" in args:
        generate_visual_for_current()

    open_preview()
