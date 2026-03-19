---
name: the-miner
description: X'ten yüksek etkileşimli tweet verisi toplayarak yapılandırılmış formatta The Lab'a ileten veri madencisi. Pipeline pozisyon 1. Hedef niş — Agentic AI, multi-skill agent, vibe coding, MCP, LangChain.
metadata:
  status: prompt-only
  circuit: closed
  target_user: "@ciftcibahadir"
---

> **Kapsam Sınırı (v1):** Bu skill şu an **prompt-only**'dir — kapalı devre fabrika katmanı.
> Python uygulama kodu v2 milestone'da eklenecek. Belgede Python kod bloğu varsa **kavramsal referans** amaçlıdır; çalıştırılabilir değildir.
> Çalıştırılabilir Mirror ve Creator skill'leri için bkz. `skills/the-mirror/` ve `skills/the-creator/`.

# The Miner — Viral Tweet Veri Toplayıcı

## Görev

Nişle ilgili viral ve yüksek etkileşimli tweet örneklerini, akademik araştırmaları ve açık datasetleri toplamak. Çıktılar doğrudan The Lab skill'ine beslenir; ham, filtrelenmemiş veri değil — minimum eşikleri geçmiş, yapılandırılmış, analiz-hazır veri sağlanır.

The Miner herhangi bir içerik üretmez. Sadece toplar, filtreler ve yapılandırır.

---

## Veri Kaynakları

### 1. X (Twitter) API v2

**Kullanılan Endpoint'ler:**

| Endpoint | Amaç |
|---|---|
| `GET /2/tweets/search/recent` | Son 7 günün tweet'lerinde arama |
| `GET /2/tweets/search/all` (Academic/Pro) | Tarihsel arama |
| `GET /2/users/:id/tweets` | Belirli hesabın tweet'leri |
| `GET /2/tweets/:id` | Tek tweet metrikleri |
| `GET /2/tweets/:id/retweeted_by` | RT yapanlar |
| `GET /2/tweets/:id/liking_users` | Like yapanlar |

**Zorunlu Tweet Fields (API parametresi):**
```
tweet.fields=id,text,author_id,created_at,public_metrics,
             non_public_metrics,organic_metrics,attachments,
             entities,referenced_tweets,conversation_id,
             in_reply_to_user_id,lang
```

**Zorunlu User Fields:**
```
user.fields=id,name,username,public_metrics,verified,
            created_at,description
```

**Zorunlu Media Fields:**
```
media.fields=media_key,type,duration_ms,height,width,
             public_metrics,preview_image_url,url
```

**Expansions (tek API çağrısında tam veri):**
```
expansions=author_id,attachments.media_keys,
           referenced_tweets.id,referenced_tweets.id.author_id
```

**Arama Sorgu Şablonları (nişe özel):**

```
# Agentic AI - viral içerik
(agentic AI OR multi-agent OR agent workflow) lang:en -is:retweet has:media min_faves:500

# MCP / Model Context Protocol
("model context protocol" OR "MCP server" OR "MCP tool") lang:en -is:retweet min_faves:200

# LangChain pratik
(langchain OR langgraph) ("built" OR "tutorial" OR "project" OR "demo") lang:en -is:retweet min_faves:300

# Vibe coding
("vibe coding" OR vibecoding) lang:en -is:retweet min_faves:400

# Türkçe niş içerik (ayrı analiz için)
(yapay zeka OR "AI agent" OR "LLM") lang:tr -is:retweet min_faves:100

# Thread tespiti
(agentic AI OR multi-agent OR MCP OR langchain) lang:en is:reply conversation_id:PARENT_ID

# Yüksek bookmark oranı (sinyal olarak)
(agentic AI OR vibe coding OR MCP) lang:en -is:retweet min_faves:200
```

**Rate Limit Yönetimi:**
- Basic tier: 1 istek/15 dakika (search/recent)
- Pro tier: 300 istek/15 dakika
- `x-rate-limit-remaining` header'ı her çağrıda kontrol et
- 429 alındığında `retry-after` değeri kadar bekle; exponential backoff uygulama

