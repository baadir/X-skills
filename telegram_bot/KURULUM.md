# TwitterYoldas Telegram Bot — Kurulum

## 1. Telegram Bot Token Al

1. Telegram'da **@BotFather** aç
2. `/newbot` yaz
3. İsim ver: `TwitterYoldas`
4. Username ver: `twitteryoldas_bot` (veya istediğin)
5. Sana verilen token'ı `.env` içindeki `TELEGRAM_BOT_TOKEN` alanına yaz

## 2. Kullanıcı ID'ni Öğren

1. Telegram'da **@userinfobot** aç, `/start` at
2. Sana verilen sayısal ID'yi `.env` içindeki `ALLOWED_USER_ID` alanına yaz
   (Sadece senin kullanımın için güvenlik)

## 3. API Key'leri .env'e Ekle

```
TELEGRAM_BOT_TOKEN=1234567890:AAF...
ALLOWED_USER_ID=123456789
ANTHROPIC_API_KEY=sk-ant-...  # D:/LLM/Twitter Skill/.env'den al
```

## 4. Bağımlılıkları Yükle

```bash
cd "D:/LLM/Twitter Skill/telegram_bot"
pip install -r requirements.txt
```

## 5. Botu Başlat

```bash
cd "D:/LLM/Twitter Skill/telegram_bot"
python bot.py
```

Çıktı:
```
🚀 TwitterYoldas Telegram Bot başlatılıyor...
📁 Queue dosyası: D:/LLM/Twitter Skill/tweet_queue.json
✅ Bot hazır. Telegram'dan mesaj gönderebilirsin.
```

## 6. Kullanım Akışı

### Telegram'dan Tweet Üret:
```
Sen:  /brainstorm MCP server yazdım, bunu tweet'e dönüştür
Bot:  ⏳ İçerik üretiliyor...
Bot:  [3 versiyon — A, B, C]
Bot:  👆 Bu içeriği queue'ya ekleyeyim mi?
      [✅ Kuyruğa Ekle] [✏️ Düzenle] [❌ İptal]
Sen:  ✅ Kuyruğa Ekle
Bot:  ✅ Kuyruğa eklendi! ID: a1b2c3d4
      Claude Code'da /twitter:post ile yayınlayabilirsin.
```

### Claude Code'da Yayınla:
```
/twitter:post        → Queue'yu listeler
/twitter:post all    → Tümünü Xquik ile atar
/twitter:post a1b2c3d4 → Sadece o tweeti atar
```

## 7. Windows Başlangıcında Otomatik Başlat (opsiyonel)

1. `Win + R` → `shell:startup`
2. Oraya bir `.bat` dosyası oluştur:
```bat
@echo off
cd /d "D:\LLM\Twitter Skill\telegram_bot"
python bot.py
```

## Komut Listesi

| Komut | Açıklama |
|-------|----------|
| `/brainstorm <fikir>` | 3 farklı tweet versiyonu |
| `/thread <konu>` | Tam thread (kanca + 4-8 tweet) |
| `/analiz <tweet>` | Mevcut tweeti iyileştir |
| `/öneri` | Haftalık içerik planı |
| `/queue` | Queue'daki bekleyen tweetleri listele |
| `/temizle` | Konuşma geçmişini sıfırla |
| Serbest mesaj | Mod otomatik seçilir |
