"""
Export tweets from a specific session (or latest session) to Excel,
then send the file to Telegram.

Usage:
    python export_tweets_to_excel.py [session_id]
    python export_tweets_to_excel.py  # uses latest session
"""
import os
import sys
import requests
import psycopg2
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# --- Config ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_FILE = PROJECT_DIR / ".env"
TELEGRAM_ENV = Path("C:/Users/ciftc/.codex/skills/pain-to-mvp-researcher/.env")

load_dotenv(ENV_FILE)
load_dotenv(TELEGRAM_ENV, override=False)

DB_HOST     = os.environ["DB_HOST"]
DB_PORT     = os.environ.get("DB_PORT", "5432")
DB_NAME     = os.environ["DB_NAME"]
DB_USER     = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

# --- DB ---
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

def get_latest_session(conn) -> str:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT session_id FROM tweets
            WHERE session_id IS NOT NULL
            ORDER BY created_at_db DESC LIMIT 1
        """)
        row = cur.fetchone()
        return row[0] if row else None

def fetch_tweets(conn, session_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                t.tweet_id,
                t.username,
                t.display_name,
                t.author_followers,
                t.author_verified,
                t.created_at,
                t.text,
                t.likes,
                t.retweets,
                t.replies,
                t.quotes,
                t.bookmarks,
                t.impressions,
                ROUND(t.engagement_rate::numeric, 4)  AS engagement_rate,
                ROUND(t.bookmark_rate::numeric, 4)    AS bookmark_rate,
                ROUND(t.priority_score::numeric, 4)   AS priority_score,
                t.priority,
                t.language,
                t.has_media,
                t.media_type,
                t.is_thread,
                t.thread_length,
                t.has_link,
                t.link_domain,
                t.hashtags,
                t.query_used,
                t.tweet_url,
                tl.kanca_tipi,
                tl.ton,
                tl.psikolojik_tetikleyici,
                tl.icerik_formu,
                tl.gorsel_format,
                tl.quality_tier
            FROM tweets t
            LEFT JOIN tweet_labels tl ON tl.tweet_id = t.tweet_id
            WHERE t.session_id = %s
            ORDER BY t.priority_score DESC NULLS LAST
        """, (session_id,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

# --- Excel ---
HEADER_FILL   = PatternFill("solid", fgColor="1F4E79")
HIGH_FILL     = PatternFill("solid", fgColor="E2EFDA")
NORMAL_FILL   = PatternFill("solid", fgColor="FFFFFF")
ALT_FILL      = PatternFill("solid", fgColor="F2F2F2")
S_FILL        = PatternFill("solid", fgColor="FFD700")
A_FILL        = PatternFill("solid", fgColor="C6EFCE")
B_FILL        = PatternFill("solid", fgColor="FFEB9C")
C_FILL        = PatternFill("solid", fgColor="FFC7CE")

THIN = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)

COLUMNS = [
    ("tweet_id",              "Tweet ID",         14),
    ("username",              "Kullanıcı",        16),
    ("display_name",          "İsim",             18),
    ("author_followers",      "Takipçi",          10),
    ("author_verified",       "Verified",          9),
    ("created_at",            "Tarih",            18),
    ("text",                  "Tweet Metni",      60),
    ("likes",                 "Beğeni",           10),
    ("retweets",              "RT",               10),
    ("replies",               "Yanıt",            10),
    ("quotes",                "Alıntı",           10),
    ("bookmarks",             "Bookmark",         10),
    ("impressions",           "İzlenim",          12),
    ("engagement_rate",       "Eng. Rate",        11),
    ("bookmark_rate",         "Bkm. Rate",        11),
    ("priority_score",        "P.Score",          10),
    ("priority",              "Öncelik",          10),
    ("language",              "Dil",               7),
    ("has_media",             "Medya?",            9),
    ("media_type",            "Medya Tipi",       12),
    ("is_thread",             "Thread?",           9),
    ("thread_length",         "Thread Uzunluk",   14),
    ("has_link",              "Link?",             8),
    ("link_domain",           "Domain",           18),
    ("hashtags",              "Hashtagler",       20),
    ("query_used",            "Sorgu",            28),
    ("tweet_url",             "URL",              40),
    ("kanca_tipi",            "Kanca Tipi",       16),
    ("ton",                   "Ton",              14),
    ("psikolojik_tetikleyici","Tetikleyici",      18),
    ("icerik_formu",          "İçerik Formu",     16),
    ("gorsel_format",         "Görsel Format",    16),
    ("quality_tier",          "Kalite",            9),
]

