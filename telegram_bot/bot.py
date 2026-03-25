"""
TwitterYoldas Telegram Bot
@ciftcibahadir için tweet üretim ve onay botu.

Akış:
1. Telegram'dan fikir/konu gönder
2. Bot OpenAI/Claude API ile Creator logic'ini çalıştırır
3. İçerik + inline onay butonları gelir
4. ✅ tıklanırsa tweet_queue.json'a yazar
5. Claude Code'da /twitter:post ile Xquik üzerinden X'e atılır
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from creator_prompt import (
    CREATOR_SYSTEM_PROMPT,
    get_analysis_context,
    get_brainstorm_context,
    get_thread_context,
)

# ── Config ──────────────────────────────────────────────────────────────────
# Önce kendi .env'i yükle, sonra ana .env ile eksikleri tamamla (ana .env öncelikli)
_THIS_DIR = Path(__file__).parent
load_dotenv(_THIS_DIR / ".env")                        # telegram_bot/.env
load_dotenv(_THIS_DIR.parent / ".env", override=True)  # D:/LLM/Twitter Skill/.env (override)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
QUEUE_FILE = Path(os.getenv("QUEUE_FILE", "D:/LLM/Twitter Skill/tweet_queue.json"))
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))  # Güvenlik: sadece bu chat'e yanıt ver

# ── LLM Client — OpenAI öncelikli, Anthropic fallback ───────────────────────
if OPENAI_API_KEY:
    from openai import OpenAI
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
    LLM_BACKEND = "openai"
elif ANTHROPIC_API_KEY:
    from anthropic import Anthropic
    llm_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    LLM_BACKEND = "anthropic"
    if "gpt" in LLM_MODEL:
        LLM_MODEL = "claude-opus-4-5"
else:
    raise ValueError("OPENAI_API_KEY veya ANTHROPIC_API_KEY .env'de tanımlı olmalı!")

# ── Kullanıcı oturum geçmişi (context window) ───────────────────────────────
user_sessions: dict[int, list] = {}  # user_id -> conversation history

# ── Queue yardımcıları ───────────────────────────────────────────────────────

def load_queue() -> dict:
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "tweets": []}


def save_queue(data: dict):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_to_queue(text: str, tweet_type: str = "tweet", thread_tweets: list = None) -> str:
    """Onaylanan tweeti queue'ya ekler, kısa ID döner."""
    queue = load_queue()
    short_id = str(uuid.uuid4())[:8]
    entry = {
        "id": short_id,
        "type": tweet_type,
        "text": text,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "source": "telegram_bot",
    }
    if thread_tweets:
        entry["thread_tweets"] = thread_tweets
    queue["tweets"].append(entry)
    save_queue(queue)
    return short_id


# ── Yetki kontrolü ──────────────────────────────────────────────────────────

def is_allowed(user_id: int, chat_id: int = 0) -> bool:
    """Chat ID ve/veya User ID kontrolü — her ikisi de 0 ise herkese açık."""
    if TELEGRAM_CHAT_ID != 0 and chat_id != TELEGRAM_CHAT_ID:
        return False
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return False
    return True


# ── Claude API çağrısı ───────────────────────────────────────────────────────

def call_creator(user_id: int, user_message: str) -> str:
    """OpenAI veya Anthropic API'yi Creator system prompt ile çağırır, konuşma geçmişini korur."""
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "content": user_message})

    # Konuşma geçmişini max 20 mesajla sınırla (context window yönetimi)
    if len(user_sessions[user_id]) > 20:
        user_sessions[user_id] = user_sessions[user_id][-20:]

    if LLM_BACKEND == "openai":
        # OpenAI Chat Completions API
        messages = [{"role": "system", "content": CREATOR_SYSTEM_PROMPT}] + user_sessions[user_id]
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,  # gpt-4o veya gpt-4o-mini
            max_tokens=4096,
            messages=messages,
        )
        assistant_text = response.choices[0].message.content
    else:
        # Anthropic Messages API
        response = llm_client.messages.create(
            model=LLM_MODEL,
            max_tokens=4096,
            system=CREATOR_SYSTEM_PROMPT,
            messages=user_sessions[user_id],
        )
        assistant_text = response.content[0].text

    user_sessions[user_id].append({"role": "assistant", "content": assistant_text})
    return assistant_text


# ── Telegram mesaj parsing ───────────────────────────────────────────────────

