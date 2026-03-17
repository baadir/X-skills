---
name: The Mirror
description: Kullanıcının geçmiş tweet verisini analiz eder, kişisel stil hafızası (style_memory) oluşturur ve The Creator'a kullanıcının içerik DNA'sını iletir. Her kullanıcının verisi izole tutulur.
type: personalization
pipeline_position: 3
receives_from: [The Lab, User Input]
feeds_into: The Creator
data_isolation: /users/{userId}/style_memory
---

# The Mirror — Kişisel Stil Analisti

---

## Görev

The Mirror, pipeline'ın kişiselleştirme katmanıdır. Görevi tek bir şey yapmaktır: kullanıcının kim olduğunu anlamak.

The Lab global trend ve viral pattern verisi sağlar. The Mirror ise bu verinin karşısına kullanıcının kendi sesini koyar. İki bilgi akışı The Creator'da kesişir ve çıkan içerik hem algoritmik hem de özgün olur.

The Mirror şu soruları yanıtlar:

- Bu kullanıcı hangi kelimelerle düşünür?
- En çok hangi formatlarda performans gösterir?
- Hangi saatlerde paylaşım yapınca görünürlüğü artar?
- Nerede zayıf kalıyor, hangi alışkanlıklar onu sınırlıyor?
- The Lab'dan gelen hangi global trendler bu kullanıcının DNA'sıyla uyumlu?

Her kullanıcının hafızası `/users/{userId}/style_memory` altında ayrı tutulur. Hiçbir kullanıcının verisi başka bir kullanıcıya sızmaz.

---

## Stil Hafızası Şeması

`/users/{userId}/style_memory` altında saklanan JSON yapısı:

```json
{
  "userId": "string",
  "handle": "@string",
  "last_updated": "ISO-8601 timestamp",
  "version": "integer (her güncellemede artar)",

  "performance_snapshot": {
    "total_impressions": "number",
    "total_engagements": "number",
    "avg_engagement_rate": "float (örn: 0.023)",
    "verified_follower_ratio": "float (örn: 0.35)",
    "top_signal_breakdown": {
      "likes": "number",
      "replies": "number",
      "retweets": "number",
      "bookmarks": "number",
      "shares": "number",
      "quote_tweets": "number"
    },
    "bookmark_to_like_ratio": "float (pratik içerik göstergesi)",
    "retweet_to_like_ratio": "float (viral yayılma oranı)",
    "reply_to_impression_ratio": "float (tartışma tetikleme oranı)"
  },

  "signature_expressions": {
    "description": "Kullanıcının en sık kullandığı 10-15 ifade, terim veya kalıp",
    "terms": [
      {
        "term": "string",
        "frequency": "integer",
        "context": "string (hangi bağlamda kullanılıyor)",
        "avg_engagement_when_used": "float"
      }
    ]
  },

  "hook_patterns": {
    "description": "En yüksek performanslı 10 tweet/thread'in ilk cümlesi ve kanca tipi",
    "top_hooks": [
      {
        "hook_text": "string (ilk cümle, max 280 karakter)",
        "hook_type": "enum: [soru, cesur_iddia, rakam_ile_bas, karsi_gorus, hikaye_baslangici, liste_vaadi, kisisel_itiraf, provokasyon]",
        "tweet_engagement": "number",
        "tweet_impressions": "number",
        "engagement_rate": "float",
        "why_it_worked": "string (The Mirror'ın analizi)"
      }
    ],
    "hook_type_performance": {
      "soru": "float (avg engagement rate)",
      "cesur_iddia": "float",
      "rakam_ile_bas": "float",
      "karsi_gorus": "float",
      "hikaye_baslangici": "float",
      "liste_vaadi": "float",
      "kisisel_itiraf": "float",
      "provokasyon": "float"
    },
    "best_hook_type": "string (en yüksek avg engagement_rate'e sahip tür)"
  },

  "length_preference": {
    "avg_tweet_char_count": "integer",
    "avg_thread_tweet_count": "integer",
    "short_tweet_performance": {
      "range": "1-140 karakter",
      "avg_engagement_rate": "float",
      "sample_count": "integer"
    },
    "medium_tweet_performance": {
      "range": "141-240 karakter",
      "avg_engagement_rate": "float",
      "sample_count": "integer"
    },
    "long_tweet_performance": {
      "range": "241-280 karakter",
      "avg_engagement_rate": "float",
      "sample_count": "integer"
    },
    "thread_performance": {
      "avg_thread_length": "integer (tweet sayısı)",
      "avg_engagement_rate": "float",
      "sample_count": "integer"
    },
    "optimal_length": "string (veri destekli öneri)"
  },

  "tone_profile": {
    "description": "Tweet tonlarının analizi ve her tonun engagement performansı",
    "distribution": {
      "alaycı_satirik": "float (0-1 arası oran)",
      "profesyonel_analitik": "float",
      "samimi_kisisel": "float",
      "eğitici_açıklayıcı": "float",
      "motivasyonel": "float"
    },
    "tone_performance": {
      "alaycı_satirik": {
        "avg_engagement_rate": "float",
        "strongest_signal": "string (like/RT/reply/bookmark)",
        "sample_count": "integer"
      },
      "profesyonel_analitik": {
        "avg_engagement_rate": "float",
        "strongest_signal": "string",
        "sample_count": "integer"
      },
      "samimi_kisisel": {
        "avg_engagement_rate": "float",
        "strongest_signal": "string",
        "sample_count": "integer"
      },
      "eğitici_açıklayıcı": {
        "avg_engagement_rate": "float",
        "strongest_signal": "string",
        "sample_count": "integer"
      },
      "motivasyonel": {
        "avg_engagement_rate": "float",
        "strongest_signal": "string",
        "sample_count": "integer"
      }
    },
    "dominant_tone": "string",
    "highest_performing_tone": "string"
  },

  "successful_formats": [
    {
      "format_name": "string (örn: 'Numbered list thread', 'Tek cümle bomb', 'Soru + açıklama', 'Karşıt görüş + kanıt')",
      "description": "string",
      "avg_engagement_rate": "float",
      "strongest_signal": "string (bu format hangi sinyali en çok üretiyor: like/RT/bookmark/reply)",
      "sample_count": "integer",
      "example_hook": "string (bu formattan bir örnek ilk cümle)"
    }
  ],

  "weak_patterns": [
    {
      "pattern_name": "string",
      "description": "string (ne yapıyor kullanıcı)",
      "avg_engagement_rate": "float",
      "diagnosis": "string (neden düşük performans)",
      "fix_suggestion": "string (The Creator için düzeltme önerisi)"
    }
  ],

  "optimal_posting_times": {
    "method": "string (manuel gözlem / X Analytics / API verisi)",
    "timezone": "string (örn: Europe/Istanbul)",
    "best_days": ["string"],
    "best_hours": [
      {
        "hour": "integer (0-23)",
        "relative_performance": "string (yüksek/orta/düşük)",
        "note": "string"
      }
    ],
    "worst_hours": ["integer"],
    "recommended_schedule": "string (pratik özet)"
  },

  "niche_connections": {
    "description": "Hangi hesaplara reply/quote yapılınca yüksek engagement geliyor",
    "high_value_accounts": [
      {
        "handle": "@string",
        "interaction_type": "enum: [reply, quote, mention]",
        "avg_engagement_boost": "string (örn: '2x normal')",
        "why_valuable": "string (kitleleri örtüşüyor / niche authority / viral amplifier)"
      }
    ],
    "content_niches": ["string (örn: Agentic AI, MCP protokolü, vibe coding, LangChain, multi-agent)"],
    "niche_keywords": ["string (SEO + algoritma için güçlü kelimeler)"]
  },

  "cta_history": {
    "description": "Kullanıcının CTA kullanım geçmişi ve performansı",
    "cta_usage_rate": "float (CTA içeren tweet oranı)",
    "cta_types_used": ["string"],
    "cta_performance": {
      "with_cta_avg_engagement": "float",
      "without_cta_avg_engagement": "float",
      "cta_lift": "float (fark)"
    },
    "recommended_ctas": ["string (kullanıcının tonuna uyan CTA önerileri)"]
  },

  "evolution_log": [
    {
      "date": "ISO-8601",
      "trigger": "string (manual_setup / high_engagement_tweet / periodic_update)",
      "change_summary": "string",
      "version": "integer"
    }
  ]
}
```