def build_excel(tweets: list[dict], session_id: str, out_path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tweets"
    ws.freeze_panes = "A2"

    # Header row
    for col_idx, (field, header, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font      = Font(bold=True, color="FFFFFF", size=10)
        cell.fill      = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = THIN
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[1].height = 28

    # Data rows
    for row_idx, tweet in enumerate(tweets, start=2):
        is_alt    = (row_idx % 2 == 0)
        is_high   = tweet.get("priority") == "high"
        tier      = tweet.get("quality_tier") or ""

        row_fill = (
            S_FILL if tier == "S" else
            A_FILL if tier == "A" else
            B_FILL if tier == "B" else
            C_FILL if tier == "C" else
            HIGH_FILL if is_high else
            ALT_FILL if is_alt else
            NORMAL_FILL
        )

        for col_idx, (field, header, _) in enumerate(COLUMNS, start=1):
            value = tweet.get(field)

            # Format special types
            if isinstance(value, list):
                value = ", ".join(value) if value else ""
            elif isinstance(value, bool):
                value = "Evet" if value else "Hayır"
            elif isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M")

            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill      = row_fill
            cell.border    = THIN
            cell.alignment = Alignment(vertical="top", wrap_text=(field == "text"))

            if field == "tweet_url" and value:
                cell.value     = "🔗 Aç"
                cell.hyperlink = value
                cell.style     = "Hyperlink"
                cell.font      = Font(size=9, underline="single")
            else:
                cell.font  = Font(size=9)

        ws.row_dimensions[row_idx].height = 60 if any(
            tweet.get("text", "") and len(tweet.get("text", "")) > 100
            for _ in [None]
        ) else 18

    # Summary sheet
    ws2 = wb.create_sheet("Özet")
    ws2["A1"] = "Session"
    ws2["B1"] = session_id
    ws2["A2"] = "Toplam Tweet"
    ws2["B2"] = len(tweets)
    ws2["A3"] = "Yüksek Öncelik"
    ws2["B3"] = sum(1 for t in tweets if t.get("priority") == "high")
    ws2["A4"] = "Thread"
    ws2["B4"] = sum(1 for t in tweets if t.get("is_thread"))
    ws2["A5"] = "Medyalı"
    ws2["B5"] = sum(1 for t in tweets if t.get("has_media"))
    ws2["A6"] = "TR"
    ws2["B6"] = sum(1 for t in tweets if t.get("language") == "tr")
    ws2["A7"] = "EN"
    ws2["B7"] = sum(1 for t in tweets if t.get("language") == "en")
    ws2["A8"] = "S Tier"
    ws2["B8"] = sum(1 for t in tweets if t.get("quality_tier") == "S")
    ws2["A9"] = "A Tier"
    ws2["B9"] = sum(1 for t in tweets if t.get("quality_tier") == "A")
    ws2["A10"] = "B Tier"
    ws2["B10"] = sum(1 for t in tweets if t.get("quality_tier") == "B")
    ws2["A11"] = "C Tier"
    ws2["B11"] = sum(1 for t in tweets if t.get("quality_tier") == "C")

    for row in ws2.iter_rows(min_row=1, max_row=11):
        for cell in row:
            cell.font = Font(bold=(cell.column == 1), size=10)
            cell.border = THIN

    ws2.column_dimensions["A"].width = 20
    ws2.column_dimensions["B"].width = 30

    wb.save(out_path)
    print(f"Excel kaydedildi: {out_path}")

# --- Telegram ---
def send_document_to_telegram(file_path: Path, caption: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML",
        }, files={"document": (file_path.name, f,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    resp.raise_for_status()
    print(f"Telegram'a gönderildi: {file_path.name}")

# --- Main ---
def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else None

    conn = get_connection()
    try:
        if not session_id:
            session_id = get_latest_session(conn)
        if not session_id:
            print("Hiç session bulunamadı.")
            return

        print(f"Session: {session_id}")
        tweets = fetch_tweets(conn, session_id)
        print(f"{len(tweets)} tweet bulundu.")

        if not tweets:
            print("Bu sessionda tweet yok.")
            return

        out_dir = Path("D:/LLM/Twitter Skill/data")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"tweets_{session_id}.xlsx"
        build_excel(tweets, session_id, out_path)

        date_str = datetime.now().strftime("%Y-%m-%d")
        high_count = sum(1 for t in tweets if t.get("priority") == "high")
        caption = (
            f"📊 <b>The Miner — Tweet Export</b>\n"
            f"📅 {date_str}\n"
            f"🆔 Session: <code>{session_id}</code>\n\n"
            f"📦 Toplam: <b>{len(tweets)}</b> tweet\n"
            f"⭐ Yüksek öncelik: <b>{high_count}</b>\n"
            f"🇹🇷 TR: {sum(1 for t in tweets if t.get('language')=='tr')} | "
            f"🇺🇸 EN: {sum(1 for t in tweets if t.get('language')=='en')}"
        )
        send_document_to_telegram(out_path, caption)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
