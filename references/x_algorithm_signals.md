# X Algoritması — Sinyal ve Ağırlık Referansı

> Kaynak: https://github.com/xai-org/x-algorithm
> Son güncelleme: 2026-03-17
> Analiz edilen dosyalar: README.md, phoenix/README.md, phoenix/recsys_model.py, home-mixer/scorers/weighted_scorer.rs, home-mixer/scorers/phoenix_scorer.rs, home-mixer/scorers/author_diversity_scorer.rs, home-mixer/candidate_pipeline/candidate_features.rs

---

## Sistem Mimarisi

X'in "For You" feed'i iki içerik kaynağını birleştirir:

| Bileşen | Görev |
|---------|-------|
| **Thunder** | In-network içerik — takip edilen hesapların son gönderileri, sub-millisecond bellekte tutulur |
| **Phoenix** | Out-of-network içerik — ML ile bulunan, takip edilmeyen hesapların gönderileri |
| **Home Mixer** | Orkestrasyon — kandidatları toplar, filtreler, skorlar, sıralar |

Pipeline akışı: `Query Hydration → Candidate Sourcing → Filtering → Scoring → Selection`

---

## Skor Hesaplama Formülü

```
Weighted Score = Σ (weight × P(action))
```

- Her engagement türü için model bir olasılık tahmin eder
- Bu olasılıklar önceden atanmış ağırlıklarla çarpılır
- Pozitif eylemler pozitif ağırlık, negatif eylemler negatif ağırlık alır
- Nihai skor normalize edilir: `NEGATIVE_SCORES_OFFSET` ve `WEIGHTS_SUM` parametreleri kullanılır

---

## 19 Engagement Türü ve Skill İçin Anlamı

### Pozitif Sinyaller (yüksek tutar → görünürlük artar)

| # | Sinyal | Skill Stratejisi |
|---|--------|-----------------|
| 1 | **Favorite / Like** | Her tweet'in en temel metriği. Güçlü kanca = daha fazla like |
| 2 | **Reply** | Soru ile biten tweet'ler reply üretir → algoritmaya güçlü sinyal |
| 3 | **Retweet** | En az alınan sinyal (%1.2 RT/Like oranın var). CTA ekle: "RT edersen daha çok kişiye ulaşır" |
| 4 | **Quote Tweet** | Karşıt görüş veya "eklemek istiyorum" diye alanda kaliteli hesaplar quote eder |
| 5 | **Photo Expand** | Görsel içeren tweet'ler ekstra tıklama = ekstra sinyal üretir |
| 6 | **Link Click** | Repoya, videoya, makalelere link = click sinyali |
| 7 | **Profile Click** | İnsanları profile götüren içerik → "sen kimsin?" dedirtmeli |
| 8 | **Video Quality View (VQV)** | ⚠️ Sadece MIN_VIDEO_DURATION_MS üzerindeki videolara uygulanır. Kısa clip değil, izlenebilir video şarт |
| 9 | **Share** | Genel paylaşım sinyali |
| 10 | **Send via DM** | İnsanlar "bunu şuna göndereyim" dediğinde = çok güçlü kalite sinyali |
| 11 | **Copy Link Share** | Link kopyalama da sinyal — "bunu saklayayım" |
| 12 | **Dwell Time** | Tweetinin üzerinde ne kadar süre durulduğu. Uzun thread'ler + görseller dwell artırır |
| 13 | **Quoted Tweet Click** | Quote tweetlerde orijinale tıklama |
| 14 | **Follow Author** | Tweet görüp takip etmek → en güçlü sinyal. "Beni takip et" CTA'sı değerli |
| 19 | **Bookmark** | "Sonra okuyayım" sinyali — algoritmada güçlü "kaydedilesi içerik" proxy'si. DM share ile birlikte en önemli kalite göstergesi. Her tweet'te bir "sakla" momenti yarat |

### Negatif Sinyaller (bunları tetiklemek skoru düşürür)

| # | Sinyal | Kaçınma Stratejisi |
|---|--------|-------------------|
| 15 | **Not Interested** | "İlgisiz" içerik atma. Nişin dışına çıkma |
| 16 | **Block Author** | Agresif, spam, provoke edici içerik |
| 17 | **Mute Author** | Çok sık post, gürültülü içerik |
| 18 | **Report** | Kurallara aykırı içerik |

---

## Author Diversity Cezası

Algoritma aynı yazarın feed'de çok görünmesini aktif olarak engeller:

```
multiplier = (1.0 - floor) × decay_factor^position + floor
```

- İlk tweet: multiplier = 1.0 (ceza yok)
- Sonraki tweetler: multiplier giderek düşer
- `floor` parametresi tamamen sıfıra düşmesini engeller

**Pratik anlamı:**
- Günde 1-3 tweet ideal. Çok sık atmak feed'deki görünürlüğü azaltır
- Aynı konuyu aynı gün thread + ayrı tweet olarak tekrarlama

---

## Phoenix Transformer Modeli (Out-of-Network)

- **Mimari:** Grok-1 tabanlı transformer (xai-org/grok-1)
- **Candidate isolation:** Adaylar birbirini göremez — sadece user context'e attend eder
- **Input:** User embedding [B,1] + History embeddings [B,128,D] + Candidate embeddings [B,32,D]
- **Output:** `[B, num_candidates, num_actions]` — her aday için 19 action olasılığı
- **Precision:** bfloat16

**Pratik anlamı:**
- Takip etmediğin hesaplar seni out-of-network ile keşfeder
- Phoenix seni seçmesi için geçmiş engagement pattern'lerin benzer kullanıcılarla örtüşmeli
- Nişinde kaliteli hesaplarla etkileşim = Phoenix'in seni doğru kitleye önermesi

---

## Filtreler (Feed'e girememe nedenleri)

| Filtre | Ne Yapar |
|--------|----------|
| `age_filter` | Çok eski tweetleri eliyor (süre dinamik, runtime parametresi) |
| `dedup_conversation_filter` | Aynı konuşmadan tekrar göstermiyor |
| `drop_duplicates_filter` | Aynı tweet'i tekrar göstermiyor |
| `muted_keyword_filter` | Kullanıcının muted keyword'leriyle eşleşen içerik eleniyor |
| `previously_seen_posts_filter` | Zaten görülmüş postlar gösterilmiyor |
| `self_tweet_filter` | Kendi tweet'lerini kendi feed'inde göstermiyor |
| `author_socialgraph_filter` | Block/mute ilişkilerine göre eleme |
| `vf_filter` | Visibility filtering — içerik politikası |

---

## Skill'e Yansıyan Temel Çıkarımlar

1. **Bookmark, DM share ve dwell time güçlü ama gözden kaçan sinyaller** — "kaydedilesi" içerik yaz; bookmark oranı kalite proxy'si olarak izle
2. **Retweet en zor elde edilen sinyal** — explicit CTA olmadan nadiren gelir
3. **Video VQV ağırlığı sadece belirli süreden uzun videolara** — kaliteli, izlenebilir video > kısa clip
4. **Çok sık tweet atmak diversity cezası yiyor** — az ama güçlü içerik > çok ama zayıf içerik
5. **Negatif sinyallerden kaçın** — 1 report, 10 like'ı götürebilir
6. **Profile click = potansiyel follow** — her tweet "beni tanıyın" fırsatı
7. **Out-of-network keşif için nişinde kal** — algoritma engagement pattern'lerine göre benzer kitleye yönlendiriyor
