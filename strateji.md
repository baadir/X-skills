# Strateji Belgesi — Multi-Skill Agent Ekosistemi

**Versiyon:** 1.0
**Tarih:** 2026-03-17
**Durum:** Aktif

---

## Özet

Bu belge, Multi-Skill Agent Ekosistemi'nin stratejik mimarisini, iş modelini ve teknik prensiplerini tanımlar.

Sistem iki katmana ayrılmıştır:
- **Kapalı Devre (Miner + Lab):** Ticari sır. Kodları paylaşılmaz.
- **Açık Kaynak (Mirror + Creator):** Toplulukla paylaşılan kullanıcı katmanı.

---

## 1. Stratejik Mimari: Hibrit Model

### A. Kapalı Devre — Üretim Fabrikası

Sistemin "mutfağı" ve ticari sırrı. Bu katmanın kodu **asla paylaşılmaz.**

| Bileşen | Rol | Görev |
|---------|-----|-------|
| **Miner** | Veri Madencisi | Global trendleri, yüksek etkileşimli tweetleri ve algoritmik sinyalleri toplar. Ham veriyi fabrikaya sokar. |
| **Lab** | Veri İşleme Merkezi | Miner'dan gelen ham veriyi temizler, kategorize eder ve Creator'ın anlayacağı etiketli veri setlerine (Altın Veri) dönüştürür. |

**Analoji:** Miner hammaddeyi getirir, Lab hammaddeyi işler.

---

### B. Açık Kaynak — Kullanıcı Katmanı

Topluluğa sunulan, uygulamanın kullanıcıyla temas eden yüzü.

| Bileşen | Rol | Görev |
|---------|-----|-------|
| **Mirror** | Kişisel Hafıza | Kullanıcının kendi tweet geçmişini analiz eder. Ücretsiz scraping API'larıyla çalışır. |
| **Creator** | İçerik Mimarı | Fabrikadan gelen trend verisi ile Mirror'dan gelen kişisel veriyi sentezleyerek içerik üretir. |

---

## 2. Skill Detayları ve Sorumluluklar

| Skill | Statü | Görev | Veri Kaynağı |
|-------|-------|-------|--------------|
| **Miner** | 🔒 Kapalı | Veri toplama ve zenginleştirme | HuggingFace, Akademik Veri, Canlı Akış |
| **Lab** | 🔒 Kapalı | Sınıflandırma ve etiketleme | İç Algoritmalar / AI Modelleri |
| **Mirror** | 🌐 Açık | Kullanıcı ses tonu analizi | Kullanıcının kendi tweetleri |
| **Creator** | 🌐 Açık | Final içerik üretimi | Miner API + Mirror Verisi |

---

## 3. Veri Akış Hattı (The Pipeline)

```
[Global Kaynaklar]
HuggingFace / Akademik Veri / Canlı Akış
        ↓
   [ MINER ]  ← Kapalı Devre
   Ham veri toplama
        ↓
   [ LAB ]    ← Kapalı Devre
   Temizleme + Etiketleme → Altın Veri
        ↓
   [ Miner API ] ← SaaS Abonelik Kapısı
        ↓               ↓
  [ MIRROR ]      [ CREATOR ]  ← Açık Kaynak
  Kullanıcı DNA   İçerik üretimi
        ↓               ↓
         → Final İçerik ←
```

### Fabrika Otomasyon Kuralları

- **Sürekli Güncelleme:** Miner, günde en az bir kez global veri setini tazeler.
- **Format Standartizasyonu:** Tüm kaynaklardan gelen veri, Lab tarafından tek bir şemaya (schema) oturtulur.
- **API Sunumu:** İşlenen veriler, API anahtarları aracılığıyla yalnızca yetkili Creator ajanlarına sunulur.

---

## 4. İş Modeli ve Ürünleştirme

### Ana Ürün: Miner API (SaaS)

Kullanıcılar, kaliteli ve güncel veri setine erişmek için abonelik sistemine dahil olurlar.

```
Ücretsiz Katman → Mirror + Creator (kendi veri kaynağıyla)
Ücretli Katman  → Mirror + Creator + Miner API (Altın Veri akışı)
```

### Açık Kaynak Değeri

