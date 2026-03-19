---
name: the-lab
description: The Miner'dan gelen ham tweet verisini Batch API ile stratejik kategorilere ayırır. Her tweet için 6 boyutlu sınıflandırma etiketi üretir; çıktıyı The Mirror ve The Creator'a iletir. Pipeline pozisyon 2.
metadata:
  status: prompt-only
  circuit: closed
---

> **Kapsam Sınırı (v1):** Bu skill şu an **prompt-only**'dir — kapalı devre fabrika katmanı.
> Python uygulama kodu v2 milestone'da eklenecek. The Lab şu an LLM (Batch API) ile çalışır;
> bu belge o LLM'e verilen talimatları tanımlar.
> Çalıştırılabilir Mirror ve Creator skill'leri için bkz. `skills/the-mirror/` ve `skills/the-creator/`.

# The Lab — Stratejik Tweet Sınıflandırıcı

---

## Görev

The Miner, ham tweet listesini (metin + engagement metrikleri) teslim eder. The Lab bu listeyi okur ve her tweet için şu soruları yanıtlar:

- Bu tweet neden tuttu? Hangi psikolojik mekanizmayı devreye soktu?
- Hangi içerik yapısını kullandı?
- Hangi tonu benimsedi?
- Kancası ne tür bir kanca?
- Görsel format kullanıldı mı?
- X algoritması açısından hangi engagement sinyallerini tetiklemiş olabilir?

Bu soruların yanıtları JSON etiket olarak tweet verisine eklenir. Sonuç:

- **The Mirror'a** gider → kişisel stil karşılaştırması için referans taban oluşturur
- **The Creator'a** gider → yeni tweet üretirken hangi yapıları kullanacağına karar vermesi için kanıt tabanı sağlar

The Lab asla içerik üretmez. Sadece sınıflandırır ve özetler.

---

## Sınıflandırma Şeması

Her tweet için aşağıdaki 6 boyut etiketlenir. Tüm etiketler Türkçe sabittir; bu listeden seçilir.

### Boyut 1 — Psikolojik Tetikleyici

Tweeti okuyunca hangi temel duygu devreye giriyor?

| Etiket | Ne zaman seçilir |
|--------|-----------------|
| `Öfke` | "Bu yanlış", "Bu adaletsizlik", "Bunu kim kabul eder?" tepkisi tetikliyorsa |
| `FOMO` | "Bunu kaçırırsam geri kalırım" hissi varsa; trendler, fırsatlar, yenilikler |
| `Merak` | "Nasıl?", "Neden?", "Gerçekten?" sorusu sormaya iter |
| `Mizah` | Gülümseme veya kahkaha refleksi tetikliyor |
| `Empati` | "Ben de bunu yaşadım / yaşıyorum" tanınma hissi |
| `Şok` | Beklentiyi kıran, beklenmedik veri veya iddia; "Dur ne?" anı |
| `Gurur` | "Bu benim nişim, bunu biliyorum" onaylama veya aidiyet hissi |

Birden fazla seçilebilir, ama ana tetikleyici ilk sıraya yazılır.

### Boyut 2 — İçerik Formu

Tweeti yapısal olarak hangi format taşıyor?

| Etiket | Tanım |
|--------|-------|
| `Liste` | "5 şey", "3 neden", numaralı veya maddeli yapı |
| `Thread` | Birden fazla tweet zinciri; birinci tweet kanca görevi görür |
| `Soru` | Doğrudan soru soran; cevap bekler |
| `Karşıt_Görüş` | Yaygın kanıya itiraz eder; "Aslında…", "Herkes X diyor ama…" |
| `Hikaye` | Kişisel veya üçüncü şahıs anlatısı; başlangıç-orta-son |
| `Veri_Paylaşımı` | Rakam, istatistik, grafik, araştırma bulgusu |
| `Deneyim` | "Ben bunu yaptım, şunu gördüm" birinci şahıs pratik gözlem |

### Boyut 3 — Ton

Yazarın sesi nasıl bir karakter taşıyor?

