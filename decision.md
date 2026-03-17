# Decision Log — TwitterYoldas Skill

---

## [2026-03-17] — Skill Veri Kaynağı Stratejisi

**Karar:** Skill'i beslemek için önce otomatik/açık veri kaynaklarıyla başla, sonra manuel fine-tune et.

**Bağlam:**
TwitterYoldas skill'i şu an genel Twitter büyüme bilgisiyle çalışıyor. Skill'e "tutmuş tweetlerin" yapısını ve X algoritmasının gerçek sinyal ağırlıklarını öğretirsek, brainstorming ve analitik modlarda çok daha somut ve kanıta dayalı öneriler verebilir.

**Değerlendirilen seçenekler:**
1. **Otomatik veri kaynakları** — `xai-org/x-algorithm` reposu + Hugging Face tweet engagement dataset'leri
2. **Manuel kurasyon** — Kullanıcının kendi yüksek etkileşimli tweetleri + nişindeki büyük hesaplar

**Neden 1. seçenek önce:**
- Daha geniş kapsamlı, genel geçer pattern'ler içeriyor
- Tekrar edilebilir ve güncellenebilir
- Manuel kurasyon emek yoğun; önce otomatik baz kurulursa manuel ekleme daha verimli olur
- xai-org/x-algorithm, algoritmanın resmi (veya yarı-resmi) kaynak koduna en yakın açık referans

**Sonraki adım:**
xai-org/x-algorithm reposunu analiz et, Hugging Face'de AI/tech nişine uygun tweet engagement dataset'i bul. Bulgular `twitter-yoldas/references/` altına eklenecek.

**Fine-tune kararı:**
Otomatik veri kaynakları eklendikten sonra sonuçlara bakılacak. Skill hâlâ "çok genel" öneriler veriyorsa kullanıcının kendi tweet geçmişi manuel olarak eklenecek.

**Durum:** Tamamlandı

**Sonuç:**
- `references/x_algorithm_signals.md` oluşturuldu — 19 engagement sinyali, ağırlık formülü, author diversity cezası, filtreler, Phoenix mimarisi
- `references/tweet_datasets.md` oluşturuldu — bilinen kaynaklar + X API v2 veri toplama script'i
- GitHub rate limit nedeniyle bazı Rust/Scala dosyalarına erişilemedi, ancak kritik bilgiler README ve Python dosyalarından alındı
- Hugging Face authentication gerektiriyor; alternatif olarak Kaggle + X API önerildi

---

## [2026-03-17] — Multi-Skill Mimari Kararı (The Miner / Lab / Mirror / Creator)

**Karar:** TwitterYoldas'ı tek skill yerine 4 skill'li hiyerarşik bir pipeline olarak yeniden tasarla.

**Bağlam:**
Tek skill yaklaşımı global viral pattern'leri ve kullanıcının kişisel stilini aynı anda taşımakta zorlanıyor. Kullanıcı, modüler ve ölçeklenebilir bir mimari önerdi.

**Mimari:**
| Skill | Görev | Veri |
|-------|-------|------|
| **The Miner** | Viral tweetleri + akademik analizleri toplar | Global/ham |
| **The Lab** | Batch API ile stratejik kategorilere ayırır | Zenginleştirilmiş |
| **The Mirror** | Kullanıcının geçmişini analiz eder, stil hafızası kurar | Kişisel/izole |
| **The Creator** | Diğer 3 skill'den rapor alır, nihai öneriyi üretir | Hibrit |

**Sınıflandırma etiketleri:**
- Psikolojik Tetikleyici: Öfke, FOMO, Merak, Mizah
- İçerik Formu: Liste, Thread, Soru, Karşıt Görüş
- Ton: Alaycı, Profesyonel, Samimi

**Maliyet kararı:**
Batch API kullanımı (%50 indirim) — GPT-4o-mini ~$7.5-10 / 1M tweet, Gemini Flash ~$3-6 / 1M tweet

**Kullanıcı stil hafızası:**
İzole path: `/users/{userId}/style_memory` — kullanıcı başına en iyi 50 tweet analizi

**Neden bu mimari:**
- Ölçeklenebilir: Her skill bağımsız güncellenebilir
- Hassas: Global trend + kişisel DNA filtresi = "yapay durmayan" içerik
- Maliyet etkin: Batch API + hafif modeller

**Sonraki adım:** Pipeline orchestration tasarla, The Mirror için @ciftcibahadir stil hafızasını kur.