- Uygulama motoru açık kaynak olduğu için topluluk tarafından geliştirilebilir.
- Ancak en iyi performans, ücretli Altın Veri seti ile elde edilir.
- Bu, organik bir "freemium moat" oluşturur.

### İleri Kullanıcı Esnekliği

Kendi veri setini oluşturmak isteyen ileri seviye kullanıcılar, Mirror ve Creator kodlarını kullanarak kendi Miner muadillerini yazabilirler. Ancak:
- Hazır veri **daha hızlı** başlangıç sağlar.
- Hazır veri **daha kaliteli** çünkü Lab'ın algoritmik etiketlemesinden geçiyor.
- Bu hız ve kalite farkı, ücretli planın asıl satış noktasıdır.

---

## 5. Çözülen Çelişkiler

| # | Çelişki | Karar |
|---|---------|-------|
| 1 | **Miner vs. Lab sınırı** | Miner "hammaddeyi getiren", Lab "hammaddeyi işleyen makine." Net ayrım. |
| 2 | **Kod paylaşımı** | Miner ve Lab kodları kesinlikle paylaşılmaz. Bu, sistemi kopyalamayı zorlaştıran bir "moat" oluşturur. |
| 3 | **İsimlendirme** | Tüm dokümanda "Miner" ismi standart olarak kullanılır. |

---

## 6. Aksiyon Bekleyen Kritik Noktalar

> Bu başlık, kararı verilmemiş açık konuları takip eder. Karar alındıkça `decision.md`'ye taşınır.

### 6.1 API Yetkilendirme
**Durum:** ⏳ Bekliyor
**Soru:** Creator ajanı, Miner API'sine nasıl güvenli bağlanacak?
**Seçenekler:** OAuth2, API Key, JWT
**Öneri:** API Key ile başla (basit), ölçeklendikçe OAuth2'ye geç.

### 6.2 Veri Sınırları
**Durum:** ⏳ Bekliyor
**Soru:** Ücretli API üzerinden dönen veri miktarı ne olacak?
**Örnek kararlar gerekli:**
- Günlük kaç trend formatı paylaşılacak?
- Veri paketleri nasıl kırılacak (Basic / Pro / Enterprise)?
- Rate limiting stratejisi ne olacak?

### 6.3 Mirror Veri Saklama Yeri
**Durum:** ✅ Karar verildi — 2026-03-17
**Soru:** Kullanıcının Mirror verisi yerelde mi tutulacak, yoksa merkezi veritabanına mı yedeklenecek?
**Seçenekler:**

| Seçenek | Avantaj | Dezavantaj |
|---------|---------|------------|
| **Yerel saklama** | Gizlilik ✅, Open source topluluğu için cazip ✅ | Cihaz değişiminde veri kaybı ❌ |
| **Merkezi yedek** | Çoklu cihaz desteği ✅, Yedekleme ✅ | Gizlilik kaygısı ❌, Ekstra altyapı ❌ |
| **Hibrit (Şifreli senkron)** | İkisinin avantajı ✅ | Karmaşık uygulama ❌ |

**Karar:** Phase 1'de **yerel saklama** seçildi.

- `style_memory.json` kullanıcı makinesinde yerel olarak tutulur
- Gizlilik avantajı: open-source kullanıcılar için cazip (merkezi sunucuya veri gitmez)
- Cihaz değişimi riski kabul edildi: v1 kapsam dışı
- Opsiyonel şifreli bulut yedek v2'de değerlendirilecek

**Uygulama:** `skills/the-mirror/mirror_sync.py` — atomic write ile yerel `style_memory.json`

**Tavsiye:** Open source versiyonu yerelde tut. Ücretli plan için opsiyonel şifreli bulut yedek ekle.

---

## 7. Versiyon Geçmişi

| Versiyon | Tarih | Değişiklik |
|----------|-------|------------|
| 1.0 | 2026-03-17 | İlk strateji belgesi oluşturuldu. Hibrit mimari, iş modeli ve açık noktalar tanımlandı. |
| 1.1 | 2026-03-17 | 6.3 Mirror Veri Saklama kararı kapatıldı: yerel saklama seçildi (Phase 1). |

---

*Bu belge yaşayan bir dokümandır. Yeni kararlar alındıkça güncellenir ve `decision.md` ile paralel takip edilir.*