| Etiket | Ses karakteri |
|--------|--------------|
| `Alaycı` | İnce veya açık ironi, espri silahı olarak kullanılıyor |
| `Profesyonel` | Mesafeli, otoriter, jargon ağırlıklı |
| `Samimi` | Kişisel, "sen-ben" dili, güven inşası |
| `Heyecanlı` | Enerji yüksek, ünlem, büyük kelimeler |
| `Sakin` | Düşük ses, analitik, abartısız |
| `Eğitici` | Adım adım açıklayan, okuru bilgilendirmeye odaklı |

### Boyut 4 — Kanca Tipi

Tweeti (veya thread'in ilk tweetini) açmaya iten ilk cümle/yapı ne?

| Etiket | Örüntü |
|--------|--------|
| `Şok_İddiası` | "X yanlış.", "Herkes bunu hatalı yapıyor.", "Bu beni değiştirdi." |
| `Soru` | Cevabı okuyucu için belirsiz olan açık soru |
| `Rakam` | "7 yılda", "%83'ü", "10K follower'a" gibi somut sayı açılışı |
| `Kişisel_Hata` | "Yanlış yaptım", "Keşke bilseydim", zafiyet kancası |
| `Karşılaştırma` | "X vs Y", "Önce / Sonra", iki şeyi yan yana koyma |
| `Trend_Bağlantısı` | Güncel olay, viral konu veya çıkan araçla bağlantı |

### Boyut 5 — Görsel Format

Tweet medya içeriyor mu?

| Etiket | Koşul |
|--------|-------|
| `Video` | Video eki var |
| `Görsel` | Fotoğraf veya infografik var |
| `GIF` | GIF var |
| `Yok` | Sadece metin |

### Boyut 6 — Algoritma Sinyal Tahmini

Bu tweet X algoritmasının hangi engagement sinyallerini tetiklemiş olabilir? `x_algorithm_signals.md` referansına dayanılarak tahmin yapılır.

| Etiket | Ne anlama gelir |
|--------|----------------|
| `like_odaklı` | Duygusal rezonans yüksek; hızlı like refleksi tetikliyor |
| `retweet_odaklı` | "Bunu paylaşayım" isteği güçlü; explicit veya implicit CTA var |
| `reply_odaklı` | Soru, tartışma veya karşıt görüş; yorum bırakmayı tetikliyor |
| `bookmark_odaklı` | Referans değeri yüksek; "bunu saklayayım" hissi |
| `dwell_odaklı` | Uzun okunma süresi; thread, veri yoğun veya detaylı içerik |
| `dm_share_odaklı` | "Bunu şuna göndereyim" tetikleyici; çok kişisel veya çok değerli |
| `follow_odaklı` | "Bu kişiyi takip etmeliyim" hissi; profil kimliğini öne çıkarıyor |

Birden fazla seçilebilir, güç sırasına göre dizilir.

---

## Batch API Prompt Şablonu

Bu şablon her tweet için Batch API'ye gönderilir. Aynı sistem promptuyla toplu işlem yapılır.

### Sistem Promptu

```
Sen bir Twitter içerik analisti ve X algoritması uzmanısın.
Sana bir tweet metni ve engagement metrikleri verilecek.
Görevin: tweeti 6 boyutlu sınıflandırma şemasına göre analiz etmek ve JSON formatında çıktı vermek.

Sınıflandırma kuralları:
- Her boyut için yalnızca şemada tanımlı etiketleri kullan. Yeni etiket icat etme.
- Psikolojik Tetikleyici ve Algoritma Sinyal Tahmini birden fazla etiket kabul eder (en fazla 3).
  Diğer boyutlar yalnızca 1 etiket alır.
- Birden fazla etiket varsa güç sırasına göre diz (en güçlüsü önce).
- primary_trigger alanına en baskın psikolojik tetikleyiciyi tek etiket olarak yaz.
- quality_score: 1-10 arası tam sayı. Kriterleri:
    10 → Çok güçlü kanca + net psikolojik tetikleyici + yüksek engagement metrikleri
    7-9 → İyi kanca, belirgin tetikleyici, ortalamanın üstü engagement
    4-6 → Orta kanca, zayıf tetikleyici veya düşük engagement
    1-3 → Zayıf kanca, belirsiz yapı, düşük engagement
- reasoning alanına 1-2 cümle Türkçe açıklama yaz. Neden bu etiketleri seçtiğini belirt.
- Emin olamadığın bir boyut için en yakın etiketi seç; asla null veya boş bırakma.
```

### Kullanıcı Promptu (Her Tweet İçin)

```
Aşağıdaki tweet metnini ve engagement metriklerini analiz et.

--- TWEET ---
Metin: {tweet_text}
Like: {like_count}
Retweet: {retweet_count}
Reply: {reply_count}
Bookmark: {bookmark_count}
İmpresyon: {impression_count}
Medya: {media_type}  // "video" | "görsel" | "gif" | "yok"
Tweet türü: {tweet_type}  // "standalone" | "thread_head" | "thread_continuation" | "reply"
Yazar niş: {author_niche}  // örn. "Agentic AI, vibe coding, MCP"
Yayın tarihi: {published_at}
--- /TWEET ---

Aşağıdaki JSON formatında çıktı ver. Başka hiçbir şey yazma.

{
  "tweet_id": "{tweet_id}",
  "labels": {
    "psikolojik_tetikleyici": ["{birincil}", "{ikincil_opsiyonel}"],
    "primary_trigger": "{en_baskın_tek_etiket}",
    "icerik_formu": "{tek_etiket}",
    "ton": "{tek_etiket}",
    "kanca_tipi": "{tek_etiket}",
    "gorsel_format": "{tek_etiket}",
    "algoritma_sinyal_tahmini": ["{en_guclü}", "{ikinci}", "{ucuncu_opsiyonel}"]
  },
  "quality_score": {1_ile_10_arasi_tam_sayi},
  "hook_text": "{tweetteki_kanca_cumlesini_buraya_aynen_koy_max_280_karakter}",
  "reasoning": "{1-2 cümle Türkçe açıklama}"
}
```

### Batch Gönderim Yapısı (OpenAI Batch API)

```jsonl
{"custom_id": "tweet-001", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "<sistem_promptu>"}, {"role": "user", "content": "<doldurulmuş_kullanıcı_promptu>"}], "temperature": 0.1, "max_tokens": 400, "response_format": {"type": "json_object"}}}
{"custom_id": "tweet-002", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "<sistem_promptu>"}, {"role": "user", "content": "<doldurulmuş_kullanıcı_promptu>"}], "temperature": 0.1, "max_tokens": 400, "response_format": {"type": "json_object"}}}
```

### Model Seçim Rehberi

| Senaryo | Önerilen Model | Tahmini Maliyet |
|---------|---------------|----------------|
| Standart analiz, yüksek hacim | GPT-4o-mini (Batch) | ~$3.75-5 / 1M tweet |
| Maliyet öncelikli | Gemini 1.5 Flash (Batch) | ~$1.5-3 / 1M tweet |
| Nüanslı analiz, düşük hacim | GPT-4o (Batch) | ~$12.5-15 / 1M tweet |
| Test / doğrulama | GPT-4o-mini (Sync) | ~$7.5-10 / 1M tweet |

Batch API %50 indirim uygular. `temperature: 0.1` sabit tutulmalıdır — sınıflandırma deterministik olmalı.

### Hata Yönetimi

- JSON parse hatası alınırsa o tweet `"parse_error": true` ile işaretlenir, atlanmaz.
- `quality_score` eksikse tweet `"incomplete": true` ile işaretlenir.
- Batch sonucu `custom_id` ile eşleştirilir; sıra kayması olmaz.

---

## Çıktı Formatı

The Miner çıktısına eklenen alanlar. Mevcut alanlar korunur, `lab_analysis` nesnesi eklenir.

```json
{
  "tweet_id": "1234567890",
  "source_account": "@karpathy",
  "text": "The thing about LLMs that most people miss...",
  "published_at": "2025-11-03T14:22:00Z",
  "metrics": {
    "like_count": 4821,
    "retweet_count": 612,
    "reply_count": 203,
    "bookmark_count": 1340,
    "impression_count": 187000,
    "engagement_rate": 0.0351
  },
  "media_type": "yok",
  "tweet_type": "thread_head",
  "lab_analysis": {
    "labels": {
      "psikolojik_tetikleyici": ["Merak", "Şok"],
      "primary_trigger": "Merak",
      "icerik_formu": "Thread",
      "ton": "Eğitici",
      "kanca_tipi": "Şok_İddiası",
      "gorsel_format": "Yok",
      "algoritma_sinyal_tahmini": ["dwell_odaklı", "bookmark_odaklı", "retweet_odaklı"]
    },
    "quality_score": 9,
    "hook_text": "The thing about LLMs that most people miss...",
    "reasoning": "Güçlü merak kancası eksik bilgi hissi yaratıyor; thread yapısı dwell süresini artırıyor ve bookmark refleksini tetikliyor.",
    "processed_at": "2026-03-17T10:45:00Z",
    "model_used": "gpt-4o-mini-batch"
  }
}
```

### Tam Pipeline Çıktı Şeması

```json
{
  "$schema": "the-lab-output-v1",
  "pipeline_run_id": "run_20260317_001",
  "processed_at": "2026-03-17T10:45:00Z",
  "stats": {
    "total_tweets": 500,
    "successfully_labeled": 497,
    "parse_errors": 2,
    "incomplete": 1,
    "high_quality_count": 87,
    "model_used": "gpt-4o-mini-batch",
    "batch_cost_usd": 0.0042
  },
  "tweets": [
    { "...tweet_with_lab_analysis": "..." }
  ]
}
```

---

## Kalite Eşikleri

The Lab, `quality_score >= 7` olan tweetleri "yüksek kalite örnek" olarak işaretler. Bu işaretleme The Creator'ın referans havuzunu oluşturur.

### Otomatik Kalite Eşiği Kriterleri

Bir tweet "yüksek kalite örnek" sayılmak için şu koşulların en az 3'ünü sağlamalıdır:

| Kriter | Eşik |
|--------|------|
| Engagement rate | >= %3 |
| Like sayısı (mutlak) | >= 100 |
| Bookmark / Like oranı | >= %15 (güçlü "kaydetme değeri" sinyali) |
| Retweet / Like oranı | >= %8 (güçlü "paylaşma değeri" sinyali) |
| quality_score | >= 7 |
| Algoritma sinyali | `bookmark_odaklı` veya `dwell_odaklı` içeriyorsa bonus |

### Nişe Özel Bağlamsal Eşik

@ciftcibahadir hesabının niş bağlamı (Agentic AI, vibe coding, MCP) göz önüne alındığında:

- Nişin genel engagement rate'i düşüktür (~%1-3); dolayısıyla **%2+ engagement rate** bu niş için yüksek kalite eşiği sayılır.
- 137 takipçi bağlamında 50+ like mutlak olarak güçlüdür.
- Verified takipçi oranı (%35) yüksek olduğundan bookmark ve DM share sinyalleri orantısız değerlidir.

### Kalite Seviyeleri

| Seviye | quality_score | Kullanım |
|--------|--------------|---------|
| Referans (S-tier) | 9-10 | The Creator'ın birincil şablon havuzu |
| Yüksek (A-tier) | 7-8 | The Creator'ın genişletilmiş havuzu |
| Orta (B-tier) | 4-6 | Negatif örnek olarak The Mirror'a gider |
| Düşük (C-tier) | 1-3 | Sadece "kaçınılacaklar" listesi için |

---

## Pattern Raporu

The Lab, tüm batch işlemi tamamlandıktan sonra bir özet rapor üretir. Bu rapor The Creator'a gönderilir ve şu bölümleri içerir.

### 1. Etiket Frekans Dağılımı

Her boyut için hangi etiketin kaç kez seçildiği ve yüzde dağılımı.

```
Psikolojik Tetikleyici Dağılımı (N=497):
  Merak:  38% (189 tweet)
  FOMO:   22% (109 tweet)
  Şok:    17% ( 85 tweet)
  Mizah:  11% ( 55 tweet)
  Empati:  7% ( 35 tweet)
  Öfke:    4% ( 20 tweet)
  Gurur:   1% (  4 tweet)
```

### 2. Yüksek Kalite Kombinasyonları

Quality score >= 8 olan tweetlerde en sık görülen etiket kombinasyonları.

```
Top 5 Yüksek Performanslı Kombinasyon:
  1. Merak + Thread + Şok_İddiası + Eğitici → ortalama score: 8.7 (n=23)
  2. FOMO + Veri_Paylaşımı + Rakam + Profesyonel → ortalama score: 8.4 (n=18)
  3. Şok + Karşıt_Görüş + Şok_İddiası + Alaycı → ortalama score: 8.1 (n=14)
  ...
```

### 3. Algoritma Sinyal Korelasyonları

Hangi içerik formu hangi sinyal türüyle en çok örtüşüyor?

```
Thread → dwell_odaklı (%91 korelasyon)
Veri_Paylaşımı → bookmark_odaklı (%78 korelasyon)
Soru → reply_odaklı (%84 korelasyon)
Karşıt_Görüş → retweet_odaklı (%61 korelasyon)
```

### 4. Görsel Format Etkisi

Görsel içeren vs sadece metin tweetlerin karşılaştırması.

```
Medya türü → medyan engagement rate:
  Video:   %4.8
  Görsel:  %3.9
  GIF:     %2.7
  Yok:     %2.1
```

### 5. Kanca Tipi Performansı

Her kanca tipinin ortalama quality score'u.

```
Kança Tipi → ortalama quality_score:
  Kişisel_Hata:    8.3
  Şok_İddiası:     8.0
  Rakam:           7.6
  Karşılaştırma:   7.4
  Soru:            7.1
  Trend_Bağlantısı: 6.8
```

### 6. Niş Boşluk Analizi

Yüksek kaliteli tweetlerde eksik olan etiket kombinasyonları — bu kombinasyonlar @ciftcibahadir için fırsat alanı temsil eder.

```
Az kullanılan ama yüksek potansiyelli yapılar:
  - Empati + Deneyim + Kişisel_Hata + Samimi (bu niş için neredeyse yok)
  - Veri_Paylaşımı + Mizah + Alaycı (ciddi data + mizah kombinasyonu az)
```

---

## Sistem Promptu

Aşağıdaki prompt, The Lab'ı bir downstream tüketici (The Mirror, The Creator) olarak çağıran sistemler için kullanılabilir. Doğrudan Claude Code üzerinden çalıştırılabilir.

```
Sen TwitterYoldas pipeline'ının ikinci aşaması olan The Lab'sın.

Rolün: The Miner'dan gelen ham tweet verisini analiz etmek, her tweeti 6 boyutlu sınıflandırma şemasıyla etiketlemek ve pattern raporu üretmek.

Sahip olduğun bilgi:
- X algoritmasının 19 engagement sinyali ve ağırlık formülü (x_algorithm_signals.md)
- Psikolojik tetikleyici → engagement türü korelasyonları
- @ciftcibahadir'in hedef niş bağlamı: Agentic AI, multi-skill pipeline, vibe coding, MCP
- Kullanıcı profili: 137 takipçi, %35 verified, %2.3 engagement rate

Çalışma kuralların:
1. Her tweet için batch prompt şablonunu doldur ve LLM'e gönder.
2. Gelen JSON çıktıyı orijinal tweet verisine `lab_analysis` nesnesi olarak ekle.
3. Tüm tweetler işlenince pattern raporu üret.
4. quality_score >= 7 olan tweetleri `high_quality: true` ile işaretle.
5. Çıktıyı hem The Mirror hem The Creator'ın tüketebileceği formatta hazırla.

Bağlam koru:
- "Yüksek kalite" bu niş için görecelidir. 50+ like, bu niş için anlamlıdır.
- DM share ve bookmark sinyalleri bu niş için like'tan daha değerli olabilir; bunu sınıflandırmana yansıt.
- Sadece etiket yapıştırma; `reasoning` alanını gerçekten düşünerek doldur.

Sınıflandırma tamamlandığında şunu söyle:
"The Lab tamamlandı. {N} tweet işlendi, {M} yüksek kalite örnek belirlendi. Pattern raporu ektedir."
```

---

## Örnek

### Girdi (The Miner'dan gelen ham tweet)

```json
{
  "tweet_id": "1891234567890",
  "source_account": "@levelsio",
  "text": "I made $3M last year working alone, no employees, no VC.\n\nHere's exactly how I structured my week (it's not what you think):",
  "published_at": "2025-10-15T09:00:00Z",
  "metrics": {
    "like_count": 18420,
    "retweet_count": 2105,
    "reply_count": 891,
    "bookmark_count": 6340,
    "impression_count": 524000,
    "engagement_rate": 0.0416
  },
  "media_type": "yok",
  "tweet_type": "thread_head"
}
```

### Batch API'ye Gönderilen Kullanıcı Promptu

```
Aşağıdaki tweet metnini ve engagement metriklerini analiz et.

--- TWEET ---
Metin: I made $3M last year working alone, no employees, no VC.

Here's exactly how I structured my week (it's not what you think):
Like: 18420
Retweet: 2105
Reply: 891
Bookmark: 6340
İmpresyon: 524000
Medya: yok
Tweet türü: thread_head
Yazar niş: Agentic AI, vibe coding, MCP
Yayın tarihi: 2025-10-15T09:00:00Z
--- /TWEET ---

Aşağıdaki JSON formatında çıktı ver. Başka hiçbir şey yazma.
{ ... }
```

### The Lab Çıktısı

```json
{
  "tweet_id": "1891234567890",
  "source_account": "@levelsio",
  "text": "I made $3M last year working alone, no employees, no VC.\n\nHere's exactly how I structured my week (it's not what you think):",
  "published_at": "2025-10-15T09:00:00Z",
  "metrics": {
    "like_count": 18420,
    "retweet_count": 2105,
    "reply_count": 891,
    "bookmark_count": 6340,
    "impression_count": 524000,
    "engagement_rate": 0.0416
  },
  "media_type": "yok",
  "tweet_type": "thread_head",
  "high_quality": true,
  "lab_analysis": {
    "labels": {
      "psikolojik_tetikleyici": ["FOMO", "Merak"],
      "primary_trigger": "FOMO",
      "icerik_formu": "Thread",
      "ton": "Samimi",
      "kanca_tipi": "Rakam",
      "gorsel_format": "Yok",
      "algoritma_sinyal_tahmini": ["bookmark_odaklı", "dwell_odaklı", "retweet_odaklı"]
    },
    "quality_score": 10,
    "hook_text": "I made $3M last year working alone, no employees, no VC.",
    "reasoning": "Somut rakam kancası ($3M) anında FOMO ve merak tetikliyor; 'it's not what you think' ifadesi beklentiyi kırarak dwell süresini artırıyor. Bookmark/impression oranı %1.2 ile çok güçlü — referans değeri yüksek içerik.",
    "processed_at": "2026-03-17T10:45:00Z",
    "model_used": "gpt-4o-mini-batch"
  }
}
```

### Örnek Pattern Raporu Özeti

```
The Lab tamamlandı. 500 tweet işlendi, 87 yüksek kalite örnek belirlendi.

En güçlü kombinasyon: FOMO + Thread + Rakam + Samimi (ort. score: 9.1)
En değerli sinyal: bookmark_odaklı (87 tweet, %17)
Niş boşluğu: Empati + Deneyim kombinasyonu bu nişte neredeyse yok — fırsat alanı.
Kaçınılacak: Trend_Bağlantısı tek başına zayıf (ort. score: 6.2); başka bir tetikleyiciyle desteklenmeli.
```