def detect_mode(text: str) -> str:
    """Kullanıcı girdisinden modu tespit et."""
    t = text.lower()
    if any(k in t for k in ["thread yap", "thread olarak", "thread üret"]):
        return "thread"
    if any(k in t for k in ["analiz et", "neden tutmadı", "düzelt", "iyileştir"]):
        return "analiz"
    if any(k in t for k in ["bu hafta ne", "öneri", "plan yap", "haftalık"]):
        return "öneri"
    if any(k in t for k in ["hangisi", "a mı b mi", "karşılaştır", "kıyasla"]):
        return "kıyaslama"
    return "brainstorm"  # default


def build_prompt(mode: str, text: str) -> str:
    if mode == "brainstorm":
        return get_brainstorm_context(text)
    elif mode == "thread":
        konu = text.replace("thread yap", "").replace("thread olarak", "").strip()
        return get_thread_context(konu)
    elif mode == "analiz":
        return get_analysis_context(text)
    else:
        return text  # öneri ve kıyaslama için direkt gönder


# ── Telegram handler'ları ────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    await update.message.reply_text(
        "👋 Merhaba! Ben TwitterYoldas Creator Bot.\n\n"
        "Bana bir fikir, konu veya tweet ver — sana viral içerik üreteyim.\n\n"
        "📌 Komutlar:\n"
        "/brainstorm <fikir> — 3 farklı tweet versiyonu\n"
        "/thread <konu> — Tam thread\n"
        "/analiz <tweet> — Mevcut tweeti iyileştir\n"
        "/öneri — Bu hafta ne atsam?\n"
        "/temizle — Konuşma geçmişini sıfırla\n"
        "/queue — Queue'daki tweetleri göster\n\n"
        "Ya da direkt mesaj at — modu otomatik seçerim."
    )


async def cmd_brainstorm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    topic = " ".join(context.args) if context.args else ""
    if not topic:
        await update.message.reply_text("❓ Fikri yaz: /brainstorm <fikir>")
        return
    await process_request(update, context, get_brainstorm_context(topic), "brainstorm")


async def cmd_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    topic = " ".join(context.args) if context.args else ""
    if not topic:
        await update.message.reply_text("❓ Konuyu yaz: /thread <konu>")
        return
    await process_request(update, context, get_thread_context(topic), "thread")


async def cmd_analiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    tweet = " ".join(context.args) if context.args else ""
    if not tweet:
        await update.message.reply_text("❓ Tweeti yaz: /analiz <tweet metni>")
        return
    await process_request(update, context, get_analysis_context(tweet), "analiz")


async def cmd_öneri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    prompt = "Bu hafta için haftalık içerik planı hazırla. MOD 4 ÖNERİ modunu kullan."
    await process_request(update, context, prompt, "öneri")


async def cmd_temizle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    await update.message.reply_text("🗑️ Konuşma geçmişi temizlendi.")