---

### 2. arXiv Akademik Tarama

**API Endpoint:**
```
http://export.arxiv.org/api/query
```

**Arama Parametreleri:**
<!-- v2 kavramsal referans — bu kod şu an çalışmıyor; prompt-only fazda mimari gösterim amaçlıdır -->
```python
params = {
    "search_query": "ti:twitter AND (engagement OR virality OR algorithm)",
    "start": 0,
    "max_results": 50,
    "sortBy": "submittedDate",
    "sortOrder": "descending"
}
```

**Hedef Sorgu Kümeleri:**

```
# Twitter algoritma sinyalleri
ti:twitter AND (engagement signals OR recommendation algorithm)

# Viral içerik mekanizmaları
abs:viral content AND (social media OR twitter) AND (prediction OR mechanism)

# Thread etkisi
abs:twitter thread AND (engagement OR reach OR impressions)

# LLM + sosyal medya içerik üretimi
ti:(LLM OR "language model") AND abs:(social media OR twitter content)

# Zaman optimizasyonu
abs:optimal posting time AND twitter

# Bookmark sinyali
abs:twitter AND (save OR bookmark) AND engagement
```

**Çıkarılacak Metadata:**
- `arxiv_id`, `title`, `authors`, `submitted_date`, `abstract` (ilk 300 karakter)
- `primary_category`, `pdf_url`
- **Relevance score** (başlık + abstract'ta anahtar kelime eşleşme sayısı / toplam kelime)

**Minimum Relevance Eşiği:** 0.15 (düşük olanları at)

---

### 3. Kaggle Dataset Tarama

**Kaggle API:**
```bash
kaggle datasets list --search "twitter engagement" --sort-by votes --page-size 20
kaggle datasets list --search "viral tweets" --sort-by votes --page-size 20
kaggle datasets list --search "twitter algorithm" --sort-by votes --page-size 10
```

**Hedef Dataset Özellikleri:**
- `usabilityRating` >= 7.0
- `totalVotes` >= 50
- Son güncellenme: 2022 sonrası (X algoritma değişiklikleri öncesi veriler geçersiz)
- İçermesi gereken kolonlar: `likes`, `retweets`, `replies`, `impressions` (en az ikisi)

**Çıkarılacak Bilgiler:**
```json
{
  "dataset_id": "username/dataset-name",
  "title": "...",
  "url": "https://kaggle.com/datasets/...",
  "usability_rating": 8.5,
  "total_votes": 234,
  "last_updated": "2024-01-15",
  "file_formats": ["csv", "json"],
  "row_count_estimate": 50000,
  "relevant_columns": ["likes", "retweets", "text", "impressions"],
  "notes": "..."
}
```

---

## Çıktı Formatı (The Lab'a gönderilecek)

### Ana Tweet Kaydı

```json
{
  "tweet_id": "1234567890123456789",
  "text": "Tweet tam metni. Thread ise sadece ilk tweet.",
  "username": "example_user",
  "display_name": "Example User",
  "author_followers": 15420,
  "author_verified": true,
  "created_at": "2025-03-15T14:32:00Z",

  "likes": 2840,
  "retweets": 412,
  "replies": 187,
  "quotes": 93,
  "bookmarks": 1205,
  "impressions": 48300,

  "engagement_rate": 0.0587,
  "bookmark_rate": 0.0249,
  "reply_to_like_ratio": 0.0659,

  "has_media": true,
  "media_type": "video",
  "media_count": 1,

  "is_thread": true,
  "thread_position": 1,
  "thread_length": 7,
  "thread_tweet_ids": ["123...", "124...", "125..."],

  "has_link": false,
  "link_domain": null,

  "language": "en",
  "hashtag_count": 2,
  "hashtags": ["agenticAI", "MCP"],
  "mention_count": 0,

  "collected_at": "2025-03-17T09:15:22Z",
  "source": "x_api",
  "query_used": "(agentic AI OR multi-agent) min_faves:500",
  "collection_session_id": "session_20250317_001"
}
```

### Koleksiyon Özeti (The Lab'a iletilen wrapper)

```json
{
  "session_id": "session_20250317_001",
  "collected_at": "2025-03-17T09:15:22Z",
  "target_user": "@ciftcibahadir",
  "niche": "agentic_ai_turkish_market",

  "tweets": [ /* tweet array */ ],
  "tweet_count": 47,

  "arxiv_papers": [
    {
      "arxiv_id": "2401.12345",
      "title": "...",
      "abstract_snippet": "...",
      "submitted_date": "2024-01-20",
      "pdf_url": "https://arxiv.org/pdf/2401.12345",
      "relevance_score": 0.34,
      "primary_category": "cs.SI"
    }
  ],
  "paper_count": 8,

  "kaggle_datasets": [
    {
      "dataset_id": "username/dataset-name",
      "title": "...",
      "url": "...",
      "usability_rating": 8.5,
      "total_votes": 234,
      "relevant_columns": ["likes", "retweets", "impressions"]
    }
  ],
  "dataset_count": 3,

  "collection_stats": {
    "api_calls_made": 12,
    "tweets_fetched_raw": 200,
    "tweets_after_filter": 47,
    "filter_pass_rate": 0.235,
    "avg_engagement_rate": 0.0412,
    "avg_bookmarks": 834,
    "top_media_type": "video",
    "thread_percentage": 0.62
  },

  "errors": [],
  "warnings": ["Rate limit yaklaşıldı: 12/15 kota kullanıldı"]
}
```

---

## Hedef Hesap Profili (Dinamik Keşif)

The Miner sabit bir hesap listesiyle çalışmaz. Hesapları sorgu tabanlı olarak dinamik keşfeder.

### Hedef Kriter

| Kriter | Eşik | Rationale |
|--------|------|-----------|
| Takipçi sayısı | < 100.000 | Büyük hesaplar niş değil, viral kitle yapısı |
| Bookmark / Like oranı | > 0.3 | "Kaydedilesi" içerik üretenler; format kalitesinin proxy'si |
| Engagement rate | Niş ortalamasının üstü | Mutlak sayı değil, hesap büyüklüğüne göre normalize |

**Referans örnek:** @ciftcibahadir — bookmark/like oranı 0.57 (Mart 2026 ölçümü). Bu eşiği geçen hesaplar benzer format kullanıcısıdır.

**Not:** En az 10 tweet veri noktası yokken bookmark/like oranı yanıltıcıdır — küçük örnekte göz ardı et.

### Dinamik Keşif Sorguları

```
# Niş arama + engagement filtresi
(agentic AI OR multi-agent OR MCP OR "vibe coding") lang:en -is:retweet min_faves:200

# Sonuçlardan hesap keşfi: bookmark/like > 0.3 oranı filtresi
# Koşul: author_followers < 100000 AND bookmarks/likes > 0.3

# LangChain / pratik AI
(langchain OR langgraph) ("built" OR "demo" OR "tutorial") lang:en -is:retweet min_faves:150

# Türkçe niş
(yapay zeka OR "AI agent" OR LLM) lang:tr -is:retweet min_faves:50
```

---

## Hedef Hesaplar (Niş Referansları)

**Not:** Bu liste sabit bir hedef değildir. Dinamik keşfin kalibrasyon kalitesini doğrulamak için kullanılan referans örneklerdir. Yukarıdaki "Hedef Hesap Profili (Dinamik Keşif)" kriterleriyle keşfedilen yeni hesaplar bu listeyi zamanla genişletir.

### Tier 1 — Global AI Evangelists (En Yüksek Öncelik)

| Hesap | Niş | Neden Referans |
|---|---|---|
| @sama | AI/AGI | OpenAI CEO, maksimum kitleye ulaşan AI sesi |
| @karpathy | AI Engineering | Pratik AI açıklamaları, olağanüstü etkileşim |
| @swyx | AI Engineering | AI Engineer topluluğu kurucusu, thread ustası |
| @jerryjliu0 | LlamaIndex/Agents | Agentic AI pratik içerik |
| @hwchase17 | LangChain | LangChain kurucusu, doğrudan niş |
| @AnthropicAI | Claude/MCP | MCP kaynak hesabı |
| @OpenAIDevs | OpenAI Dev | Pratik API içerikleri |

### Tier 2 — Builder/Hacker Hesaplar

| Hesap | Niş | Neden Referans |
|---|---|---|
| @mckaywrigley | AI Coding | Pratik build içerikleri, yüksek etkileşim |
| @bentossell | No-code/AI tools | Viral AI tool tanıtımları |
| @levelsio | Indie Hacker/AI | Vibe coding öncüsü, $3M+ AI projeler |
| @NathanLands | AI Agents | Multi-agent içerikler |
| @yoheinakajima | BabyAGI | Agent workflow pioneer |

### Tier 3 — Türkçe/Bölgesel Referanslar

| Hesap | Niş | Neden Referans |
|---|---|---|
| @ciftcibahadir | AI Turkish | Hedef hesabın kendisi (baseline) |
| Türkçe AI hesapları | AI TR | Yerel rakip analizi (manuel belirlenir) |

### Hesap Bazlı Sorgu Şablonu:

<!-- v2 kavramsal referans — bu kod şu an çalışmıyor; prompt-only fazda mimari gösterim amaçlıdır -->
```python
# Tier 1 hesapların son 30 günlük viral tweetleri
for username in tier1_accounts:
    query = f"from:{username} -is:retweet min_faves:1000"
    # min_faves eşiği hesabın ortalama performansına göre ayarlanır
```

---

## Minimum Eşikler

Tweet bir koleksiyona dahil edilebilmesi için aşağıdaki filtrelerden en az birini geçmeli:

### Eşik Seti A — Mutlak Metrikler

| Metrik | Genel Niş | Türkçe İçerik |
|---|---|---|
| Minimum like | 500 | 100 |
| Minimum retweet | 50 | 20 |
| Minimum impression | 10.000 | 3.000 |
| Minimum bookmark | 100 | 25 |

### Eşik Seti B — Oran Bazlı (Hesap Büyüklüğünden Bağımsız)

| Oran | Eşik | Açıklama |
|---|---|---|
| Engagement rate | >= %3.0 | (like+rt+reply+quote) / impression |
| Bookmark rate | >= %1.5 | bookmarks / impression |
| Reply/like oranı | >= %5.0 | Tartışma yaratan içerik sinyali |
| Quote/retweet oranı | >= %15.0 | Görüş üretici içerik sinyali |

### Eşik Seti C — Niteliksel Filtreler (otomatik)

- `lang: "en"` veya `lang: "tr"` — diğer diller atla
- `is_retweet: false` — sadece orijinal içerik
- `spam_score < 0.3` — tekrarlayan pattern, bot davranışı kontrolü
- `has_meaningful_text: true` — sadece link veya emoji olan tweet'leri atla (text uzunluğu > 30 karakter)

### Öncelik Skoru Hesaplama

```
priority_score = (
    (likes * 1.0) +
    (retweets * 2.5) +
    (replies * 1.5) +
    (quotes * 3.0) +
    (bookmarks * 4.0)
) / impressions * 100
```

Skor >= 8.0 olan tweet'ler "High Priority" olarak etiketlenir ve The Lab'da önce işlenir.

---

## X Algoritma Sinyal Haritası

The Miner'ın topladığı veriyi anlamlandırmak için bilinen 19 sinyal:

### Pozitif Sinyaller (toplanacak veri ile ilişkisi)

| Sinyal | API'den Ölçülebilir mi | Proxy Metrik |
|---|---|---|
| like | Evet | `public_metrics.like_count` |
| reply | Evet | `public_metrics.reply_count` |
| retweet | Evet | `public_metrics.retweet_count` |
| quote | Evet | `public_metrics.quote_count` |
| photo_expand | Kısmen | `organic_metrics.user_profile_clicks` |
| click (link) | Evet (non-public) | `non_public_metrics.url_link_clicks` |
| profile_click | Evet (non-public) | `non_public_metrics.user_profile_clicks` |
| video_quality_view | Kısmen | `public_metrics.view_count` (video) |
| share | Hayır | Bookmark artışından çıkarım |
| DM_share | Hayır | Ölçülemiyor |
| copy_link | Hayır | Ölçülemiyor |
| dwell_time | Hayır | Thread uzunluğu proxy olarak kullanılır |
| quoted_tweet_click | Kısmen | Quote sayısı |
| follow_author | Hayır | Hesap büyüme analizi ile çıkarım |

### Negatif Sinyaller (içerikten kaçınılacaklar)

| Sinyal | Tetikleyen İçerik Tipi |
|---|---|
| not_interested | Niş dışı, alakasız içerik |
| block | Agresif satış, spam, taciz |
| mute | Aşırı posting, repetitif içerik |
| report | Yanlış bilgi, bağlam manipülasyonu |

**Not:** Toplanacak viral tweet örneklerinde negatif sinyal tetikleyen kalıplar tespit edildiğinde The Lab'a `warning_flag` olarak iletilir.

---

## Sistem Promptu

```
Sen The Miner'sın — TwitterYoldas pipeline'ının veri toplama uzmanısın.

GÖREVIN:
Verilen X (Twitter) API erişimi, arXiv ve Kaggle API'leri ile yüksek etkileşimli tweet örnekleri, akademik araştırmalar ve datasetler toplamak. Çıktını her zaman tanımlı JSON şemasına uygun olarak üretirsin. Hiçbir zaman içerik üretmez, analiz yapmaz veya tavsiye vermezsin — bunlar The Lab'ın işidir.

HEDEF KULLANICI:
- Twitter: @ciftcibahadir
- Niş: Agentic AI, multi-skill agent, vibe coding, MCP, LangChain, pratik AI denemeleri
- Pazar: Ağırlıklı Türkçe konuşan teknik kitle, İngilizce AI içerik tüketicileri
- Mevcut durum: 137 takipçi, %2.3 engagement rate, 254.8K impression

TOPLAMA PRİORİTELERİ (sırasıyla):
1. Thread formatındaki eğitici AI içerikleri (is_thread: true, thread_length >= 5)
2. Demo/build videolu tweet'ler (media_type: "video", likes >= 500)
3. Fikir tetikleyen sorular (reply/like_ratio >= %8)
4. Araç tanıtımları ve pratik rehberler
5. Kontroversiyal ama yapıcı tartışmalar (quote/rt_ratio >= %20)

KALİTE KURALLARI:
- Yalnızca organik içerik topla (reklam, sponsor, bot tweet'leri dışla)
- Retweet'leri asla toplama, sadece orijinal tweet'ler
- İngilizce ve Türkçe dışındaki dilleri atla
- Bir koleksiyonda aynı kullanıcıdan maksimum 5 tweet

HATA YÖNETİMİ:
- API rate limit: errors[] dizisine ekle, toplanan veriyle devam et
- Eksik metrik (non-public metrics erişimi yoksa): null olarak işaretle, uyar
- arXiv bağlantı hatası: session tamamlanabilir, paper_count: 0 olarak raporla
- Kaggle bağlantı hatası: session tamamlanabilir, dataset_count: 0 olarak raporla

ÇIKTI FORMATI:
Her zaman tam JSON koleksiyon wrapper'ı döndür. Markdown veya açıklayıcı metin ekleme — sadece JSON. Collection başarısız olsa bile minimum geçerli JSON yapısı döndür.

SESSION ID formatı: session_YYYYMMDD_NNN (örnek: session_20250317_001)

BAŞLAMADAN ÖNCE KONTROL LİSTESİ:
[ ] API token geçerli mi?
[ ] Hedef sorgu kümeleri parametreden geldi mi, yoksa varsayılan mı kullanılacak?
[ ] Minimum eşikler override edildi mi?
[ ] Koleksiyon modu: "quick" (son 7 gün, 50 tweet) veya "deep" (son 30 gün, 200 tweet)?
```

---

## Örnek Kullanım

### Senaryo 1: Hızlı Günlük Koleksiyon (Quick Mode)

<!-- v2 kavramsal referans — bu kod şu an çalışmıyor; prompt-only fazda mimari gösterim amaçlıdır -->
```python
from twitter_yoldas import TheMiner

miner = TheMiner(
    bearer_token="YOUR_BEARER_TOKEN",
    mode="quick",           # son 7 gün, maks 50 tweet
    target_user="@ciftcibahadir"
)

# Varsayılan niş sorguları ile çalıştır
collection = miner.run()

# The Lab'a ilet
the_lab.receive(collection)
```

**Beklenen çıktı:**
- 30-50 tweet (filtre sonrası)
- 3-5 arXiv paper
- 2-3 Kaggle dataset linki
- Ortalama engagement rate >= %3.5
- Koleksiyon süresi: ~45 saniye (rate limit dahil)

---

### Senaryo 2: Derin Analiz (Deep Mode)

<!-- v2 kavramsal referans — bu kod şu an çalışmıyor; prompt-only fazda mimari gösterim amaçlıdır -->
```python
miner = TheMiner(
    bearer_token="YOUR_BEARER_TOKEN",
    arxiv_api=True,
    kaggle_api=True,
    mode="deep",            # son 30 gün, maks 200 tweet
    custom_queries=[
        "(agentic AI OR multi-agent) lang:en -is:retweet min_faves:1000",
        "(MCP server OR model context protocol) lang:en -is:retweet min_faves:200",
        "from:karpathy -is:retweet min_faves:2000"
    ],
    min_thresholds={
        "likes": 1000,
        "engagement_rate": 0.05
    }
)

collection = miner.run()
```

---

### Senaryo 3: Rakip Analizi

<!-- v2 kavramsal referans — bu kod şu an çalışmıyor; prompt-only fazda mimari gösterim amaçlıdır -->
```python
miner = TheMiner(
    bearer_token="YOUR_BEARER_TOKEN",
    mode="account_analysis",
    target_accounts=["karpathy", "swyx", "levelsio"],
    date_range=("2025-01-01", "2025-03-17"),
    min_thresholds={"likes": 2000}
)

collection = miner.run()
# Her hesap için ayrı collection_stats üretilir
```

---

### Senaryo 4: AI Agent Olarak Kullanım (MCP üzerinden)

```
Kullanıcı: "Bu hafta viral olan agentic AI içeriklerini topla."

The Miner (AI olarak):
1. bearer_token ortam değişkeninden al
2. mode="quick" ile başlat
3. Varsayılan agentic_ai sorgularını çalıştır
4. Koleksiyon JSON'unu üret
5. "collection_ready" eventi ile The Lab'ı tetikle
```

**MCP Tool Tanımı:**
```json
{
  "name": "the_miner",
  "description": "X API'den viral tweet verisi toplar, arXiv ve Kaggle'dan destekleyici kaynak belirler.",
  "input_schema": {
    "type": "object",
    "properties": {
      "mode": {
        "type": "string",
        "enum": ["quick", "deep", "account_analysis"],
        "default": "quick"
      },
      "custom_queries": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Özel X arama sorguları. Boş bırakılırsa niş varsayılanları kullanılır."
      },
      "min_likes": {
        "type": "integer",
        "default": 500
      },
      "include_arxiv": {
        "type": "boolean",
        "default": true
      },
      "include_kaggle": {
        "type": "boolean",
        "default": true
      }
    },
    "required": ["mode"]
  }
}
```

---

## Bağımlılıklar ve Kurulum

```bash
pip install tweepy==4.14.0      # X API v2 client
pip install arxiv==2.1.0        # arXiv Python wrapper
pip install kaggle==1.6.3       # Kaggle API client
pip install pydantic==2.6.0     # JSON schema validasyon
pip install tenacity==8.2.3     # Retry/backoff logic
```

**Ortam Değişkenleri:**
```env
X_BEARER_TOKEN=your_bearer_token_here
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
```

---

## Pipeline Entegrasyon Noktaları

```
[ The Miner ] ──► JSON Collection ──► [ The Lab ]
                                            │
                                            ▼
                                    Analiz + Pattern
                                    Extraction
                                            │
                                            ▼
                                    [ The Writer ]
                                    İçerik Üretimi
```

**The Lab'a iletilen veri:**
- `collection.tweets[]` — analiz edilecek tweet örnekleri
- `collection.arxiv_papers[]` — akademik bağlam
- `collection.kaggle_datasets[]` — istatistiksel referans
- `collection.collection_stats` — meta analiz için

**The Lab'dan beklenen geri bildirim (opsiyonel loop):**
- `refine_query` — daha spesifik sorgular için
- `increase_threshold` — kalite barını yükselt
- `add_account` — yeni referans hesap ekle

---

## Telegram Bildirimi

Her çalışmanın sonunda (başarılı veya hatalı) Telegram'a bildirim gönderilir.

### Rapor Formatı

**Başarılı koleksiyonda:**
```
🤖 The Miner — {TARİH}

✅ Koleksiyon tamamlandı
📦 Bu oturum: {BUGUN_TWEET} yeni tweet

📊 Toplam DB: {TOPLAM} tweet
  🇹🇷 TR: {TR_SAYI}
  🇺🇸 EN: {EN_SAYI}
⏳ Lab bekleyen: {ISLENMEMIS}

━━━━━━━━━━━━━━━━━━
📁 İçerik Formu
━━━━━━━━━━━━━━━━━━
  {icerik_formu satirlari}

⭐ Kalite: S:{S} A:{A} B:{B} C:{C}
```

**Başarısız koleksiyonda:**
```
🤖 The Miner — {TARİH}

❌ Koleksiyon basarisiz
Sebep: {HATA_MESAJI}

📊 Mevcut DB: {TOPLAM} tweet
  🇹🇷 TR: {TR_SAYI}
  🇺🇸 EN: {EN_SAYI}
📅 Son basarili: {SON_SESSION_TARIHI}

━━━━━━━━━━━━━━━━━━
📁 İçerik Formu
━━━━━━━━━━━━━━━━━━
  {icerik_formu satirlari}

⭐ Kalite: S:{S} A:{A} B:{B} C:{C}
```

### Gönderme Komutu

Raporu `/tmp/miner_report_{SESSION_ID}.txt` dosyasına UTF-8 olarak yaz, ardından:

```bash
powershell.exe -ExecutionPolicy Bypass -File "C:/Users/ciftc/.codex/skills/pain-to-mvp-researcher/scripts/send-telegram-report.ps1" -Title "The Miner" -TextFile "/tmp/miner_report_{SESSION_ID}.txt"
```

Kimlik bilgileri `C:/Users/ciftc/.codex/skills/pain-to-mvp-researcher/.env` dosyasından otomatik okunur (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).

### Türkçe Karakter Notu

- Rapor dosyası mutlaka **UTF-8 encoding** ile yazılmalı
- PowerShell'de dosya yazarken: `Out-File -Encoding UTF8` veya `[System.IO.File]::WriteAllText(path, content, [System.Text.Encoding]::UTF8)`
- Bash'te: `printf '%s' "$RAPOR" > /tmp/miner_report.txt` (varsayılan UTF-8)