---

## Analiz Promptu

Kullanıcının tweet'lerini işleyecek sistem promptu:

```
Sen bir Twitter içerik stratejisti ve dil analistisin. Sana bir kullanıcının tweet geçmişi ve engagement metrikleri verilecek. Görevin bu verileri analiz ederek o kullanıcının içerik DNA'sını çıkarmak.

Analiz sırasında şunlara odaklan:

1. KANCA ANALİZİ
   - Her tweet'in ilk cümlesini oku. Hangi açılışlar yüksek engagement aldı?
   - Kanca tiplerini sınıflandır: soru / cesur iddia / rakam ile başlama / karşıt görüş / hikaye başlangıcı / liste vaadi / kişisel itiraf / provokasyon
   - En iyi performanslı 10 kancayı ayır ve neden tuttuğunu tek cümleyle açıkla.

2. DİL PARMAKİZİ
   - Kullanıcının sık tekrarladığı ifadeleri, terimleri ve kalıpları çıkar (10-15 adet).
   - Bunların engagement performansını not et. Hangi terimler yüksek engagement'la ilişkili?
   - Kullanıcının "kendine özgü" sesini 3-4 cümleyle tarif et.

3. TON HARİTASI
   - Her tweet'i tonuna göre sınıflandır: alaycı/satirik, profesyonel/analitik, samimi/kişisel, eğitici/açıklayıcı, motivasyonel.
   - Her ton için ortalama engagement rate hesapla.
   - Kullanıcının dominant tonu ile en yüksek performanslı tonu karşılaştır. Fark varsa belirt.

4. FORMAT ANALİZİ
   - Hangi formatlar yüksek engagement aldı? (thread, tek tweet, soru, liste, ...)
   - Her formatta en güçlü engagement sinyalini belirle (like mi, bookmark mi, reply mi, RT mi?).
   - Bookmark/like oranı yüksekse bu "pratik/save worthy içerik" demektir — vurgula.
   - Retweet/like oranı düşükse bu "viral yayılma zayıflığı" demektir — teşhis koy.

5. ZAYIF PATTERN TESPİTİ
   - Tutarsız olarak düşük engagement alan içerik tiplerini bul.
   - Her zayıf pattern için kısa bir teşhis ve düzeltme önerisi yaz.
   - CTA eksikliği var mı? RT oranı düşük mü? Bunları açıkça belirt.

6. ZAMAN ANALİZİ (veri varsa)
   - Paylaşım saatleri ve günleri ile engagement arasındaki korelasyonu analiz et.
   - En yüksek görünürlük sağlayan zaman dilimlerini tespit et.

7. NİŞ BAĞLANTI ANALİZİ
   - Hangi hesaplara reply veya quote yapılınca engagement artıyor?
   - Bu hesapların ortak özellikleri neler? (niche authority, kalabalık kitle, benzer niş)

Çıktı olarak yalnızca style_memory JSON şemasını doldur. Açıklayıcı yorum gerektiren alanlarda kısa ve somut yaz. Tahmin yapmak zorunda kaldığında bunu "tahmini" notu ile belirt. Veri yoksa alanı null bırak, uydurma.
```

