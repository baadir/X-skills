# Requirements: TwitterYoldas — Multi-Skill Agent Ekosistemi

**Defined:** 2026-03-17
**Core Value:** Kullanıcının kendi ses tonunu koruyarak X algoritmasının öne çıkardığı formatları birleştiren, "yapay durmayan" içerik önerileri üretmek.

---

## v1 Requirements

### Mirror Sync (SYNC)

- [x] **SYNC-01**: `mirror_sync.py` tweepy'den twikit 2.3.3'e migrate edilmiş, cookie tabanlı auth ile çalışıyor
- [x] **SYNC-02**: Script kendi hesabının tweetlerini çekiyor: text, created_at, view_count, like_count, reply_count, retweet_count, bookmark_count
- [x] **SYNC-03**: `start_time = last_synced_at` kullanarak incremental sync yapıyor (sadece yeni tweetleri çekiyor)
- [x] **SYNC-04**: Her tweet için hook_type, tone, format, is_reply, has_media otomatik kategorize ediliyor
- [x] **SYNC-05**: `style_memory.json` atomic write ile kaydediliyor (crash'te veri kaybı yok)
- [x] **SYNC-06**: Tweet arşivi 1000 tweet ile sınırlı, rolling window ile eski kayıtlar temizleniyor
- [x] **SYNC-07**: Rate limit koruması: 429 hatası için exponential backoff, günlük max fetch limiti
- [x] **SYNC-08**: `--dry-run` modu çalışıyor, `--since YYYY-MM-DD` override destekleniyor
- [x] **SYNC-09**: Sync çalıştıktan sonra terminal'e özet rapor basıyor: kaç tweet çekildi, yeni high_performer var mı

### Style Memory (MEM)

- [x] **MEM-01**: `style_memory.json` şeması: performance_snapshot, hook_patterns, tone_profile, signature_expressions, high_performers, last_synced_at, version
- [x] **MEM-02**: `high_performers` listesi otomatik güncelleniyor: engagement rate > ortalamanın 1.5 katı olan tweetler
- [x] **MEM-03**: `performance_snapshot` her sync'te güncelleniyor: avg_engagement_rate, bookmark_to_like_ratio, retweet_to_like_ratio
- [x] **MEM-04**: `@ciftcibahadir` için başlangıç değerleri elle girilmiş (254.8K impressions, 5.9K eng, 48 verified vb.)
- [x] **MEM-05**: `evolution_log` her güncellemede kayıt tutuyor: tarih, trigger, değişiklik özeti, version

### Mirror SKILL (MSKILL)

- [x] **MSKILL-01**: `the-mirror/SKILL.md` `style_memory.json` şemasını tam tanımlıyor ve açıklıyor
- [x] **MSKILL-02**: Mirror SKILL aktivasyonunda önce `last_synced_at` kontrol edip yeni tweet var mı diye sync uyarısı veriyor
- [x] **MSKILL-03**: Mirror SKILL, `style_memory.json`'dan DNA Raporu üretiyor ve The Creator'a iletebiliyor
- [x] **MSKILL-04**: Mirror SKILL minimum veri uyarısı yapıyor: <20 tweet için "tahmini" flagleri zorunlu

### Creator SKILL (CRTR)

- [x] **CRTR-01**: `the-creator/SKILL.md` DNA Raporunu input olarak alıp Mod 1 (Brainstorm) çalıştırabiliyor
- [x] **CRTR-02**: `the-creator/SKILL.md` Mod 3 (Analiz) çalıştırabiliyor: verilen tweet veya metriği analiz et
- [x] **CRTR-03**: Creator çıktısı `signature_expressions` listesinden en az 1-2 terim kullanıyor
- [x] **CRTR-04**: Creator her öneride CTA rehberliği veriyor (RT zayıflığı nedeniyle zorunlu)
- [x] **CRTR-05**: Creator "authenticity check" uyguluyor: çıktı "bu kullanıcıdan çıkmış gibi" test ediliyor

### Miner & Lab SKILL (MLSKILL)

- [ ] **MLSKILL-01**: `the-miner/SKILL.md` niş hesap listesini, veri toplama formatını ve priority score formülünü içeriyor
- [x] **MLSKILL-02**: `the-lab/SKILL.md` batch etiketleme prompt şemasını (JSONL), 6 boyutlu sınıflandırmayı ve S/A/B/C tier sistemini içeriyor
- [x] **MLSKILL-03**: Miner ve Lab SKILL.md dosyaları prompt-only (kod yok), kapalı devre olarak işaretlenmiş

### References & Docs (REFS)

- [ ] **REFS-01**: `references/x_algorithm_signals.md` X algoritmasının sinyal ağırlıklarını, author diversity cezasını ve Phoenix mimarisini içeriyor
- [ ] **REFS-02**: `references/tweet_datasets.md` ücretsiz dataset kaynakları ve kullanılabilir kütüphaneleri listeler
- [ ] **REFS-03**: `decision.md` tüm mimari kararları tarihiyle birlikte kayıt altında tutuyor
- [ ] **REFS-04**: `strateji.md` hibrit mimariyi, iş modelini ve açık noktaları tanımlıyor
- [x] **REFS-05**: `.gitignore` Miner/Lab kodlarını (gelecekteki) ve cookies.json'u dışarıda tutuyor

---

## v2 Requirements

### Miner Canlı Scraper

- **MINER-01**: twikit ile hedef hesapların tweetlerini otomatik toplayan scraper
- **MINER-02**: arXiv / akademik kaynak entegrasyonu
- **MINER-03**: priority score otomatik hesaplama ve filtreleme

### Lab Otomatik Etiketleyici

- **LAB-01**: Batch API ile toplanan tweetleri otomatik etiketleyen pipeline
- **LAB-02**: S/A/B/C tier kalite filtresi uygulayan kod
- **LAB-03**: Niş boşluk analizi raporu üreten sistem

### Miner API (SaaS)

- **API-01**: Altın veri setine erişim için REST API
- **API-02**: API Key tabanlı yetkilendirme
- **API-03**: Rate limiting ve kullanım kotası yönetimi

### Çoklu Kullanıcı

- **MULTI-01**: `/users/{userId}/style_memory` izole path yapısı
- **MULTI-02**: Kullanıcı kayıt ve API key yönetimi

---

## Out of Scope (v1)

| Feature | Neden Kapsam Dışı |
|---------|-------------------|
| Miner/Lab backend kodu | v1 prompt-only; kod moat gelecek milestone |
| SaaS abonelik sistemi | Önce kendi kullanımı için doğrulama şart |
| Web arayüzü / dashboard | CLI + JSON v1 için yeterli |
| Çoklu kullanıcı desteği | v1 yalnızca @ciftcibahadir |
| Tweet zamanlayıcı / scheduler | Kapsam dışı; ilk şikâyet konusu olacak ama v1 değil |
| Bulut yedekleme | Mirror verisi yerelde kalır; gizlilik avantajı |
| Otomatik tweet atma | Kullanıcı kontrolü şart; otomasyon riski |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SYNC-01 | Phase 1 | Complete |
| SYNC-02 | Phase 1 | Complete |
| SYNC-03 | Phase 1 | Complete |
| SYNC-04 | Phase 1 | Complete |
| SYNC-05 | Phase 1 | Complete |
| SYNC-06 | Phase 1 | Complete |
| SYNC-07 | Phase 1 | Complete |
| SYNC-08 | Phase 1 | Complete |
| SYNC-09 | Phase 1 | Complete |
| MEM-01 | Phase 1 | Complete |
| MEM-02 | Phase 1 | Complete |
| MEM-03 | Phase 1 | Complete |
| MEM-04 | Phase 1 | Complete |
| MEM-05 | Phase 1 | Complete |
| MSKILL-01 | Phase 2 | Complete |
| MSKILL-02 | Phase 2 | Complete |
| MSKILL-03 | Phase 2 | Complete |
| MSKILL-04 | Phase 2 | Complete |
| CRTR-01 | Phase 2 | Complete |
| CRTR-02 | Phase 2 | Complete |
| CRTR-03 | Phase 2 | Complete |
| CRTR-04 | Phase 2 | Complete |
| CRTR-05 | Phase 2 | Complete |
| MLSKILL-01 | Phase 3 | Pending |
| MLSKILL-02 | Phase 3 | Complete |
| MLSKILL-03 | Phase 3 | Complete |
| REFS-01 | Phase 3 | Pending |
| REFS-02 | Phase 3 | Pending |
| REFS-03 | Phase 3 | Pending |
| REFS-04 | Phase 3 | Pending |
| REFS-05 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after Phase 1 completion (01-04)*
