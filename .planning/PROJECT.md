# Multi-Skill Agent Ekosistemi — TwitterYoldas

## What This Is

Twitter/X'te organik büyümeyi hedefleyen, 4 skill'den oluşan hibrit bir AI ajan ekosistemi. Kapalı devre veri fabrikası (Miner + Lab) global trend verisi üretir; açık kaynak kullanıcı katmanı (Mirror + Creator) bu veriyi kullanıcının kişisel sesiyle harmanlayarak içerik önerileri sunar.

**v1.0 shipped:** 4 skill belgesi tamamlandı, Mirror sync çalışıyor, core product loop aktif (tweet data in → DNA report → voice-authentic content out).

## Core Value

Kullanıcının kendi ses tonunu koruyarak X algoritmasının öne çıkardığı formatları birleştiren, "yapay durmayan" içerik önerileri üretmek.

## Requirements

### Validated

- ✓ `mirror_sync.py` twikit 2.3.3 ile çalışıyor, cookie tabanlı auth, incremental sync — v1.0
- ✓ `style_memory.json` şeması dolu: hook patterns, tone profile, engagement snapshot, evolution_log — v1.0
- ✓ Mirror SKILL.md, `style_memory.json` şemasını belgeliyor, DNA raporu üretiyor — v1.0
- ✓ Creator SKILL.md, Mirror DNA raporunu alıp Mod 1 (Brainstorm) ve Mod 3 (Analiz) çalıştırıyor — v1.0
- ✓ Miner SKILL.md, hedef hesapları ve priority_score formülünü içeriyor (prompt-only) — v1.0
- ✓ Lab SKILL.md, 6-boyutlu sınıflandırma ve S/A/B/C tier sistemini içeriyor (prompt-only) — v1.0
- ✓ `references/x_algorithm_signals.md` 19 sinyal ağırlığını, author diversity formülünü ve Phoenix mimarisini içeriyor — v1.0
- ✓ `references/tweet_datasets.md` twikit 2.3.3 kaynaklarını listeler — v1.0
- ✓ `decision.md` ve `strateji.md` güncel, tüm Phase 1-3 kararlarını yansıtıyor — v1.0

### Active

- [ ] Mirror SKILL.md dual schema conflict çözüldü (`last_updated` → `last_synced_at`, eski tone key'leri kaldırıldı)
- [ ] `top_signal_breakdown.shares` `update_performance_snapshot()` tarafından hesaplanıyor
- [ ] Miner SKILL.md pipeline diyagramındaki `[ The Writer ]` → `[ The Creator ]` düzeltildi
- [ ] VALIDATION.md dosyaları `status: draft`'tan gerçek compliance durumuna güncellendi
- [ ] Root-level `.gitignore` eklendi (şu an yalnızca `skills/the-mirror/.gitignore` mevcut)

### Out of Scope

- Miner/Lab backend kodu (scraper, etiketleyici) — v1 prompt-only; kod moat sonraki milestone
- SaaS abonelik sistemi — önce kendi kullanımı için doğrulama şart
- Web arayüzü / dashboard — CLI ve JSON v1 için yeterli
- Çoklu kullanıcı desteği — v1 yalnızca @ciftcibahadir
- Otomatik Miner→Lab→Mirror→Creator pipeline — v1 manuel; orchestration v2
- Bulut yedekleme — Mirror verisi yerelde kalır; gizlilik avantajı

## Context

**Current state (v1.0):**
- `skills/the-mirror/mirror_sync.py`: 957 LOC, twikit 2.3.3, 15 unit tests passing
- `skills/the-mirror/SKILL.md`: 1110 lines, DNA report schema, staleness check, TAHMINI gate
- `skills/the-creator/SKILL.md`: 849 lines, DNA input protocol, Mod 3 algorithm signal rationale
- `skills/the-miner/SKILL.md`: 665+ lines, prompt-only, Hedef Hesap Profili, priority_score
- `skills/the-lab/SKILL.md`: prompt-only, JSONL schema, 6-dim classification, S/A/B/C tiers
- `references/x_algorithm_signals.md`: 19 signals, author diversity decay, Phoenix architecture
- `references/tweet_datasets.md`: twikit 2.3.3 as v1 primary method
- `decision.md`: Phase 1 (7 decisions) + Phase 2 (5 decisions) + original 3 blocks
- `strateji.md`: section 6.3 closed (local storage), 6.1 + 6.2 open as v2 items
- Tests: 24 automated tests passing (`pytest skills/ -v`)

**Hedef kullanıcı:** @ciftcibahadir — Agentic AI nişi, 254.8K impressions, engagement %2.3, bookmark/like 0.57, RT/like 0.012

**Tech debt from v1.0:** See `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — 9 items, no blockers.

## Constraints

- **Tech Stack**: Python — twikit 2.3.3, cookie-based auth
- **Hosting**: Yerel / kendi sunucu — platform bağımlılığı yok
- **API Maliyeti**: Sıfır — twikit cookie tabanlı ücretsiz
- **Kapsam**: Kod üretimi mirror_sync.py ile sınırlı; diğer skill'ler prompt belgesi
- **Veri Gizliliği**: Mirror verisi yerelde tutulur (`style_memory.json`), buluta yedekleme yok

## Key Decisions

| Karar | Gerekçe | Sonuç |
|-------|---------|-------|
| Hibrit mimari (Kapalı + Açık) | Miner/Lab "moat" oluşturur, Mirror/Creator topluluk değeri sağlar | ✓ Good — v1 doğrulandı |
| V1 kapsam: Skill'ler + Mirror Sync | Hızlı doğrulama, sıfır altyapı maliyeti | ✓ Good — 31 req, 1 günde tamamlandı |
| Python backend | Twikit ekosistemi, AI entegrasyon kolaylığı | ✓ Good — twikit 2.3.3 stabil |
| Yerel hosting | Kontrol, maliyet sıfır, gizlilik | ✓ Good — `style_memory.json` local |
| Ücretsiz API önceliği | X resmi API ücretli; twikit cookie tabanlı ücretsiz | ✓ Good — twikit çalışıyor |
| Mirror verisi yerelde | Open source topluluğu için gizlilik avantajı, v1 basitliği | ✓ Good — strateji.md 6.3 kapatıldı |
| Prompt-only Miner+Lab v1 | Kod moat'ı v2'ye ertele, v1'de kullanılabilirliği doğrula | ✓ Good — SKILL.md'ler tamamlandı |
| twikit 2.3.3 (tweepy'den migrasyon) | view_count + bookmark_count ücretsiz, tweepy öldü | ✓ Good — tüm metrikler çalışıyor |
| Atomic write (mkstemp + os.replace) | Crash-safe; veri kaybını önler | ✓ Good — test_crash_safety geçiyor |
| 7-gün staleness eşiği | Dengeli: çok sık uyarı değil, veri kalitesi korunuyor | ✓ Good — Mirror SKILL doğrulandı |

---
*Last updated: 2026-03-17 after v1.0 milestone*