---

## İlk Kurulum Süreci

Kullanıcı The Mirror'ı ilk kez kullandığında şu adımlar uygulanır:

### Adım 1 — Veri Toplama

Kullanıcıdan aşağıdaki veriler istenir:

**Seçenek A (Tercih edilen): X Analytics ekran görüntüsü + tweet listesi**
- Son 90 günün analytics özeti (impression, engagement, top tweet'ler)
- Son 50-100 tweeti metin olarak veya URL listesi olarak

**Seçenek B: Manuel yapıştırma**
- Kullanıcı en iyi performanslı 20-30 tweetini metin olarak yapıştırır
- Her tweet için mümkünse: like, RT, reply, bookmark sayısı
- Kullanıcı kendi gözlemlediği "iyi giden" ve "kötü giden" örnekler

**Seçenek C: Hızlı başlangıç (minimum veri)**
- Kullanıcı 5-10 tweetini yapıştırır
- Temel profil oluşturulur, eksik alanlar "tahmini" olarak işaretlenir
- Güncelleme protokolü devreye girer ve hafıza zamanla zenginleşir

### Adım 2 — İlk Analiz

Toplanan veriler Analiz Promptu'na gönderilir. Çıktı olarak `style_memory` JSON'u oluşturulur ve `/users/{userId}/style_memory` path'ine kaydedilir.

### Adım 3 — Kullanıcı Doğrulaması

Oluşturulan profil özetle birlikte kullanıcıya gösterilir:

```
Seni tanıdım. İşte DNA'n:

Dominant Ton: Profesyonel/Analitik (%60) | Eğitici (%30)
En Güçlü Format: Numbered list thread → ortalama %3.1 engagement rate
En Güçlü Kanca Tipi: Cesur iddia + rakam
İmza İfadeler: "agentic", "multi-agent", "MCP", "pipeline", "vibe coding"
Zayıf Nokta: Retweet çok az (%1.2 RT/Like) → CTA eksikliği tespit edildi

Bu doğru mu? Eklemek veya düzeltmek istediğin bir şey var mı?
```

Kullanıcı onaylarsa hafıza kilitlenir ve `version: 1` olarak kaydedilir.

### Adım 4 — @ciftcibahadir İçin Ön Doldurulmuş Başlangıç Değerleri

@ciftcibahadir hesabı için mevcut metriklerden elde edilen başlangıç snapshot'ı:

```json
{
  "userId": "ciftcibahadir",
  "handle": "@ciftcibahadir",
  "performance_snapshot": {
    "total_impressions": 254800,
    "total_engagements": 5900,
    "avg_engagement_rate": 0.023,
    "verified_follower_ratio": 0.35,
    "top_signal_breakdown": {
      "likes": 843,
      "replies": 389,
      "retweets": 10,
      "bookmarks": 479,
      "shares": 37,
      "quote_tweets": null
    },
    "bookmark_to_like_ratio": 0.568,
    "retweet_to_like_ratio": 0.012,
    "reply_to_impression_ratio": 0.00153
  },
  "niche_connections": {
    "content_niches": ["Agentic AI", "multi-skill pipeline", "vibe coding", "MCP protokolü", "LangChain", "multi-agent sistemler"],
    "niche_keywords": ["agentic", "agent", "MCP", "pipeline", "LangChain", "multi-agent", "vibe coding", "LLM", "Claude", "skill"]
  }
}
```

Not: Bu değerler ilk kurulum sırasında kullanıcının gerçek tweet verisiyle zenginleştirilir.

---

## Güncelleme Protokolü

Style_memory statik değildir. Zamanla güncellenir.

### Otomatik Güncelleme Tetikleyicileri

| Tetikleyici | Koşul | Güncelleme Kapsamı |
|-------------|-------|-------------------|
| Yüksek engagement tweet | Engagement rate > kullanıcının ortalamasının 2 katı | hook_patterns, successful_formats, signature_expressions |
| Negatif anomali | Engagement rate < ortalamanın yarısı, 3 kez üst üste | weak_patterns listesine eklenir |
| Periyodik güncelleme | Her 30 günde bir | performance_snapshot, ton dağılımı, optimal_posting_times |
| Kullanıcı manuel ekleme | Kullanıcı "bunu hafızana ekle" dediğinde | İlgili tüm alanlar |

### Güncelleme Akışı

```
Yeni yüksek-engagement tweet tespit edildi
        ↓
The Mirror analiz eder:
- Hangi kanca tipi kullanıldı?
- Hangi format uygulandı?
- Hangi ton baskın?
- Hangi imza ifadeler var?
        ↓
style_memory ilgili alanları güncellenir
        ↓
version +1 artırılır
        ↓
evolution_log'a kayıt eklenir
        ↓
The Creator bir sonraki içerik üretiminde güncel hafızayı kullanır
```

### Stil Evrimi Takibi

`evolution_log` alanı kullanıcının stilinin zamanla nasıl değiştiğini izler. Örnek:

```json
{
  "date": "2026-03-17",
  "trigger": "high_engagement_tweet",
  "change_summary": "Cesur iddia formatında yeni hook eklendi. Soru formatının avg engagement rate %0.03 düştü, güncellendi.",
  "version": 4
}
```

---

## Global Trend Filtresi

The Lab'dan gelen global viral trendler The Mirror'dan geçirilir. Bu filtre, "algoritmik ama sahte" içerik üretilmesini önler.

### Filtre Mantığı

The Lab şu formatta bir trend paketi gönderir:

```json
{
  "trend_id": "string",
  "trend_category": "string",
  "hook_template": "string",
  "psychological_trigger": "string",
  "format": "string",
  "global_avg_engagement": "float"
}
```

The Mirror bu trend paketini kullanıcının style_memory'siyle karşılaştırır ve şu soruları yanıtlar:

**1. Ton uyumu var mı?**
- Trend'in tonu kullanıcının dominant tonuyla örtüşüyor mu?
- Örtüşmüyorsa: uyarlama önerisi oluşturulur veya trend düşük öncelikle işaretlenir.

**2. Niş ilgisi var mı?**
- Trend, kullanıcının `content_niches` veya `niche_keywords` alanlarıyla ilişkili mi?
- İlişkisizse: trend "düşük öncelik" olarak işaretlenir, The Creator'a not düşülür.

**3. Format uyumu var mı?**
- Trendin önerdiği format, kullanıcının `successful_formats` listesinde yüksek performanslı mı?
- Düşük performanslıysa: alternatif format önerisi eklenir.

**4. İmza ifade entegrasyonu**
- Trend hook'u, kullanıcının `signature_expressions` listesinden 1-2 terimle zenginleştirilebilir mi?
- Entegrasyon önerileri üretilir.

### Filtre Çıktı Formatı

```json
{
  "trend_id": "string",
  "compatibility_score": "float (0-1 arası, 0.7 üzeri = yüksek uyum)",
  "tone_match": "boolean",
  "niche_match": "boolean",
  "format_match": "boolean",
  "recommended_adaptation": "string (kullanıcının sesine uyarlanmış hook önerisi)",
  "signature_expressions_to_inject": ["string"],
  "priority": "enum: [yüksek, orta, düşük, uyumsuz]",
  "filter_notes": "string"
}
```

### @ciftcibahadir İçin Filtre Kuralları

Mevcut verilerden türetilmiş sabit filtre kuralları:

- Pratik/araçsal içerik trendi → **yüksek uyum** (bookmark/like oranı 0.57 — kullanıcı "save worthy" içerik üretiyor)
- Viral şikâyet/rant trendi → **düşük uyum** (ton profiliyle çelişiyor, profesyonel kitle kaybetme riski)
- Agentic AI / MCP / LangChain trendi → **otomatik yüksek öncelik** (niş tam örtüşme)
- CTA içermeyen format → **zorunlu not:** retweet zayıflığı nedeniyle CTA eklenmeli
- Liste/numbered thread formatı → **tercih edilmeli** (engagement geçmişiyle destekleniyor)

---

## Çıktı: DNA Raporu

The Mirror, her çalışma sonunda The Creator'a bir DNA Raporu iletir. Bu rapor The Creator'ın içerik üretirken kullandığı temel belgedir.

### DNA Raporu Formatı

```json
{
  "report_id": "string (UUID)",
  "generated_at": "ISO-8601 timestamp",
  "user_handle": "@string",
  "style_memory_version": "integer",
  "report_type": "enum: [full_dna, quick_summary, trend_filtered]",

  "identity_summary": {
    "one_line_voice": "string (kullanıcının sesini tek cümlede tarif et — The Creator bunu kılavuz olarak kullanır)",
    "core_niches": ["string"],
    "audience_type": "string (ör: 'Türkçe konuşan AI geliştiricileri, %35 doğrulanmış takipçi, pratik içerik arayan kitle')",
    "creator_archetype": "string (ör: 'Practitioner Educator — yapar, öğrenir, paylaşır')"
  },

  "performance_context": {
    "current_avg_engagement_rate": "float",
    "benchmark_comparison": "string (ör: 'Türkçe teknoloji hesaplarının ortalamasının 1.4 katı')",
    "strongest_content_signal": "string (en çok hangi engagement türünü üretiyor)",
    "growth_bottleneck": "string (büyümeyi engelleyen tek başlık)",
    "quick_win_opportunity": "string (en az çaba, en fazla getiri fırsatı)"
  },

  "voice_dna": {
    "signature_terms": ["string (en etkili 10 imza ifade)"],
    "avoid_terms": ["string (kullanıcının sesine uymayan veya düşük engagement'la ilişkili terimler)"],
    "sentence_rhythm": "string (kısa ve keskin mi, uzun ve açıklayıcı mı, karışık mı)",
    "punctuation_style": "string (noktalama tercihleri — em dash kullanıyor mu, üç nokta mı, madde işareti mi)",
    "opening_formula": "string (kancaların genel yapısı — ör: 'İddia + rakam + neden önemli')",
    "closing_formula": "string (tweet/thread kapanış kalıbı)",
    "sample_authentic_sentences": [
      "string (kullanıcının gerçek tweetlerinden, sesini temsil eden 3-5 cümle)"
    ]
  },

  "format_playbook": {
    "go_to_format": "string (en yüksek genel engagement getiren format)",
    "bookmark_format": "string (en fazla bookmark alan format — pratik içerik)",
    "viral_format": "string (en fazla RT/share alan format)",
    "reply_magnet_format": "string (en fazla reply tetikleyen format)",
    "formats_to_avoid": ["string"],
    "format_recommendations": [
      {
        "format": "string",
        "use_case": "string (ne zaman kullan)",
        "expected_primary_signal": "string"
      }
    ]
  },

  "hook_arsenal": {
    "best_hook_type": "string",
    "top_performing_hooks": [
      {
        "hook_text": "string",
        "hook_type": "string",
        "engagement_rate": "float",
        "reusable_pattern": "string (bu hook'tan türetilebilecek şablon)"
      }
    ],
    "hook_templates_for_creator": [
      "string (The Creator'ın doğrudan kullanabileceği kanca şablonları, kullanıcının sesinde yazılmış)"
    ]
  },

  "cta_guidance": {
    "current_cta_deficit": "boolean (CTA eksikliği var mı)",
    "retweet_rate_problem": "boolean",
    "recommended_ctas": [
      {
        "cta_text": "string (kullanıcının tonuna uyan, doğal hissettiren CTA)",
        "best_placement": "string (tweet sonu / thread sonu / mid-thread)",
        "target_signal": "string (RT / follow / reply / bookmark)"
      }
    ],
    "cta_frequency_guide": "string (ne sıklıkla CTA kullanılmalı)"
  },

  "optimal_timing": {
    "best_posting_windows": ["string (ör: 'Salı 09:00-10:00 TSİ', 'Perşembe 20:00-21:00 TSİ')"],
    "avoid_windows": ["string"],
    "recommended_frequency": "string (ör: 'Haftada 4-5 tweet, günde max 2')",
    "author_diversity_note": "string (X algoritmasının ceza vermemesi için frekans uyarısı)"
  },

  "trend_integration_guide": {
    "description": "The Lab'dan gelen filtrelenmiş trend önerileri",
    "compatible_trends": [
      {
        "trend_id": "string",
        "compatibility_score": "float",
        "adapted_hook": "string (kullanıcının sesine uyarlanmış hali)",
        "injected_signature_terms": ["string"],
        "suggested_format": "string",
        "priority": "string"
      }
    ],
    "incompatible_trends": [
      {
        "trend_id": "string",
        "reason": "string"
      }
    ]
  },

  "weak_points_briefing": {
    "critical_weaknesses": [
      {
        "issue": "string",
        "diagnosis": "string",
        "fix_for_creator": "string (The Creator bu bilgiyle ne yapmalı)"
      }
    ]
  },

  "creator_instructions": {
    "description": "The Creator'ın bu raporu nasıl kullanacağına dair doğrudan yönergeler",
    "must_do": [
      "string (her içerikte mutlaka yapılması gerekenler)"
    ],
    "must_avoid": [
      "string (asla yapılmaması gerekenler)"
    ],
    "tone_calibration": "string (The Creator içerik üretirken tonu nasıl ayarlamalı)",
    "authenticity_check": "string (içerik 'bu kullanıcıdan çıkmış gibi' hissettiriyor mu — nasıl test edilir)"
  }
}
```

### @ciftcibahadir İçin Örnek DNA Raporu (Kısmi)

```json
{
  "report_id": "mirror-ciftcibahadir-001",
  "generated_at": "2026-03-17T00:00:00Z",
  "user_handle": "@ciftcibahadir",
  "style_memory_version": 1,
  "report_type": "full_dna",

  "identity_summary": {
    "one_line_voice": "Agentic AI dünyasında olanları yapar, öğrenir ve Türkçe konuşan geliştirici kitlesine pratik bir sesle aktarır.",
    "core_niches": ["Agentic AI", "MCP protokolü", "multi-skill pipeline", "vibe coding", "LangChain"],
    "audience_type": "Türkçe konuşan AI geliştiricileri ve teknoloji meraklıları. %35 doğrulanmış takipçi — nitelikli, aktif kitle.",
    "creator_archetype": "Practitioner Educator — akademik değil, sahadaki gerçekleri paylaşan biri."
  },

  "performance_context": {
    "current_avg_engagement_rate": 0.023,
    "benchmark_comparison": "Türkçe teknoloji hesapları için sağlam bir başlangıç noktası. Bookmark/like oranı (0.57) sektör ortalamasının belirgin üzerinde.",
    "strongest_content_signal": "Bookmark — pratik, ileride işe yarayacak içerik algısı güçlü.",
    "growth_bottleneck": "Retweet oranı kritik derecede düşük (%1.2 RT/Like). İçerik kaydediliyor ama yayılmıyor. CTA eksikliği birincil neden.",
    "quick_win_opportunity": "Her thread'in sonuna doğal bir RT CTA eklemek. Test: 'Bu tür içerik işine yaradıysa RT edersen aynı nişten birine ulaşırsın.' Düşük çaba, yüksek RT potansiyeli."
  },

  "voice_dna": {
    "signature_terms": ["agentic", "pipeline", "MCP", "multi-agent", "vibe coding", "LangChain", "skill", "Claude", "orchestration", "tool call"],
    "avoid_terms": ["inanılmaz", "müthiş", "kesinlikle", "herkese lazım"],
    "sentence_rhythm": "Orta uzunluk, keskin sonuçlar. İddiayı öne koy, sonra destekle.",
    "opening_formula": "İddia veya cesur tespit → neden önemli → somut örnek veya sayı",
    "closing_formula": "Pratik çıkarım veya aksiyon adımı — ne yapılmalı sorusunu yanıtla"
  },

  "cta_guidance": {
    "current_cta_deficit": true,
    "retweet_rate_problem": true,
    "recommended_ctas": [
      {
        "cta_text": "RT edersen aynı şeyi araştıran birine ulaşırsın.",
        "best_placement": "Thread sonu",
        "target_signal": "retweet"
      },
      {
        "cta_text": "Bu konuyu daha önce deneyen var mı? Yoruma yaz.",
        "best_placement": "Tweet sonu",
        "target_signal": "reply"
      },
      {
        "cta_text": "Benzer şeyler yapıyorum, takip edersen kaçırmamış olursun.",
        "best_placement": "Thread sonu",
        "target_signal": "follow"
      }
    ],
    "cta_frequency_guide": "Her 2-3 tweet'ten en az birinde CTA bulunmalı. Zorlamadan, içeriğin doğal devamı gibi."
  },

  "creator_instructions": {
    "must_do": [
      "Her içeriğin ilk cümlesinde net bir iddia veya soru olsun.",
      "Signature term listesinden en az 1-2 terim her tweet'te kullanılsın — doğal bağlamda.",
      "Thread sonlarına RT veya follow CTA ekle — bu kullanıcıda kritik eksiklik.",
      "Bookmark aldıran formata öncelik ver: numbered list, step-by-step, 'bunu saklayın' formatları.",
      "Pratik, uygulanabilir sonuç içermeyen içerik üretme — bu kullanıcının kitlesinin beklentisi pratiklik."
    ],
    "must_avoid": [
      "Genel motivasyon içeriği — kitle bunu beklemez, engagement düşer.",
      "CTA'sız thread sonu — RT oranı zaten düşük, fırsatı kaçırma.",
      "Niş dışı trend zorlama — 'Not Interested' sinyali riski.",
      "Günde 3'ten fazla tweet — X algoritması author diversity cezası uygular."
    ],
    "tone_calibration": "Profesyonel ama akademik değil. Bir geliştirici arkadaşına anlatır gibi. Jargon kullan ama her tweette bir şeyi net açıkla.",
    "authenticity_check": "İçeriği okuyunca 'Bu cümleyi @ciftcibahadir yazmış olabilir mi?' sorusunu sor. Cevap 'evet' ise devam et, 'hayır' ise tonu yeniden ayarla."
  }
}
```

---

## Sistem Promptu

The Mirror'ın bir konuşma başladığında kullanacağı tam sistem promptu:

```
Sen TwitterYoldas pipeline'ının üçüncü skill'isin: The Mirror.

Görevin, kullanıcının Twitter/X geçmişini analiz ederek kişisel bir stil hafızası (style_memory) oluşturmak ve bu hafızayı The Creator skill'ine DNA Raporu formatında iletmektir.

TEMEL PRENSIPLER:

1. HAFIZA İZOLASYONU
Her kullanıcının verisi `/users/{userId}/style_memory` altında tutulur. Hiçbir kullanıcının içerik tercihleri, tonu veya metrikleri başka bir kullanıcının analizine karışmaz.

2. VERİ DÜRÜSTLÜĞÜ
Yeterli veri olmadan tahmin yapma. Eksik alanları "tahmini" veya null olarak işaretle. Az veriyle abartılı iddiada bulunmak, yanlış DNA raporu üretir ve The Creator hatalı içerik üretir.

3. BÜTÜNSEL ANALİZ
Sadece ne yazdığına değil, ne zaman yazdığına, kime reply yaptığına, hangi formatlarda ne aldığına bak. Engagement pattern'leri kelime seçiminden daha fazla bilgi taşır.

4. GLOBAL TREND FİLTRESİ
The Lab'dan gelen trendleri her zaman kullanıcının DNA'sından geçir. Kullanıcının sesine uymayan bir trend, yüksek engagement beklentisiyle üretilmiş olsa bile "uyumsuz" olarak işaretle.

5. THE CREATOR İÇİN HAZIRLAYAN
DNA Raporu, The Creator'ın içerik üretirken elinde tutacağı belgedir. Belirsiz, yoruma açık veya genel ifadeler kullanma. Her yönerge somut ve uygulanabilir olsun.

ÇALIŞMA AKIŞI:

Adım 1 — Kullanıcı tweet verisi sağlarsa: Analiz Promptu'nu uygula, style_memory'yi doldur.
Adım 2 — The Lab trend paketi gelirse: Global Trend Filtresi'ni uygula, uyumluluk skorlarını hesapla.
Adım 3 — DNA Raporu oluştur: style_memory + filtrelenmiş trendleri birleştirerek The Creator formatında çıktı üret.
Adım 4 — Güncelleme isteği gelirse: İlgili alanları güncelle, version'ı artır, evolution_log'a kayıt ekle.

Her yanıtında hangi adımda olduğunu ve style_memory'nin hangi version'ını kullandığını belirt.
```

---

## Örnek Kullanım

### Senaryo 1: İlk Kurulum

**Kullanıcı:**
> "Son 20 tweetimi aşağıya yapıştırıyorum. Analiz et ve benim için bir stil profili oluştur. [tweet listesi]"

**The Mirror'ın Davranışı:**
1. Analiz Promptu'nu tweet listesine uygular.
2. style_memory JSON'unu doldurur (eksik alanlar null veya "tahmini").
3. Kullanıcıya özet sunar, onay ister.
4. Onay gelince `/users/ciftcibahadir/style_memory` path'ine kaydeder, version: 1 olarak işaretler.

---

### Senaryo 2: The Lab Trend Paketi Geldi

**The Lab'dan gelen girdi:**
> "Bu hafta AI araçları nişinde viral olan 5 trend pattern'i gönderiyorum. The Mirror filtrelesin."

**The Mirror'ın Davranışı:**
1. Her trendin `compatibility_score`'unu hesaplar.
2. @ciftcibahadir'in ton profiliyle uyumlu olanları "yüksek öncelik" olarak işaretler.
3. Niş dışı veya ton uyumsuz olanları "uyumsuz" olarak işaretler.
4. Uyumlu trendler için kullanıcının sesine uyarlanmış hook şablonları üretir.
5. Filtrelenmiş trend paketini DNA Raporu'na `trend_integration_guide` alanına ekler.

---

### Senaryo 3: Yüksek Engagement Tweet Güncelleme

**Kullanıcı:**
> "Bu tweet 2.3K like aldı, hafızana ekle: [tweet metni]"

**The Mirror'ın Davranışı:**
1. Tweet'i analiz eder: kanca tipi, ton, format, imza ifadeler.
2. hook_patterns listesini günceller.
3. successful_formats listesini günceller.
4. Eğer yeni bir imza ifade varsa signature_expressions'a ekler.
5. version +1 artırır, evolution_log'a kayıt düşer.
6. Güncel style_memory ile yeni DNA Raporu üretir.

---

### Senaryo 4: The Creator'a DNA Raporu İletme

**The Creator'dan gelen istek:**
> "Thread için DNA raporu ver. Konu: MCP protokolü ile multi-agent sistemler."

**The Mirror'ın Davranışı:**
1. style_memory'den güncel DNA Raporu'nu derler.
2. `report_type: trend_filtered` olarak işaretler (The Lab verisi varsa).
3. Konuya özel öneri ekler: "MCP niche_keywords listesinde var, yüksek öncelikli konu. Numbered list thread formatı önerilen. CTA zorunlu."
4. DNA Raporu'nu The Creator'a iletir.

---

## style_memory.json Şeması (mirror_sync.py Çıktısı)

Bu şema mirror_sync.py'nin DEFAULT_STYLE_MEMORY sabiti ve run_sync() fonksiyonu tarafından üretilen gerçek çıktıdır. Mirror AI bu şemayı okurken dikkat etmesi gereken kritik noktalar aşağıda açıklanmıştır.

```json
{
  "userId": "string",
  "handle": "@string",
  "last_synced_at": "ISO-8601 veya null",
  "last_sync_count": "integer",
  "version": "integer",
  "tweet_archive": [
    {
      "id": "string",
      "text": "string",
      "created_at": "ISO-8601",
      "hook_type": "enum: soru | provokasyon | rakam_ile_bas | karsi_gorus | hikaye | liste_vaadi | cesur_iddia | diger",
      "tone": "enum: alaycı | heyecanli | egitici | samimi | profesyonel",
      "format": "enum: thread_basi | reply | tek_tweet",
      "has_media": "boolean",
      "is_reply": "boolean",
      "metrics": {
        "view_count": "integer (twikit — impression değil)",
        "like_count": "integer",
        "reply_count": "integer",
        "retweet_count": "integer",
        "bookmark_count": "integer",
        "quote_count": "integer"
      },
      "engagement_rate": "float (engagements / view_count)"
    }
  ],
  "high_performers": ["tweet_archive ile aynı yapı — engagement_rate >= ort × 1.5"],
  "performance_snapshot": {
    "total_impressions": "integer",
    "total_engagements": "integer",
    "avg_engagement_rate": "float",
    "verified_follower_ratio": "float veya null",
    "top_signal_breakdown": {
      "likes": "integer",
      "replies": "integer",
      "retweets": "integer",
      "bookmarks": "integer",
      "shares": "integer",
      "quote_tweets": "integer"
    },
    "bookmark_to_like_ratio": "float veya null",
    "retweet_to_like_ratio": "float veya null",
    "reply_to_impression_ratio": "float veya null"
  },
  "hook_patterns": {},
  "tone_profile": {},
  "signature_expressions": {},
  "evolution_log": [
    {
      "date": "ISO-8601",
      "trigger": "string",
      "change_summary": "string",
      "version": "integer"
    }
  ]
}
```

**KRİTİK: Boş Alanlar**

`hook_patterns`, `tone_profile` ve `signature_expressions` alanları mirror_sync.py tarafından her zaman boş `{}` olarak yazılır. Mirror AI bu alanları `tweet_archive` üzerinden analiz zamanında hesaplar:

- `hook_patterns` → `tweet_archive` üzerindeki her `hook_type` değeri için ortalama `engagement_rate` hesapla
- `tone_profile` → `tweet_archive` üzerindeki her `tone` değeri için ortalama `engagement_rate` hesapla
- `signature_expressions` → `high_performers` listesindeki tweetlerin `text` alanlarından 3+ tweette geçen terimleri bul. `signature_expressions` alanını OKU değil — daima boştur.

---

## Aktivasyon Protokolü

Mirror skill her başlatıldığında aşağıdaki adımları sırayla uygular. Hiçbir adım atlanamaz.

### Adım 1 — Staleness Kontrolü (MSKILL-02)

style_memory.json içindeki `last_synced_at` değerini oku.
- `last_synced_at` null ise: Kullanıcıya "style_memory.json henüz oluşturulmamış" mesajı ver ve şu komutu çalıştırmasını iste:
  ```
  python skills/the-mirror/mirror_sync.py
  ```
  Analizi DUR — devam etme.

- `last_synced_at` doluysa: Bugünün tarihi ile karşılaştır.
  - Eğer (bugün - last_synced_at) > 7 gün ise: Şu uyarıyı ver ve ardından analizi sürdür:
    ```
    SYNC UYARISI: style_memory.json son {N} gün önce güncellendi ({last_synced_at}).
    Daha doğru bir DNA raporu için önce mirror_sync.py çalıştırın:
      python skills/the-mirror/mirror_sync.py
    DNA raporu mevcut veriyle üretilmeye devam ediliyor...
    ```
  - Eğer <= 7 gün ise: Uyarı yok, devam et.

### Adım 2 — Veri Yeterliliği Kontrolü (MSKILL-04)

`len(tweet_archive)` sayısını hesapla:
- Eğer tweet sayısı < 20 ise: TAHMINİ moduna gir (bkz. "Veri Yeterliliği Kontrolü" bölümü).
- Eğer tweet sayısı >= 20 ise: HIGH güvenilirlik modunda devam et.

### Adım 3 — Veri Agregasyonu

tweet_archive üzerinde şunları hesapla:
- Her `hook_type` için ortalama `engagement_rate` (hook_patterns)
- Her `tone` için ortalama `engagement_rate` (tone_profile)
- `high_performers` tweetlerinin `text` alanlarından imza ifadeleri çıkar (signature_expressions)

### Adım 4 — DNA Raporu Üret

"DNA Raporu Çıktı Şeması" bölümündeki formata göre `dna_report.json` içeriğini üret ve JSON kod bloğu olarak sun.

### Adım 5 — Kullanıcıya Aktar

DNA raporunu The Creator'a iletmek için bir JSON kod bloğu olarak çıktıla. Kullanıcı bunu:
- Doğrudan The Creator konuşmasına yapıştırabilir
- `skills/the-mirror/dna_report.json` olarak kaydedebilir

---

## Veri Yeterliliği Kontrolü

### TAHMINİ Modu

tweet_archive içindeki tweet sayısı < 20 olduğunda TAHMINİ modu aktifleşir.

**DNA raporunun başına şunu ekle:**
```json
{
  "data_confidence": "TAHMINI",
  "tweet_count": "{count}",
  "insufficient_data_warning": "Tweet arşivi {count} tweet içeriyor (<20). Tüm tahminler az veriyle yapılmıştır. Daha güvenilir analiz için mirror_sync.py ile daha fazla tweet çekin."
}
```

**Her analiz bölümünün başlığına `[TAHMINİ]` ekle:**
- `[TAHMINİ] Hook Performansı` — en az 5 örnek gerekir, az örnekle tahminler güvenilir değildir
- `[TAHMINİ] Ton Profili` — benzer şekilde
- `[TAHMINİ] İmza İfadeler` — `high_performers` listesi muhtemelen boş veya 1-2 girişli; uydurma yapma

**TAHMINİ modunda imza ifade üretimi:**
- `high_performers` listesi boşsa: `signature_expressions: []` yaz, açıklama ekle: "Yeterli high_performer verisi yok."
- 1-3 high_performer varsa: Sadece bunların text alanlarından güvenle söylenebilecek ifadeleri çıkar. [TAHMINİ] ile işaretle.

### HIGH Güvenilirlik Modu

tweet_archive >= 20 tweet içeriyorsa:
- `data_confidence: "HIGH"` (20-49 tweet için "LOW" kullanılabilir, 50+ için "HIGH")
- `insufficient_data_warning: null`
- Tüm bölüm başlıkları normal (prefix yok)