async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    queue = load_queue()
    pending = [t for t in queue.get("tweets", []) if t["status"] == "pending"]
    if not pending:
        await update.message.reply_text("📭 Queue boş. Henüz onaylanan tweet yok.")
        return

    lines = [f"📋 *Tweet Queue* — {len(pending)} pending\n"]
    for t in pending:
        preview = t["text"][:60].replace("\n", " ")
        lines.append(f"`{t['id']}` | {t['type']} | {preview}...")

    lines.append("\n💡 Claude Code'da `/twitter:post` ile yayınlayabilirsin.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Serbest mesajları işle — modu otomatik tespit et."""
    if not is_allowed(update.effective_user.id, update.effective_chat.id):
        return
    text = update.message.text.strip()
    mode = detect_mode(text)
    prompt = build_prompt(mode, text)
    await process_request(update, context, prompt, mode)


async def process_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
    mode: str,
):
    """Creator'ı çağır, sonucu inline butonlarla gönder."""
    user_id = update.effective_user.id
    status_msg = await update.message.reply_text("⏳ İçerik üretiliyor...")

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, call_creator, user_id, prompt
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Hata: {e}")
        return

    # Sonucu parçalara böl (Telegram max 4096 karakter)
    chunks = [result[i : i + 4000] for i in range(0, len(result), 4000)]

    # İlk chunk'ı düzenle, geri kalanları yeni mesaj olarak at
    await status_msg.edit_text(chunks[0])
    for chunk in chunks[1:]:
        await update.message.reply_text(chunk)

    # Onay butonlarını sadece öneri/kıyaslama dışında göster
    if mode not in ("öneri", "kıyaslama"):
        # Context'e result ve mode kaydet (callback için)
        context.user_data["pending_content"] = result
        context.user_data["pending_mode"] = mode

        keyboard = [
            [
                InlineKeyboardButton("✅ Kuyruğa Ekle", callback_data="queue_add"),
                InlineKeyboardButton("✏️ Düzenle", callback_data="edit_request"),
                InlineKeyboardButton("❌ İptal", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👆 Bu içeriği queue'ya ekleyeyim mi?",
            reply_markup=reply_markup,
        )


def load_pending() -> dict:
    """telegram_pending.json'u oku (Creator skill'den gelen onay bekleyenler)."""
    pending_file = QUEUE_FILE.parent / "telegram_pending.json"
    if pending_file.exists():
        with open(pending_file, encoding="utf-8") as f:
            return json.load(f)
    return {"items": []}


def resolve_pending(item_id: str, approved: bool) -> dict | None:
    """Pending item'ı bul, durumunu güncelle. İçeriği döndür."""
    pending_file = QUEUE_FILE.parent / "telegram_pending.json"
    data = load_pending()
    found = None
    for item in data["items"]:
        if item["id"] == item_id and item["status"] == "awaiting_approval":
            item["status"] = "approved" if approved else "rejected"
            found = item
            break
    with open(pending_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return found


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline buton callback'lerini işle."""
    query = update.callback_query
    await query.answer()
    action = query.data

    # ── Creator skill'den gelen onay (approve:<id> / reject:<id>) ──
    if action.startswith("approve:"):
        item_id = action.split(":", 1)[1]
        item = resolve_pending(item_id, approved=True)
        if not item:
            await query.edit_message_text("⚠️ Bu içerik zaten işlendi veya bulunamadı.")
            return
        short_id = add_to_queue(item["text"], item.get("type", "tweet"))
        await query.edit_message_text(
            f"✅ Kuyruğa eklendi!\n"
            f"🆔 ID: `{short_id}`\n\n"
            f"Claude Code'da `/twitter:post` ile yayınlayabilirsin.",
            parse_mode="Markdown",
        )

    elif action.startswith("reject:"):
        item_id = action.split(":", 1)[1]
        resolve_pending(item_id, approved=False)
        await query.edit_message_text("❌ İçerik reddedildi.")

    # ── Bot içinden üretilen içerik onayı (eski format) ──
    elif action == "queue_add":
        content = context.user_data.get("pending_content", "")
        mode = context.user_data.get("pending_mode", "tweet")
        tweet_type = "thread" if mode == "thread" else "tweet"
        short_id = add_to_queue(content, tweet_type)
        await query.edit_message_text(
            f"✅ Kuyruğa eklendi!\n"
            f"🆔 ID: `{short_id}`\n\n"
            f"Claude Code'da `/twitter:post` ile yayınlayabilirsin.",
            parse_mode="Markdown",
        )

    elif action == "edit_request":
        await query.edit_message_text(
            "✏️ Düzenleme isteğini mesaj olarak yaz.\n"
            "Örn: 'Kancayı daha güçlü yap' veya 'Daha kısa yaz'"
        )

    elif action == "cancel":
        context.user_data.pop("pending_content", None)
        context.user_data.pop("pending_mode", None)
        await query.edit_message_text("❌ İptal edildi.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN .env'de tanimli degil!")
    if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        raise ValueError("OPENAI_API_KEY veya ANTHROPIC_API_KEY .env'de tanimli olmali!")

    print("🚀 TwitterYoldas Telegram Bot başlatılıyor...")
    print(f"🤖 LLM Backend: {LLM_BACKEND.upper()} ({LLM_MODEL})")
    print(f"📁 Queue dosyası: {QUEUE_FILE}")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("brainstorm", cmd_brainstorm))
    app.add_handler(CommandHandler("thread", cmd_thread))
    app.add_handler(CommandHandler("analiz", cmd_analiz))
    app.add_handler(CommandHandler(["öneri", "oneri"], cmd_öneri))
    app.add_handler(CommandHandler("temizle", cmd_temizle))
    app.add_handler(CommandHandler("queue", cmd_queue))

    # Inline buton callback
    app.add_handler(CallbackQueryHandler(button_callback))

    # Serbest mesajlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot hazır. Telegram'dan mesaj gönderebilirsin.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
