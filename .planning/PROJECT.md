# Multi-Skill Agent Ekosistemi — TwitterYoldas

## What This Is

Twitter/X'te organik büyümeyi hedefleyen, 4 skill'den oluşan hibrit bir AI ajan ekosistemi. Kapalı devre veri fabrikası (Miner + Lab) global trend verisi üretir; açık kaynak kullanıcı katmanı (Mirror + Creator) bu veriyi kullanıcının kişisel sesiyle harmanlayarak içerik önerileri sunar. V1 hedefi: 4 skill'i tamamlamak ve Mirror'ı kullanıcının kendi tweetlerini otomatik okuyacak şekilde çalıştırmak.

## Core Value

Kullanıcının kendi ses tonunu koruyarak X algoritmasının öne çıkardığı formatları birleştiren, "yapay durmayan" içerik önerileri üretmek.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] The Mirror SKILL.md tamamlanmış ve `last_synced_at` tabanlı incremental sync destekliyor
- [ ] `mirror_sync.py` ücretsiz API (twikit / twitter-api-client) ile çalışıyor, kendi tweetlerini çekiyor
- [ ] `style_memory.json` şeması dolu: hook patterns, tone profile, engagement snapshot
- [ ] The Creator SKILL.md, Mirror'dan gelen DNA raporunu alıp içerik taslağı üretiyor
- [ ] The Miner SKILL.md, hedef hesapları ve niş tweetleri tanımlıyor (kod yok, prompt tabanlı)
- [ ] The Lab SKILL.md, batch etiketleme prompt şemasını içeriyor (kod yok, prompt tabanlı)
- [ ] `references/x_algorithm_signals.md` güncel X algoritma sinyal ağırlıklarını içeriyor
- [ ] `references/tweet_datasets.md` kullanılabilir dataset kaynaklarını listeler
- [ ] `decision.md` ve `strateji.md` güncel ve tüm kararları yansıtıyor

### Out of Scope

- Miner API backend geliştirme — v1'de kapsam dışı, sonraki milestone
- SaaS abonelik sistemi — v1 önce kendi kullanımı için doğrulama gerekiyor
- Lab için gerçek kod (scraper, etiketleyici) — v1 prompt-only
- Miner için gerçek scraper kodu — v1 prompt-only
- Web arayüzü / dashboard — CLI ve JSON yeterli v1 için
- Çoklu kullanıcı desteği — v1 yalnızca @ciftcibahadir ile test edilir

## Context

- Mevcut skill dosyaları: `skills/the-miner/SKILL.md`, `skills/the-lab/SKILL.md`, `skills/the-mirror/SKILL.md`, `skills/the-creator/SKILL.md`
- Mirror sync taslağı: `skills/the-mirror/mirror_sync.py` (Tweepy tabanlı, ücretsiz API'ye geçiş gerekiyor)
- Referanslar: `references/x_algorithm_signals.md` (19 sinyal, Phoenix mimarisi), `references/tweet_datasets.md`
- Hedef kullanıcı: @ciftcibahadir — Agentic AI nişi, 137 takipçi, %35 verified, 254.8K impressions
- Grok ile yapılan analiz: engagement %2.3, bookmark/like 0.57, RT/like 0.012 (zayıf)
- Ücretsiz tweet okuma için en umut verici kütüphane: `twitter-api-client` (tweet_stats() metodu)

## Constraints

- **Tech Stack**: Python — tweepy, twikit, twitter-api-client ekosistemi
- **Hosting**: Yerel / kendi sunucu — platform bağımlılığı yok
- **API Maliyeti**: Sıfır veya minimum — ücretsiz scraping API'ları öncelikli
- **Kapsam**: V1 kod üretimi mirror_sync.py ile sınırlı; skill'ler prompt belgesi olarak kalır
- **Veri Gizliliği**: Mirror verisi yerelde tutulur (`style_memory.json`), buluta yedekleme yok

## Key Decisions

| Karar | Gerekçe | Sonuç |
|-------|---------|-------|
| Hibrit mimari (Kapalı + Açık) | Miner/Lab "moat" oluşturur, Mirror/Creator topluluk değeri sağlar | — Pending |
| V1 kapsam: Skill'ler + Mirror Sync | Hızlı doğrulama, sıfır altyapı maliyeti | — Pending |
| Python backend | Tweepy/twikit ekosistemi, AI entegrasyon kolaylığı | — Pending |
| Yerel hosting | Kontrol, maliyet sıfır, gizlilik | — Pending |
| Ücretsiz API önceliği | X resmi API ücretli; twikit/twitter-api-client cookie tabanlı ücretsiz | — Pending |
| Mirror verisi yerelde | Open source topluluğu için gizlilik avantajı, v1 basitliği | — Pending |

---
*Last updated: 2026-03-17 after initialization*
