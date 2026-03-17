# Phase 3: Miner, Lab + References — Research

**Researched:** 2026-03-17
**Domain:** Documentation editing — prompt-only skill files, reference docs, decision/strategy backfill
**Confidence:** HIGH (all source files read directly; no external research needed for a documentation phase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Miner hedef hesap profili:** Hedef 100K altı takipçi, bookmark/like oranı > 0.3 olan hesaplar. @ciftcibahadir oranı 0.57 — benzer format kullanan hesaplar bu eşiği geçer. SKILL.md format: Handle + niş açıklaması (her hesap: @handle, tahmini takipçi sayısı, neden değerli)
- **Miner hesap keşif stratejisi:** Tamamen dinamik — sabit seed listesi yok. Miner sorgu tabanlı keşfeder: nişle ilgili arama sorguları kullanır, engagement filtresi uygular. SKILL.md'de örnek sorgular ve filtreleme mantığı yer almalı (sabit hesap isimleri değil)
- **tweet_datasets.md güncellemesi:** twikit 2.3.3'ü birincil "kendi tweet'lerini okuma" kaynağı olarak ekle; Phase 1 migration kararını (tweepy → twikit) yansıt; eski resmi API Pro / tweepy referanslarını "v1'de kullanılmıyor" olarak işaretle
- **x_algorithm_signals.md:** Olduğu gibi bırak — 19 sinyal kapsamlı ve Phase 1 araştırmasında doğrulandı. Güncelleme gereksiz.
- **decision.md + strateji.md backfill:** Tüm Phase 1-3 implementasyon kararlarını backfill et. Minimum: twikit migration, async pattern, cookie auth, DNA report şeması, 7-gün staleness eşiği, TAHMINİ gate (<20 tweet). strateji.md'deki "Mirror veri saklama" açık noktasını kapat: Phase 1'de yerelde kalmaya karar verildi. Diğer iki açık nokta (API auth yöntemi, veri sınırları) v2'ye bırak.

### Claude's Discretion

- decision.md'deki karar formatı (mevcut formatı koru, değiştirme)
- strateji.md açık nokta kapanış şekli
- MLSKILL-03 "kapalı devre" işaretleme formatı

### Deferred Ideas (OUT OF SCOPE)

- x_algorithm_signals.md'ye Mirror/Creator DNA raporu bağlantısı — v2 refinement
- Miner API yetkilendirme yöntemi (OAuth2 vs API Key) — v2 milestone kararı
- Veri sınırları / tier yapısı — v2 milestone kararı
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MLSKILL-01 | `the-miner/SKILL.md` niş hesap listesini, veri toplama formatını ve priority score formülünü içeriyor | Gap analysis below: priority score formülü MEVCUT (satır 356-366); hedef hesap profili ve dinamik keşif stratejisi EKSİK (mevcut sabit tier listesi yerine dinamik + bookmark/like > 0.3 filtre mantığı) |
| MLSKILL-02 | `the-lab/SKILL.md` batch etiketleme prompt şemasını (JSONL), 6-dimension classification ve S/A/B/C tier sistemini içeriyor | Gap analysis below: JSONL batch şeması MEVCUT (satır 188-191); 6-boyut MEVCUT; S/A/B/C tier tanımları MEVCUT (satır 303-308) — tek eksik: "prompt-only" işaretlemesi |
| MLSKILL-03 | Miner ve Lab SKILL.md dosyaları prompt-only (kod yok), kapalı devre olarak işaretlenmiş | Gap analysis below: Her iki dosya da işaretlenmemiş — Python code block'ları var, "prompt-only / kapalı devre" bildirimi yok |
| REFS-01 | `references/x_algorithm_signals.md` 19 sinyal ağırlıklarını, author diversity decay formülünü ve Phoenix mimarisini içeriyor | MEVCUT ve eksiksiz — dokunma |
| REFS-02 | `references/tweet_datasets.md` ücretsiz dataset kaynakları ve kullanılabilir kütüphaneleri listeler | EKSİK: twikit 2.3.3 referansı yok; tweepy script birincil yöntem olarak gösteriliyor — güncelleme gerekli |
| REFS-03 | `decision.md` tüm mimari kararları tarihiyle birlikte kayıt altında tutuyor | EKSİK: Phase 1-2 implementasyon kararları (twikit migration, async pattern, cookie auth, DNA report şeması, staleness eşiği, TAHMINI gate) yok |
| REFS-04 | `strateji.md` hibrit mimariyi, iş modelini ve açık noktaları tanımlıyor | KISMI EKSİK: Hibrit mimari ve iş modeli mevcut; 6.3 Mirror Veri Saklama açık noktası hâlâ "⏳ Bekliyor" — Phase 1'de yerel kalmaya karar verildi, kapatılmalı |
</phase_requirements>

---

## Summary

Phase 3 tamamen dokümantasyon düzenlemesidir. Hiç kod yazılmaz, hiç script çalıştırılmaz. Tüm deliverable'lar mevcut markdown dosyalarına yapılan hedefli eklemeler ve düzeltmelerdir.

Gap analizi şunu ortaya koyuyor: **the-lab/SKILL.md neredeyse eksiksiz** — JSONL şeması, 6-boyut sınıflandırma ve S/A/B/C tier sistemi zaten var. Tek eksik: prompt-only / kapalı devre işareti ve Python code block'larının temizlenmesi veya işaretlenmesi. **the-miner/SKILL.md** ise iki önemli boşluk içeriyor: (1) mevcut sabit tier listesi, kararlaştırılan dinamik keşif stratejisiyle çelişiyor; (2) bookmark/like > 0.3 filtreleme kriterini açıkça içermiyor. **tweet_datasets.md** güncellenmesi en kolay iş — kısa bir twikit notu eklenip tweepy script'i "v1'de kullanılmıyor" olarak işaretlenecek. **decision.md** en büyük backfill işidir — 01-SUMMARY ve 02-SUMMARY dosyalarından ~12 karar toplanarak mevcut formatta loglanacak. **strateji.md** ise sadece 6.3 bölümünü kapatmayı gerektiriyor.

**Primary recommendation:** Her dosyayı ayrı bir plan göreviyle ele al. Doğrulama için grep/string-search yeterli — her hedef string bir test.

---

## Gap Analysis (Kritik Bulgular)

### MLSKILL-01: the-miner/SKILL.md Durumu

**MEVCUT (dokunma):**
- Priority score formülü: satır 356-366 — `(likes*1.0 + retweets*2.5 + replies*1.5 + quotes*3.0 + bookmarks*4.0) / impressions * 100` — tam ve doğru
- Çıktı formatı (JSON koleksiyon wrapper): satır 226-276 — tam ve doğru
- Minimum eşikler: satır 328-352 — kapsamlı
- Arama sorgu örnekleri: satır 62-85 — nişe özgü, iyi

**EKSİK / YANLIŞ (düzeltilmeli):**
1. **Hedef hesap profili eksik:** Mevcut dosya sabit tier listesi içeriyor (Tier 1: @sama, @karpathy vb.). Kararlaştırılan yaklaşım ise tamamen dinamik — "100K altı, bookmark/like > 0.3" filtresiyle sorgu tabanlı keşif. Sabit liste silinmemeli ama "bu sabit hesaplar değil, dinamik keşfin başlangıç örnekleridir" şeklinde yeniden çerçevelenmeli.
2. **bookmark/like > 0.3 filtresi yok:** "Hedef hesap profili" bölümü yok. Bu kriterin (100K altı, bookmark/like > 0.3) açıkça belgelenmesi gerekiyor. @ciftcibahadir'in kendi oranı (0.57) referans örnek olarak yer almalı.
3. **Python code block'ları var:** Satır 316-321, 457-519, 575-577. MLSKILL-03 gereği bu bloklar ya silinmeli ya da "v2 — bu kod şu an çalışmıyor; prompt-only phase'de kavramsal referans" olarak işaretlenmeli. Kararlaştırılan yaklaşım: işaretlemek daha güvenli (silinirse bağlam kaybolur).
4. **Prompt-only / kapalı devre bildirimi yok:** Dosyanın başına veya uygun bir bölüme eklenmeli.

**Mevcut "Hedef Hesaplar" bölümü (satır 281-322) için plan:**
- Bölümü silme — sadece çerçeveyi değiştir
- Başına "Bu hesaplar sabit bir liste değil; dinamik keşfin kalitesini doğrulamak için referans örneklerdir" notunu ekle
- Yeni bir "Dinamik Hesap Keşfi" bölümü ekle: bookmark/like > 0.3 kriteri, 100K altı takipçi filtresi, @ciftcibahadir oranı (0.57) örnek olarak

### MLSKILL-02: the-lab/SKILL.md Durumu

**MEVCUT (dokunma):**
- JSONL batch prompt şeması: satır 188-191 — iki satır JSONL örneği var, format doğru
- 6-boyutlu sınıflandırma: satır 36-119 — tam ve eksiksiz (Psikolojik Tetikleyici, İçerik Formu, Ton, Kanca Tipi, Görsel Format, Algoritma Sinyal Tahmini)
- S/A/B/C tier tanımları: satır 303-308 — Referans (S-tier: 9-10), Yüksek (A-tier: 7-8), Orta (B-tier: 4-6), Düşük (C-tier: 1-3) — tam ve açık

**EKSİK / YANLIŞ:**
1. **Python code block'u yok** — Lab SKILL.md'de Python kodu bulunmuyor. Bu iyi.
2. **Prompt-only / kapalı devre bildirimi yok** — Dosyanın başına eklenmeli.
3. **MLSKILL-03 uyum notu:** Sistem promptu metin bloğu (satır 129-147) ve kullanıcı promptu (satır 149-184) Python değil, düz metin — bu zaten prompt-only. Ancak bunu açıkça işaretleyen bir başlık/bildirim yok.

### MLSKILL-03: Prompt-only / Kapalı Devre İşaretleme

Her iki SKILL.md dosyasında yapılacak iki şey:
1. YAML frontmatter'a `status: prompt-only` ve `circuit: closed` alanları ekle
2. İçerik bölümüne kısa bir "Kapsam Sınırı" notu ekle: "Bu skill şu an prompt-only'dir. v2 milestone'da Python implementation eklenecek. Kod bloğu varsa kavramsal referans amaçlıdır."

### REFS-01: x_algorithm_signals.md Durumu

**MEVCUT ve EKSİKSİZ — dokunma.**

Kontrol edilen içerik:
- 19 engagement sinyali: satır 38-65 — 14 pozitif + 4 negatif = 18 etiket; sinyal 19 "DM share" başlığı ayrı. Sayım doğru.
- Author diversity decay formülü: satır 72-74 — `multiplier = (1.0 - floor) × decay_factor^position + floor` — mevcut
- Phoenix mimarisi: satır 86-97 — Grok-1 tabanlı transformer, input/output boyutları, candidate isolation — mevcut

REFS-01 gereksinimi zaten karşılanıyor. Dokunmak gerekmez.

### REFS-02: tweet_datasets.md Durumu

**EKSİK olan:**
1. twikit 2.3.3 referansı yok — dosya tamamen tweepy tabanlı
2. Satır 44-122: `import tweepy` kullanan bir script birincil yöntem olarak sunuluyor — Phase 1'de tweepy'nin null impressions sorunu nedeniyle twikit'e geçildi; bu script yanıltıcı
3. mirror_sync.py bağlantısı yok

**Eklenecekler (CONTEXT.md kararı):**
- Yeni bölüm: "Kendi Tweet'lerini Okuma — twikit 2.3.3 (v1 Birincil Yöntem)"
  - Bir satır tanım: twikit 2.3.3, cookie tabanlı auth
  - mirror_sync.py referansı: `skills/the-mirror/mirror_sync.py`
  - Neden twikit: tweepy Free tier `impression_count` null döndürüyor
- Mevcut tweepy script bölümüne "⚠️ v1'de kullanılmıyor" işareti

**Dokunulmayacaklar:** Açık dataset listesi (satır 10-35), Manuel Kurasyon bölümü (satır 143-150)

### REFS-03: decision.md Durumu

**Mevcut:** 3 karar bloğu var — hepsi pre-Phase-1 mimari kararlar.

**Eksik kararlar (01-SUMMARY + 02-SUMMARY + STATE.md'den):**

Phase 1 implementasyon kararları:
1. tweepy → twikit 2.3.3 migrasyonu (cookie auth, null impressions nedeni)
2. twikit Client singleton — modül seviyesinde
3. `view_count` denominator (`impression_count` yerine) — twikit breaking change
4. Atomic write: same-dir tempfile + os.replace (Windows cross-device güvenliği)
5. `asyncio.run(main())` — Python 3.10+ Windows ProactorEventLoop
6. Cutoff precedence: `--since` > `last_synced_at` > None
7. `evolution_log` guard: not dry_run AND new_tweets non-empty

Phase 2 implementasyon kararları:
8. DNA report şeması: `voice_dna`, `data_confidence`, `hook_arsenal`, `cta_guidance`, `sync_status` alanları
9. 7-gün staleness eşiği (`is_stale: true` tetikleyicisi)
10. TAHMINI gate: <20 tweet için `data_confidence: "TAHMINI"`
11. Creator SKILL.md additive-only edit stratejisi (satır 740 sonrası ekleme)
12. Named field references: `voice_dna.signature_terms`, `cta_guidance.recommended_ctas`

**Format:** Mevcut `## [2026-03-17] — Başlık` formatını koru. Her karar için: Karar, Bağlam, Neden, Sonuç, Durum.

### REFS-04: strateji.md Durumu

**Mevcut:** Hibrit mimari, iş modeli, pipeline diyagramı, çözülen çelişkiler — hepsi mevcut ve iyi.

**Eksik:** Bölüm 6.3 "Mirror Veri Saklama Yeri" hâlâ "⏳ Bekliyor" — Phase 1'de yerel kalmaya karar verildi.

**Yapılacak:**
- 6.3 başlığında `**Durum:** ⏳ Bekliyor` → `**Durum:** ✅ Karar verildi — 2026-03-17`
- Karar metni ekle: "Phase 1'de yerel saklama seçildi. Gizlilik avantajı, open-source kullanıcılar için cazip. Ücretli plan için opsiyonel şifreli bulut yedek v2'de değerlendirilecek."
- Versiyon geçmişine satır ekle

**6.1 ve 6.2:** v2'ye bırakılıyor — dokunma.

---

## Architecture Patterns

### Bu Fazın Çalışma Modeli: Additive-only Editing

Phase 2'de başarıyla kullanılan ve test edilmiş pattern:
- Mevcut satırları değiştirme — sadece sona veya uygun bölüme ekle
- Yeni bölümler, eski bölümleri "override" ettiğini açıkça belirt
- Verifikasyon: grep ile hedef string'in varlığını kontrol et

### Verifikasyon Stratejisi (MLSKILL-01 — REFS-04)

Phase 2'de işe yarayan string-search pattern burada da geçerlidir. Her gereksinim için bir hedef string belirle:

| Gereksinim | Hedef String | Dosya |
|------------|-------------|-------|
| MLSKILL-01 bookmark filtresi | `bookmark/like.*0.3` veya `bookmark.*like.*oran` | the-miner/SKILL.md |
| MLSKILL-01 priority score | `priority_score` | the-miner/SKILL.md |
| MLSKILL-01 dinamik keşif | `dinamik` | the-miner/SKILL.md |
| MLSKILL-02 JSONL | `custom_id` | the-lab/SKILL.md |
| MLSKILL-02 S-tier | `S-tier` veya `Referans.*9-10` | the-lab/SKILL.md |
| MLSKILL-03 Miner | `prompt-only` | the-miner/SKILL.md |
| MLSKILL-03 Lab | `prompt-only` | the-lab/SKILL.md |
| REFS-01 | Dokunulmayacak — PASS |  |
| REFS-02 twikit | `twikit 2.3.3` | tweet_datasets.md |
| REFS-02 eski tweepy | `v1.*kullanılmıyor` veya `kullanılmıyor` | tweet_datasets.md |
| REFS-03 twikit migration | `tweepy.*twikit` | decision.md |
| REFS-03 DNA şeması | `data_confidence` | decision.md |
| REFS-04 | `Karar verildi` veya `yerel.*saklama` | strateji.md |

### Doğrulama Komutu Şablonu

```bash
# Her gereksinim için:
grep -n "hedef_string" "dosya_yolu"
# Satır numarası dönüyorsa PASS, yoksa FAIL
```

---

## Don't Hand-Roll

| Problem | Yapma | Yap |
|---------|-------|-----|
| Mevcut dosyaları sıfırdan yeniden yaz | Büyük rewrite — bağlam kaybolur, Phase 2 additive edit'leri bozulabilir | Hedefli ekleme / küçük düzeltme |
| x_algorithm_signals.md'yi güncelle | Kararlaştırıldı: dokunma | Olduğu gibi bırak |
| Python code'u gerçekten sil | Silinirse kavramsal bağlam kaybolur | "v2 referans" notu ekle veya "prompt-only" bildirim |
| decision.md formatını değiştir | Mevcut format arama ve okuma için optimize edilmiş | Aynı `## [tarih] — Başlık` formatını koru |

---

## Common Pitfalls

### Pitfall 1: Sabit Tier Listesini Silmek
**What goes wrong:** the-miner/SKILL.md'deki Tier 1/2/3 hesap listesi silinirse referans örnekler kaybolur.
**Why it happens:** "Dinamik keşif" kararı sabit liste ile çelişiyor gibi görünüyor.
**How to avoid:** Silme — sadece çerçeveyi değiştir. "Bu liste sabit hedef değil, dinamik keşfin kalibrasyon referansı" notunu ekle.

### Pitfall 2: Phase 2 Additive Editlerini Bozmak
**What goes wrong:** the-mirror/SKILL.md veya the-creator/SKILL.md'de satır numaralarına göre işlem yapılırsa Phase 2'de eklenen satırlar kayıt dışı kalabilir.
**Why it happens:** Phase 2 additive-only edit yaptı; satır numaraları değişti.
**How to avoid:** Phase 3 bu dosyalara dokunmuyor zaten (kapsam dışı). Sadece the-miner ve the-lab SKILL.md'leri düzenleniyor.

### Pitfall 3: decision.md Backfill'i Aşırı Büyütmek
**What goes wrong:** Her küçük teknik detayı ayrı karar bloğu olarak yazmak dosyayı şişirir.
**How to avoid:** Benzer kararları grupla. Örneğin Phase 1 teknik kararlarını tek blokta logla: "Phase 1 — twikit migration ve async pattern kararları" başlığı altında liste.

### Pitfall 4: REFS-01'e Dokunmak
**What goes wrong:** x_algorithm_signals.md'yi güncelleme isteği gelebilir çünkü "19 sinyal" kontrolü yaparken içerik cazip görünüyor.
**How to avoid:** CONTEXT.md'de kilitli: "Olduğu gibi bırak." REFS-01 gereksinimi zaten karşılanmış durumda.

### Pitfall 5: Versiyon Geçmişini Güncellemeyi Unutmak
**What goes wrong:** strateji.md'de 6.3 kapatılır ama Bölüm 7 "Versiyon Geçmişi" tablosu güncellenmez.
**How to avoid:** strateji.md görevi sona erdiğinde versiyon tablosuna satır eklemeyi kontrol et.

---

## Code Examples

### Miner SKILL.md — Eklenecek "Hedef Hesap Profili" Bölümü

```markdown
## Hedef Hesap Profili (Dinamik Keşif)

The Miner sabit bir hesap listesiyle çalışmaz. Hesapları sorgu tabanlı dinamik olarak keşfeder.

### Hedef Kriter

| Kriter | Eşik | Rationale |
|--------|------|-----------|
| Takipçi sayısı | < 100.000 | Büyük hesaplar niş değil, viral kitle yapısı |
| Bookmark / Like oranı | > 0.3 | "Kaydedilesi" içerik üretenler; format kalitesinin proxy'si |
| Engagement rate | Niş ortalamasının üstü | Mutlak sayı değil, hesap büyüklüğüne göre normalize |

**Referans örnek:** @ciftcibahadir — bookmark/like oranı 0.57 (Mart 2026 ölçümü). Bu eşiği geçen hesaplar benzer format kullanıcısıdır.

### Dinamik Keşif Sorguları

```
# Niş arama + engagement filtresi
(agentic AI OR multi-agent OR MCP OR vibe coding) lang:en -is:retweet min_faves:200

# Sonuçlardan hesap keşfi: hangi hesaplar bookmark/like > 0.3 oranına sahip?
# Manuel veya otomatik filtreleme:
- author_followers < 100000
- bookmarks / likes > 0.3 (en az 10 veri noktası gerekli — küçük örnekte yanıltıcı)
```

**Not:** Aşağıdaki "Hedef Hesaplar (Niş Referansları)" bölümü sabit hedef değildir — dinamik keşfin sonuçlarını kalibre etmek için referans örneklerdir.
```

### tweet_datasets.md — Eklenecek twikit Bölümü

```markdown
## Kendi Tweet'lerini Okuma — twikit 2.3.3 (v1 Birincil Yöntem)

**Kütüphane:** twikit 2.3.3 — cookie tabanlı auth
**Uygulama:** `skills/the-mirror/mirror_sync.py`
**Neden twikit:** tweepy Free tier `impression_count` null döndürür; twikit `view_count` dolu döndürür.

> **Phase 1 kararı (2026-03-17):** mirror_sync.py tweepy'den twikit 2.3.3'e migrate edildi.
> Detay: `decision.md` — "Phase 1 — twikit migration" girdisi.
```

### decision.md — Yeni Karar Bloğu Formatı (Phase 1 örnek)

```markdown
## [2026-03-17] — Phase 1: twikit Migration ve Async Pattern Kararları

**Kararlar:**
1. tweepy → twikit 2.3.3: Free tier tweepy `impression_count` null döndürüyor — tüm engagement hesaplamalarını bozuyor
2. view_count denominator: twikit'te `impression_count` yerine `view_count` kullanılıyor (twikit breaking change)
3. Cookie auth: `cookies.json` ile authenticate — bearer token gerektirmiyor, düşük hacimli kullanımda bot-detection riski düşük
4. asyncio.run(main()): Python 3.10+ Windows ProactorEventLoop — get_event_loop().run_until_complete() yerine
5. Cutoff precedence: --since > last_synced_at > None (ilk çalıştırma)
6. Atomic write: same-dir tempfile + os.replace — Windows cross-device rename güvenliği
7. evolution_log guard: not dry_run AND new_tweets non-empty — sıfır sonuçlu sync'te boş log girişi oluşturma

**Durum:** Tamamlandı — Phase 1 planları 01-01 ile 01-04
```

---

## State of the Art

| Eski Yaklaşım | Şu Anki Yaklaşım | Ne Zaman Değişti | Etki |
|---------------|-----------------|-----------------|------|
| tweepy ile tweet çekme | twikit 2.3.3, cookie auth | Phase 1, 2026-03-17 | view_count > 0, bookmark_count dolu |
| Miner/Lab = tek monolitik skill | 4 ayrı skill pipeline | Pre-Phase-1 mimari kararı | Her skill bağımsız güncellenebilir |
| Sabit hedef hesap listesi | Dinamik sorgu tabanlı keşif | Phase 3 (bu faz) | Bakım gerektirmez, otomatik güncel |

**Deprecated/outdated:**
- tweepy Free tier için tweet çekme: v1'de kullanılmıyor, tweet_datasets.md'de işaretlenecek
- Sabit Miner hesap listesi: Kavramsal referans olarak kalır ama "sabit hedef" çerçevesi kaldırılır

---

## Open Questions

1. **the-miner/SKILL.md'deki Python code block'larına ne olacak?**
   - What we know: MLSKILL-03 "kod yok" diyor; sayfada Python var (satır 316-321, 457-519, 575-577)
   - What's unclear: Silmek mi, "v2 referans" notu eklemek mi?
   - Recommendation: "v2 referans" notu ekle — silmek kavramsal bağlamı yok eder; işaretlemek gereksinimi karşılar ve bağlamı korur. CONTEXT.md "prompt-only" işaretleme formatı Claude'un takdirine bırakıyor.

2. **decision.md backfill için granülarite seviyesi**
   - What we know: 12 karar tespit edildi; mevcut dosya 3 blok içeriyor, her blok birden fazla kararı kapsamlı biçimde açıklıyor
   - What's unclear: Her karar ayrı blok mu olmalı yoksa gruplanabilir mi?
   - Recommendation: Phase 1 kararlarını tek blok, Phase 2 kararlarını tek blok olarak grupla — mevcut dosyanın "karar tematik grup" formatıyla uyumlu

---

## Validation Architecture

> Bu faz için nyquist_validation durumu .planning/config.json'a göre değerlendirildi.

### Bu Faz İçin Test Stratejisi

Phase 3 tamamen dokümantasyon değişikliği olduğundan unit test framework gerekmez. Phase 2'de kullanılan string-search doğrulama pattern bu faz için yeterli ve uygun.

### Phase Requirements — Test Haritası

| Req ID | Davranış | Test Tipi | Komut | Durum |
|--------|----------|-----------|-------|-------|
| MLSKILL-01 | bookmark/like > 0.3 kriteri SKILL.md'de mevcut | string-search | `grep -n "0.3" "skills/the-miner/SKILL.md"` | Wave 0: Fail (henüz yok) |
| MLSKILL-01 | Dinamik keşif stratejisi mevcut | string-search | `grep -n "dinamik" "skills/the-miner/SKILL.md"` | Wave 0: Fail |
| MLSKILL-01 | priority_score formülü mevcut | string-search | `grep -n "priority_score" "skills/the-miner/SKILL.md"` | Zaten PASS |
| MLSKILL-02 | custom_id (JSONL) mevcut | string-search | `grep -n "custom_id" "skills/the-lab/SKILL.md"` | Zaten PASS |
| MLSKILL-02 | S-tier tanımı mevcut | string-search | `grep -n "S-tier" "skills/the-lab/SKILL.md"` | Zaten PASS |
| MLSKILL-03 | Miner prompt-only işareti | string-search | `grep -n "prompt-only" "skills/the-miner/SKILL.md"` | Wave 0: Fail |
| MLSKILL-03 | Lab prompt-only işareti | string-search | `grep -n "prompt-only" "skills/the-lab/SKILL.md"` | Wave 0: Fail |
| REFS-01 | x_algorithm_signals.md değişmedi | string-search | `grep -n "decay_factor" "references/x_algorithm_signals.md"` | Zaten PASS |
| REFS-02 | twikit 2.3.3 referansı mevcut | string-search | `grep -n "twikit 2.3.3" "references/tweet_datasets.md"` | Wave 0: Fail |
| REFS-02 | tweepy "kullanılmıyor" işareti | string-search | `grep -rn "kullanılmıyor" "references/tweet_datasets.md"` | Wave 0: Fail |
| REFS-03 | twikit migration kararı loglu | string-search | `grep -n "twikit" "decision.md"` | Wave 0: Fail |
| REFS-03 | DNA şeması kararı loglu | string-search | `grep -n "data_confidence" "decision.md"` | Wave 0: Fail |
| REFS-04 | Mirror saklama kararı kapatıldı | string-search | `grep -n "Karar verildi\|yerel.*sakla" "strateji.md"` | Wave 0: Fail |

### Wave 0 Gaps

- [ ] Tüm FAIL olan test'ler Wave 0 (ilk plan) baseline olarak belgelenecek; her sonraki plan kendi hedefini geçirmeli

*(Test framework kurulumu gerekmez — grep komutları plan task verification adımlarında çalıştırılır)*

---

## Sources

### Primary (HIGH confidence)
- `skills/the-miner/SKILL.md` — direkt okuma; 620 satır, priority score formülü (satır 356-366), hesap tier listesi (satır 281-322), arXiv/Kaggle entegrasyonu doğrulandı
- `skills/the-lab/SKILL.md` — direkt okuma; 518 satır, JSONL batch şeması (satır 188-191), 6-boyut sınıflandırma (satır 36-119), S/A/B/C tier (satır 303-308) doğrulandı
- `references/x_algorithm_signals.md` — direkt okuma; 19 sinyal, decay formülü, Phoenix mimarisi — REFS-01 zaten karşılanmış
- `references/tweet_datasets.md` — direkt okuma; tweepy script birincil yöntem, twikit yok — güncelleme gerekli
- `decision.md` — direkt okuma; 3 pre-Phase-1 blok; Phase 1-2 implementasyon kararları eksik
- `strateji.md` — direkt okuma; 6.3 Mirror Veri Saklama "⏳ Bekliyor" hâlâ açık
- `.planning/phases/01-mirror-foundation/01-04-SUMMARY.md` — direkt okuma; 7 Phase 1 karar tespit edildi
- `.planning/phases/02-mirror-creator-integration/02-03-SUMMARY.md` — direkt okuma; 5 Phase 2 karar tespit edildi
- `.planning/phases/03-miner-lab-references/03-CONTEXT.md` — direkt okuma; kilitli kararlar ve kapsam dışı konular

---

## Metadata

**Confidence breakdown:**
- Gap analysis (MLSKILL-01-03, REFS-01-04): HIGH — tüm dosyalar direkt okundu, her gereksinim satır numarasıyla doğrulandı
- Backfill kararlar listesi (REFS-03): HIGH — SUMMARY dosyaları ve STATE.md'den çapraz doğrulama yapıldı
- Verifikasyon stratejisi: HIGH — Phase 2'de çalışan string-search pattern

**Research date:** 2026-03-17
**Valid until:** Bu faz tamamlanana kadar (stabil dokümantasyon, harici bağımlılık yok)
