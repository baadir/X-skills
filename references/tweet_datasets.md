# Tweet Engagement Dataset Kaynakları

> Son güncelleme: 2026-03-17
> Durum: Kaynaklar belgelendi, erişim yöntemleri detaylandırıldı

---

## Mevcut Açık Dataset'ler

### 1. Twitter Virality Prediction Dataset (Kaggle)
- **URL:** https://www.kaggle.com/datasets/tariqsays/virality-of-tweet-dataset
- **İçerik:** Tweet metni + retweet sayısı + like sayısı + kullanıcı özellikleri
- **Boyut:** ~40K tweet
- **Erişim:** Kaggle hesabı gerekli, API ile indirilebilir
- **Sütunlar:** text, retweet_count, favorite_count, user_followers_count, user_friends_count, hashtags, media_count

### 2. Twitter Trending Tweets (Kaggle)
- **URL:** https://www.kaggle.com/datasets/heitornunes/twitter-career-data
- **İçerik:** Trending tweet'ler + engagement metrikleri
- **Erişim:** Kaggle hesabı gerekli

### 3. Social Media Influencers Dataset (GitHub)
- **URL:** https://github.com/Social-media-dataset-samples
- **İçerik:** 1.000+ record, multi-platform
- **Erişim:** Açık, doğrudan indirilebilir

### 4. Retweet Prediction Dataset (Research)
- **Paper:** "Can Cascades be Predicted?" (Cheng et al., 2014)
- **İçerik:** Twitter'da cascade büyüme tahmini için tweet + engagement verisi
- **Erişim:** Stanford SNAP üzerinden: https://snap.stanford.edu/data/

### 5. Twitter100k (Research)
- **İçerik:** 100K tweet + retweet sayıları + zaman serileri
- **Kaynak:** Araştırma topluluklarında dolaşımda
- **Erişim:** Farklı GitHub repolarından bulunabilir

---

## Kendi Tweet'lerini Okuma — twikit 2.3.3 (v1 Birincil Yöntem)

**Kütüphane:** twikit 2.3.3 — cookie tabanlı auth
**Uygulama:** `skills/the-mirror/mirror_sync.py`
**Neden twikit:** tweepy Free tier `impression_count` null döndürür; twikit `view_count` dolu döndürür.

> **Phase 1 kararı (2026-03-17):** mirror_sync.py tweepy'den twikit 2.3.3'e migrate edildi.
> Detay: `decision.md` — "Phase 1 — twikit Migration ve Async Pattern Kararları" girdisi.

---

## Skill için Önerilen Veri Toplama Yöntemi

Hazır dataset'ler ya engagement metriği eksik ya da nişe özgü değil.
**En doğru yaklaşım: X API v2 ile hedef nişteki yüksek etkileşimli tweet'leri toplamak.**

### X API v2 ile Veri Toplama Script'i — ⚠️ v1'de kullanılmıyor

> **Not:** Bu script tweepy kullanır. tweepy Free tier'da `impression_count` null döner — bu nedenle v1'de twikit'e geçildi. Aşağıdaki script arşiv amaçlıdır.

```python
import tweepy
import json
import csv
from datetime import datetime, timedelta

# X API v2 Bearer Token
client = tweepy.Client(bearer_token="YOUR_BEARER_TOKEN")

# Hedef hesaplar (AI/agentic nişi)
TARGET_ACCOUNTS = [
    "levelsio",      # Indie hacker, yüksek engagement
    "karpathy",      # AI araştırmacı, viral thread'ler
    "goodside",      # AI pratisyen
    "sama",          # OpenAI CEO
    "fchollet",      # Deep learning uzmanı
    "emollick",      # AI + eğitim
    "mattshumer_",   # AI ürün
    "ciftcibahadir"  # Kendi hesabın
]

def collect_high_engagement_tweets(username, min_likes=50):
    """Bir hesabın yüksek etkileşimli tweet'lerini topla"""
    user = client.get_user(username=username)
    user_id = user.data.id

    tweets = client.get_users_tweets(
        id=user_id,
        max_results=100,
        tweet_fields=["public_metrics", "created_at", "text", "attachments"],
        media_fields=["type", "duration_ms"],
        expansions=["attachments.media_keys"]
    )

    results = []
    for tweet in tweets.data:
        metrics = tweet.public_metrics
        if metrics["like_count"] >= min_likes:
            results.append({
                "username": username,
                "tweet_id": tweet.id,
                "text": tweet.text,
                "likes": metrics["like_count"],
                "retweets": metrics["retweet_count"],
                "replies": metrics["reply_count"],
                "bookmarks": metrics.get("bookmark_count", 0),
                "impressions": metrics.get("impression_count", 0),
                "engagement_rate": (
                    metrics["like_count"] + metrics["retweet_count"] + metrics["reply_count"]
                ) / max(metrics.get("impression_count", 1), 1),
                "created_at": str(tweet.created_at),
                "has_media": bool(tweet.attachments),
                "is_reply": tweet.text.startswith("@"),
                "is_thread": False  # Manuel işaretleme gerekir
            })

    return results

# Tüm hesaplardan veri topla
all_tweets = []
for account in TARGET_ACCOUNTS:
    try:
        tweets = collect_high_engagement_tweets(account, min_likes=50)
        all_tweets.extend(tweets)
        print(f"{account}: {len(tweets)} yüksek etkileşimli tweet bulundu")
    except Exception as e:
        print(f"{account} hatası: {e}")

# CSV'ye kaydet
with open("high_engagement_tweets.csv", "w", newline="", encoding="utf-8") as f:
    if all_tweets:
        writer = csv.DictWriter(f, fieldnames=all_tweets[0].keys())
        writer.writeheader()
        writer.writerows(all_tweets)

print(f"Toplam {len(all_tweets)} tweet kaydedildi.")
```

### Gerekli Kurulum
```bash
pip install tweepy
# X Developer Portal'dan Bearer Token al: https://developer.twitter.com/
```

---

## Skill'e Entegrasyon Planı

Toplanan veri `references/high_performing_tweets.csv` olarak kaydedilecek.
Skill bu CSV'yi şu şekilde kullanacak:
1. **Pattern analizi:** Hangi yapılar yüksek like/RT alıyor?
2. **Kanca örnekleri:** İlk tweet nasıl açılıyor?
3. **Format analizi:** Video/görsel içerenler vs sadece metin
4. **Niş kıyaslama:** "Bu kanca @karpathy'nin X engagementlı tweetiyle benzer yapıda"

---

## Alternatif: Manuel Kurasyon

X API erişimi yoksa, `references/curated_examples.md` dosyasına elle eklenecek:
- Tweet metni
- Engagement rakamları
- Tarih
- Neden tuttuğuna dair analiz
- Algoritma sinyali bağlantısı (x_algorithm_signals.md'den)
