"""
Lab classification queue processor.

lab_processed=FALSE olan tweet'leri LLM ile sınıflandırır,
tweet_labels tablosuna yazar, tweets.lab_processed=TRUE yapar.

Kullanım:
  python ingestion/lab_processor.py              # tüm bekleyenleri işle
  python ingestion/lab_processor.py --limit 50   # max 50 tweet
  python ingestion/lab_processor.py --dry-run    # sadece sayıları göster

Gerekli env:
  OPENAI_API_KEY veya ANTHROPIC_API_KEY
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2  # type: ignore
from psycopg2.extras import execute_values  # type: ignore
from dotenv import load_dotenv  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from ingestion.models import LabLabel, score_to_tier

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lab system prompt
# ─────────────────────────────────────────────

LAB_SYSTEM_PROMPT = """Sen The Lab'sın — TwitterYoldas pipeline'ının sınıflandırma motorusun.

Sana verilen her tweet için tam olarak şu JSON yapısını döndür (başka hiçbir şey ekleme):

{
  "tweet_id": "<id>",
  "psikolojik_tetikleyici": ["<primary>", "<secondary_optional>"],
  "primary_trigger": "<en_güçlü_tetikleyici>",
  "icerik_formu": "<tek_seçim>",
  "ton": "<tek_seçim>",
  "kanca_tipi": "<tek_seçim>",
  "gorsel_format": "<tek_seçim>",
  "algoritma_sinyal": ["<güçlüden_zayıfa>"],
  "quality_score": <1-10>,
  "hook_text": "<açılış_cümlesi>",
  "reasoning": "<1-2_cümle>"
}

SINIFLANDIRMA KURALLARI:

psikolojik_tetikleyici seçenekleri (çoklu seçim OK):
  öfke | fomo | merak | mizah | empati | şok | gurur

icerik_formu seçenekleri (tek seçim):
  thread | liste | soru | karşıt_görüş | hikaye | veri_paylaşımı | deneyim

ton seçenekleri (tek seçim):
  alaycı | heyecanli | egitici | samimi | profesyonel

kanca_tipi seçenekleri (tek seçim):
  soru | provokasyon | rakam_ile_bas | karsi_gorus | hikaye | liste_vaadi | cesur_iddia | diger

gorsel_format seçenekleri (tek seçim):
  video | görsel | gif | yok

algoritma_sinyal seçenekleri (güçlüden zayıfa sırala):
  like_odaklı | retweet_odaklı | reply_odaklı | bookmark_odaklı | dwell_odaklı | dm_share_odaklı | follow_odaklı

quality_score (1-10):
  9-10: Güçlü hook + net psikolojik tetikleyici + yüksek etkileşim metrikleri
  7-8:  İyi hook + net tetikleyici + ortalamanın üzeri etkileşim
  4-6:  Orta hook + zayıf tetikleyici veya düşük etkileşim
  1-3:  Zayıf hook + belirsiz yapı + düşük etkileşim

ÇIKTI FORMATI: Sadece JSON array. Açıklama veya markdown ekleme."""


def build_user_prompt(tweets: List[Dict[str, Any]]) -> str:
    lines = ["Aşağıdaki tweet'leri sınıflandır:\n"]
    for t in tweets:
        lines.append(f'tweet_id: {t["tweet_id"]}')
        lines.append(f'text: {t["text"]}')
        lines.append(f'likes: {t["likes"]} | retweets: {t["retweets"]} | replies: {t["replies"]} | bookmarks: {t["bookmarks"]} | impressions: {t["impressions"]}')
        lines.append(f'has_media: {t["has_media"]} | media_type: {t.get("media_type","yok")} | is_thread: {t["is_thread"]}')
        lines.append("---")
    lines.append("\nJSON array olarak döndür:")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# LLM çağrısı
# ─────────────────────────────────────────────

def classify_batch_openai(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """OpenAI gpt-4o-mini ile batch sınıflandırma."""
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = build_user_prompt(tweets)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": LAB_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    # Model bazen {"results": [...]} formatında döner
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    return parsed.get("results", list(parsed.values())[0] if parsed else [])


def classify_batch_anthropic(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Anthropic Claude ile batch sınıflandırma."""
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = build_user_prompt(tweets)

    msg = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=4096,
        system=LAB_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    # JSON array bul
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    return json.loads(raw)


def classify_batch(tweets: List[Dict[str, Any]], model_used: str) -> List[Dict[str, Any]]:
    if "openai" in model_used.lower() or "gpt" in model_used.lower():
        return classify_batch_openai(tweets)
    return classify_batch_anthropic(tweets)


# ─────────────────────────────────────────────
# DB işlemleri
# ─────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "twitter_yoldas"),
        user=os.getenv("DB_USER", "yoldas"),
        password=os.getenv("DB_PASSWORD", "yoldas_secret"),
    )