**Durum:** Tamamlandı — 4 SKILL.md oluşturuldu (paralel agent)

**Sonuç:**
- `skills/the-miner/SKILL.md` — 620 satır, X API v2 endpoint'leri, niş hedef hesaplar, priority score formülü, arXiv + Kaggle entegrasyonu
- `skills/the-lab/SKILL.md` — Batch API prompt şablonu (JSONL formatı), 6 boyutlu sınıflandırma, S/A/B/C tier kalite sistemi, niş boşluk analizi
- `skills/the-mirror/SKILL.md` — 785 satır, kullanıcı DNA şeması (8 bölüm), global trend filtresi, The Creator için DNA raporu formatı, @ciftcibahadir ön doldurulmuş başlangıç değerleri
- `skills/the-creator/SKILL.md` — 5 üretim modu, X algoritma optimizasyon kuralları, anti-pattern listesi, tam sistem promptu, uçtan uca pipeline örneği

---

## [2026-03-17] — Proje Strateji Belgesi Oluşturuldu

**Karar:** Projenin hibrit mimarisi, iş modeli ve açık noktaları `strateji.md` formatında kayıt altına alındı.

**Bağlam:**
Projenin büyüme süreci ile birlikte stratejik kararların tek bir dokümanda toplanması ihtiyacı doğdu. Miner/Lab (kapalı devre) ile Mirror/Creator (açık kaynak) arasındaki yapı netleştirildi ve yazıya geçirildi.

**Belgelenen kararlar:**
- Hibrit model (Kapalı Devre Fabrika + Açık Kaynak Ajanlar) kesinleşti
- Miner ve Lab kodları asla paylaşılmayacak — bu "moat" olarak korunacak
- Ana gelir modeli: Miner API üzerinden SaaS abonelik
- Open source katman: Mirror + Creator (kendi veri kaynağıyla ücretsiz çalışır)

**Açık kalan ve takip gerektiren 3 kritik nokta:**
1. Creator → Miner API yetkilendirme yöntemi (OAuth2 / API Key)
2. Ücretli API veri paketlerinin sınırları (günlük kota, tier yapısı)
3. Mirror verisinin saklama yeri (yerel vs. merkezi vs. hibrit şifreli)

**Durum:** Tamamlandı — `strateji.md` oluşturuldu

---

## [2026-03-17] — Phase 1: twikit Migration ve Async Pattern Kararları

**Bağlam:**
mirror_sync.py'nin tweepy'den twikit 2.3.3'e geçişi sırasında alınan yedi implementasyon kararı. Phase 1 planları 01-01 ile 01-04 arasında uygulandı. Kaynak: 01-04-SUMMARY.md ve STATE.md.

**Kararlar:**
1. **tweepy → twikit 2.3.3 migrasyonu:** tweepy Free tier `impression_count` null döndürüyor — tüm engagement hesaplamalarını bozuyor. twikit cookie tabanlı auth ile `view_count` dolu döndürüyor.
2. **twikit Client singleton:** Modül seviyesinde tek istemci. Testler `ms.client`'i doğrudan patch eder; her auth çağrısında yeniden başlatma yok.
3. **view_count denominator:** `impression_count` yerine `view_count` kullanılıyor — twikit breaking change; tüm engagement rate hesaplamalarına yansıtıldı.
4. **Atomic write:** same-dir tempfile (`dir=target_dir`) + `os.replace` — Windows'ta cross-device rename riski ortadan kalkar; tempfile ve hedef aynı sürücüde kalır.
5. **asyncio.run(main()):** `get_event_loop().run_until_complete()` yerine — Python 3.10+ Windows ProactorEventLoop lifecycle doğru yönetiliyor.
6. **Cutoff precedence:** `--since` flag > `last_synced_at` > None (ilk çalıştırma). Kullanıcı `style_memory.json` düzenlemeden geçmişe dönebilir.
7. **evolution_log guard:** `not dry_run AND new_tweets non-empty` koşulu — sıfır sonuçlu sync çalıştırmalarında boş log girişi oluşturulmuyor.

**Durum:** Tamamlandı — Phase 1 (01-01 ile 01-04)

**Sonuç:**
- `skills/the-mirror/mirror_sync.py` twikit 2.3.3 üzerinde çalışıyor
- 13 test GREEN; `--dry-run` @ciftcibahadir'e karşı doğrulandı (view_count > 0, bookmark_count dolu)
- `style_memory.json` atomic write ile crash-safe

---
