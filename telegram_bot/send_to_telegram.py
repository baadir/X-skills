"""
TwitterYoldas — Send to Telegram for Approval

Creator skill'in ürettiği içeriği Telegram'a onay için gönderir.
Bot'un çalışıyor olması gerekmez — doğrudan Telegram Bot API'ye HTTP isteği atar.

Kullanım:
  python send_to_telegram.py "tweet metni"
  python send_to_telegram.py "tweet metni" --type thread
  python send_to_telegram.py --file tweet.txt
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# .env yükleme (ana .env öncelikli)
_THIS_DIR = Path(__file__).parent
load_dotenv(_THIS_DIR / ".env")
load_dotenv(_THIS_DIR.parent / ".env", override=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PENDING_FILE = _THIS_DIR.parent / "telegram_pending.json"
QUEUE_FILE = _THIS_DIR.parent / "tweet_queue.json"


def load_pending() -> dict:
    if PENDING_FILE.exists():
        with open(PENDING_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"items": []}


def save_pending(data: dict):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_pending(text: str, tweet_type: str) -> str:
    """Onay bekleyen içeriği pending dosyasına yaz, ID döndür."""
    pending = load_pending()
    item_id = str(uuid.uuid4())[:8]
    pending["items"].append({
        "id": item_id,
        "type": tweet_type,
        "text": text,
        "status": "awaiting_approval",
        "created_at": datetime.utcnow().isoformat(),
    })
    save_pending(pending)
    return item_id


def send_telegram_message(text: str, item_id: str, tweet_type: str) -> bool:
    """Telegram Bot API ile mesaj + onay butonları gönderir."""
    # Uzun içeriği kes (Telegram max 4096)
    preview = text[:3800] + ("..." if len(text) > 3800 else "")

    type_emoji = "🧵" if tweet_type == "thread" else "✍️"
    message = (
        f"{type_emoji} *Creator'dan yeni içerik*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{preview}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 `{item_id}`"
    )

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Kuyruğa Ekle", "callback_data": f"approve:{item_id}"},
            {"text": "❌ İptal",         "callback_data": f"reject:{item_id}"},
        ]]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(inline_keyboard),
    }

    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code == 200:
        return True
    else:
        print(f"Telegram API hatasi: {resp.status_code} — {resp.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Tweet içeriğini Telegram onayına gönder")
    parser.add_argument("text", nargs="?", help="Tweet metni")
    parser.add_argument("--file", "-f", help="Tweet metnini dosyadan oku")
    parser.add_argument("--type", "-t", choices=["tweet", "thread"], default="tweet",
                        help="İçerik tipi (default: tweet)")
    args = parser.parse_args()

    # Metin kaynağı
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read().strip()
    elif args.text:
        text = args.text.strip()
    else:
        # stdin'den oku (pipe ile kullanım için)
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            print("Hata: Tweet metni verilmedi. Kullanim: python send_to_telegram.py '<metin>'")
            sys.exit(1)

    if not text:
        print("Hata: Bos icerik gonderilemez.")
        sys.exit(1)

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Hata: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID tanimli degil.")
        sys.exit(1)

    # Pending'e kaydet
    item_id = add_pending(text, args.type)
    print(f"Pending ID: {item_id}")

    # Telegram'a gonder
    ok = send_telegram_message(text, item_id, args.type)
    if ok:
        print(f"Telegram'a gonderildi! ID: {item_id}")
        print("Telegram'dan onaylayinca tweet_queue.json'a eklenecek.")
    else:
        print("Telegram gonderilemedi. Token/Chat ID'yi kontrol et.")
        sys.exit(1)


if __name__ == "__main__":
    main()
