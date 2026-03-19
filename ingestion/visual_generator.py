"""
TwitterYoldas — Visual Generator
Wiro.ai API (reve/generate model) ile tweet görselleri üretir.
API pattern: mirror-picture-pipeline projesinden alınmıştır.

Akış:
  POST /v1/Run/{model} → taskid
  Poll /v1/Task/Detail → task_postprocess_end
  İndir → preview/data/visuals/ kaydet
"""

import os, sys, json, time, requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

WIRO_API_KEY      = os.getenv("WIRO_API_KEY", "039gchr2hscgjackhaedmhwezjcsd9g9")
WIRO_BASE         = "https://api.wiro.ai/v1"
WIRO_MODEL        = "reve/generate"          # mirror-picture-pipeline'dan alınan model
POLL_ENDPOINT     = f"{WIRO_BASE}/Task/Detail"
POLL_INTERVAL     = 3    # saniye
POLL_TIMEOUT      = 120  # saniye

FORMATS_FILE  = BASE_DIR / "data" / "tweet_formats.json"
VISUALS_DIR   = BASE_DIR / "preview" / "data" / "visuals"
VISUALS_DIR.mkdir(parents=True, exist_ok=True)


# ── Auth ──────────────────────────────────────────────────────
def _headers() -> dict:
    return {"x-api-key": WIRO_API_KEY, "Content-Type": "application/json"}


# ── Format Kütüphanesi ────────────────────────────────────────
def load_formats() -> dict:
    with open(FORMATS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {fmt["id"]: fmt for fmt in data["formats"]}


def build_prompt(format_id: str, variables: dict) -> str:
    """Format şablonunu değişkenlerle doldurur."""
    formats = load_formats()
    if format_id not in formats:
        # fallback: genel prompt
        return f"Minimalist dark tech card. {' '.join(str(v) for v in variables.values())}"
    template = formats[format_id]["wiro_prompt_template"]
    for key, val in variables.items():
        template = template.replace("{" + key + "}", str(val))
    # Doldurulamayan değişkenleri temizle
    import re
    template = re.sub(r"\{[^}]+\}", "", template)
    return template.strip()


# ── Wiro.ai Generate + Poll ───────────────────────────────────
def _submit_task(prompt: str, aspect_ratio: str = "16:9") -> str:
    """Görsel oluşturma görevini başlatır, taskid döner."""
    payload = {
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "format": "png",
    }
    resp = requests.post(
        f"{WIRO_BASE}/Run/{WIRO_MODEL}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    taskid = data.get("taskid") or data.get("tasktoken")
    if not taskid:
        raise ValueError(f"taskid alınamadı: {data}")
    print(f"[Wiro] Task başlatıldı: {taskid}")
    return taskid


def _poll_task(taskid: str) -> str:
    """Task tamamlanana kadar poll eder, image URL döner."""
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        resp = requests.post(
            POLL_ENDPOINT,
            headers=_headers(),
            json={"taskid": taskid},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        tasks = data.get("tasklist", [])
        if tasks and tasks[0].get("status") == "task_postprocess_end":
            outputs = tasks[0].get("outputs", [])
            if outputs:
                url = outputs[0].get("url")
            if not url:
                url = tasks[0].get("result") or tasks[0].get("imageUrl")
            if url:
                print(f"[Wiro] Görsel hazır: {url[:80]}...")
                return url
            break
    raise TimeoutError(f"Wiro poll timeout ({POLL_TIMEOUT}s) — taskid: {taskid}")


def _download(url: str, dest: Path) -> Path:
    """Görseli diske indirir."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"[Wiro] Kaydedildi: {dest}")
    return dest


# ── Ana Fonksiyon ─────────────────────────────────────────────
def generate_visual(
    format_id: str,
    variables: dict,
    output_path: Path | None = None,
    aspect_ratio: str | None = None,
) -> dict:
    """
    Format kütüphanesinden prompt oluştur, Wiro.ai ile görsel üret.

    Döndürür:
        {
          "success": bool,
          "local_path": str | None,   # preview/data/visuals/ altında
          "url": str | None,          # Wiro CDN URL
          "error": str | None
        }
    """
    try:
        # Aspect ratio format kütüphanesinden al
        if not aspect_ratio:
            fmts = load_formats()
            fmt = fmts.get(format_id, {})
            aspect_ratio = fmt.get("visual_style", {}).get("aspect_ratio", "16:9")

        prompt = build_prompt(format_id, variables)
        print(f"[Wiro] Format: {format_id} | AR: {aspect_ratio}")
        print(f"[Wiro] Prompt: {prompt[:120]}...")

        taskid    = _submit_task(prompt, aspect_ratio)
        image_url = _poll_task(taskid)

        # İndir
        if output_path is None:
            ts = int(time.time() * 1000)
            output_path = VISUALS_DIR / f"{format_id}_{ts}.png"
        _download(image_url, output_path)

        return {
            "success": True,
            "local_path": str(output_path),
            "url": image_url,
            "filename": output_path.name,
            "error": None,
        }

    except requests.HTTPError as e:
        err = f"HTTP {e.response.status_code}: {e.response.text[:300]}"
        print(f"[Wiro] HTTPError: {err}")
        return {"success": False, "local_path": None, "url": None, "filename": None, "error": err}
    except TimeoutError as e:
        print(f"[Wiro] Timeout: {e}")
        return {"success": False, "local_path": None, "url": None, "filename": None, "error": str(e)}
    except Exception as e:
        print(f"[Wiro] Hata: {e}")
        return {"success": False, "local_path": None, "url": None, "filename": None, "error": str(e)}


def generate_for_thread(thread_data: dict) -> dict:
    """
    Preview thread JSON'u için görsel üret, thread verisini güncelle.
    thread_data: preview/data/current_thread.json formatı
    """
    fmt_id    = thread_data.get("analysis", {}).get("format_id", "ai_startup_factory_series")
    variables = thread_data.get("visual_variables", {})

    if not variables:
        print("[Wiro] visual_variables boş, varsayılan kullanılıyor.")
        variables = {"bulgu_no": "1", "kaynak_sayisi": "41",
                     "pain_point_sayisi": "13", "firsat_sayisi": "1"}

    result = generate_visual(fmt_id, variables)

    # İlk tweet'e görsel bilgisini ekle
    if result["success"] and thread_data.get("tweets"):
        tweet1 = thread_data["tweets"][0]
        tweet1["visual_local"] = result["local_path"]
        tweet1["visual_url"]   = result["url"]

    return result


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    fmt = sys.argv[1] if len(sys.argv) > 1 else "ai_startup_factory_series"
    vars_map = {
        "bulgu_no": "1",
        "kaynak_sayisi": "41",
        "pain_point_sayisi": "13",
        "firsat_sayisi": "1",
    }
    print(f"\n[Test] Format: {fmt}")
    result = generate_visual(fmt, vars_map)
    print(f"\n[Sonuç] {json.dumps(result, ensure_ascii=False, indent=2)}")
