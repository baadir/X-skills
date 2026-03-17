# Phase 3: Miner, Lab + References - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Prompt-only skill belgelerini (Miner ve Lab) tamamla, referans dosyalarını güncelle, `decision.md` ve `strateji.md`'yi Phases 1-3 kararlarıyla güncel hale getir. Hiç kod yok. Python script yok. Sadece doküman güncellemesi.

</domain>

<decisions>
## Implementation Decisions

### Miner hedef hesap profili
- Hedef: 100K altı takipçi ama yüksek engagement'lı hesaplar
- Filtreleme kriteri: bookmark/like oranı > 0.3
- Rationale: @ciftcibahadir'in oranı 0.57 — benzer format kullanan hesaplar bu eşiği geçer
- SKILL.md'de format: Handle + niş açıklaması (her hesap: @handle, tahmini takipçi sayısı, neden değerli)

### Miner hesap keşif stratejisi
- Tamamen dinamik — sabit seed listesi yok
- Miner sorgu tabanlı keşfeder: nişle ilgili arama sorguları kullanır, engagement filtresi uygular
- SKILL.md'de örnek sorgular ve filtreleme mantığı yer almalı (sabit hesap isimleri değil)

### tweet_datasets.md güncelleme
- twikit 2.3.3'ü birincil "kendi tweet'lerini okuma" kaynağı olarak ekle
- Phase 1 migration kararını (tweepy → twikit) yansıt
- Eski resmi API Pro / tweepy referanslarını "v1'de kullanılmıyor" olarak işaretle

### x_algorithm_signals.md
- Olduğu gibi bırak — 19 sinyal kapsamlı ve Phase 1 araştırmasında doğrulandı
- Güncelleme gereksiz

### decision.md + strateji.md
- Tüm Phase 1-3 implementasyon kararlarını backfill et
- Minimum: twikit migration, async pattern, cookie auth, DNA report şeması, 7-gün staleness eşiği, TAHMINİ gate (<20 tweet)
- strateji.md'deki "Mirror veri saklama" açık noktasını kapat: Phase 1'de yerelde kalmaya karar verildi
- Diğer iki açık nokta (API auth yöntemi, veri sınırları) v2'ye bırak

### Claude's Discretion
- decision.md'deki karar formatı (mevcut formatı koru, değiştirme)
- strateji.md açık nokta kapanış şekli
- MLSKILL-03 "kapalı devre" işaretleme formatı

</decisions>

<specifics>
## Specific Ideas

- Miner SKILL.md'deki sorgu örnekleri "agentic AI", "multi-agent", "MCP tools", "vibe coding", "LangChain" gibi nişe özgü keyword'leri içermeli
- Lab SKILL.md zaten 518 satır — gereksinim odaklı kontrol et, büyük rewrite değil
- tweet_datasets.md'ye eklenecek twikit notu kısa olmalı: bir satır tanım + mirror_sync.py'ye referans

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/the-miner/SKILL.md` (620 satır): X API v2 endpoint'leri, arXiv/Kaggle entegrasyonu var. Eksik: dinamik hesap keşfi sorgu mantığı, bookmark/like filtresi.
- `skills/the-lab/SKILL.md` (518 satır): 6 boyutlu sınıflandırma, Batch API var. Kontrol: S/A/B/C tier sistemi tam mı?
- `references/x_algorithm_signals.md` (124 satır): 19 sinyal, Phoenix mimarisi — dokunma.
- `references/tweet_datasets.md` (150 satır): twikit eksik, tweepy/resmi API ağırlıklı.
- `decision.md`: Phase 1 öncesi mimari kararlar var. Phase 1-3 implementasyon kararları yok.
- `strateji.md`: 3 açık nokta var — Mirror saklama çözüldü, 2'si v2.

### Integration Points
- `tweet_datasets.md` → `skills/the-mirror/mirror_sync.py` bağlantısı eklenmeli
- `decision.md` → Phase 1-3 SUMMARY.md dosyalarından kararlar toplanarak backfill edilmeli

</code_context>

<deferred>
## Deferred Ideas

- x_algorithm_signals.md'ye Mirror/Creator DNA raporu bağlantısı — v2 refinement
- Miner API yetkilendirme yöntemi (OAuth2 vs API Key) — v2 milestone kararı
- Veri sınırları / tier yapısı — v2 milestone kararı

</deferred>

---

*Phase: 03-miner-lab-references*
*Context gathered: 2026-03-17*