def fetch_unprocessed(conn, limit: int = 100) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tweet_id, text, likes, retweets, replies, quotes,
                   bookmarks, impressions, has_media, media_type, is_thread
            FROM tweets
            WHERE lab_processed = FALSE
            ORDER BY priority_score DESC NULLS LAST
            LIMIT %s
            """,
            (limit,),
        )
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def write_labels(conn, labels: List[LabLabel], model_used: str) -> int:
    if not labels:
        return 0

    rows = [
        (
            lbl.tweet_id,
            lbl.psikolojik_tetikleyici or None,
            lbl.primary_trigger,
            lbl.icerik_formu,
            lbl.ton,
            lbl.kanca_tipi,
            lbl.gorsel_format,
            lbl.algoritma_sinyal or None,
            lbl.quality_score,
            lbl.quality_tier,
            lbl.hook_text,
            lbl.reasoning,
            datetime.now(timezone.utc),
            model_used,
        )
        for lbl in labels
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO tweet_labels (
                tweet_id,
                psikolojik_tetikleyici, primary_trigger,
                icerik_formu, ton, kanca_tipi, gorsel_format,
                algoritma_sinyal,
                quality_score, quality_tier,
                hook_text, reasoning, processed_at, model_used
            ) VALUES %s
            ON CONFLICT (tweet_id) DO UPDATE SET
                psikolojik_tetikleyici = EXCLUDED.psikolojik_tetikleyici,
                primary_trigger        = EXCLUDED.primary_trigger,
                icerik_formu           = EXCLUDED.icerik_formu,
                ton                    = EXCLUDED.ton,
                kanca_tipi             = EXCLUDED.kanca_tipi,
                gorsel_format          = EXCLUDED.gorsel_format,
                algoritma_sinyal       = EXCLUDED.algoritma_sinyal,
                quality_score          = EXCLUDED.quality_score,
                quality_tier           = EXCLUDED.quality_tier,
                hook_text              = EXCLUDED.hook_text,
                reasoning              = EXCLUDED.reasoning,
                processed_at           = EXCLUDED.processed_at,
                model_used             = EXCLUDED.model_used
            """,
            rows,
        )

        # lab_processed güncelle
        tweet_ids = [lbl.tweet_id for lbl in labels]
        cur.execute(
            "UPDATE tweets SET lab_processed = TRUE, hook_text = tl.hook_text "
            "FROM tweet_labels tl "
            "WHERE tweets.tweet_id = tl.tweet_id AND tweets.tweet_id = ANY(%s)",
            (tweet_ids,),
        )

    conn.commit()
    return len(rows)


# ─────────────────────────────────────────────
# Ana işleyici
# ─────────────────────────────────────────────

def process_queue(
    conn,
    total_limit: int = 1000,
    batch_size: int = 20,
    dry_run: bool = False,
    model: str = "auto",
) -> Dict[str, int]:
    # Model seç
    if model == "auto":
        if os.getenv("OPENAI_API_KEY"):
            model_used = "gpt-4o-mini"
        elif os.getenv("ANTHROPIC_API_KEY"):
            model_used = "claude-3-5-haiku-20241022"
        else:
            raise RuntimeError("OPENAI_API_KEY veya ANTHROPIC_API_KEY gerekli")
    else:
        model_used = model

    # Toplam bekleyen
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tweets WHERE lab_processed = FALSE")
        pending = cur.fetchone()[0]

    logger.info(f"Lab queue: {pending} tweet bekliyor | model: {model_used} | batch: {batch_size}")

    if dry_run:
        logger.info("Dry-run modu — hiçbir şey yazılmayacak")
        return {"pending": pending}

    total_processed = 0
    total_errors    = 0

    while total_processed < min(total_limit, pending):
        tweets = fetch_unprocessed(conn, limit=batch_size)
        if not tweets:
            break

        logger.info(f"  Batch sınıflandırılıyor: {len(tweets)} tweet...")

        try:
            raw_labels = classify_batch(tweets, model_used)
        except Exception as e:
            logger.error(f"  LLM hatası: {e}")
            total_errors += len(tweets)
            time.sleep(5)  # kısa bekle, devam et
            continue

        labels: List[LabLabel] = []
        for rl in raw_labels:
            try:
                lbl = LabLabel(
                    tweet_id=rl["tweet_id"],
                    psikolojik_tetikleyici=rl.get("psikolojik_tetikleyici", []),
                    primary_trigger=rl.get("primary_trigger"),
                    icerik_formu=rl.get("icerik_formu"),
                    ton=rl.get("ton"),
                    kanca_tipi=rl.get("kanca_tipi"),
                    gorsel_format=rl.get("gorsel_format"),
                    algoritma_sinyal=rl.get("algoritma_sinyal", []),
                    quality_score=rl.get("quality_score"),
                    hook_text=rl.get("hook_text"),
                    reasoning=rl.get("reasoning"),
                    model_used=model_used,
                )
                labels.append(lbl)
            except Exception as e:
                logger.warning(f"  Label parse hatası ({rl.get('tweet_id')}): {e}")
                total_errors += 1

        written = write_labels(conn, labels, model_used)
        total_processed += written
        logger.info(f"  ✓ {written} label yazıldı | toplam: {total_processed}")

        # Rate limit: OpenAI gpt-4o-mini için ihtiyatlı bekle
        time.sleep(1)

    logger.info(f"\n✅ Lab queue tamamlandı: {total_processed} işlendi, {total_errors} hata")
    return {"processed": total_processed, "errors": total_errors}


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TwitterYoldas Lab Processor")
    parser.add_argument("--limit",      type=int, default=1000, help="Maks işlenecek tweet (varsayılan: 1000)")
    parser.add_argument("--batch-size", type=int, default=20,   help="LLM batch büyüklüğü (varsayılan: 20)")
    parser.add_argument("--model",      type=str, default="auto", help="gpt-4o-mini | claude-3-5-haiku-20241022 | auto")
    parser.add_argument("--dry-run",    action="store_true",    help="Sadece sayıları göster, yazma")
    args = parser.parse_args()

    conn = get_connection()
    try:
        process_queue(
            conn,
            total_limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            model=args.model,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
