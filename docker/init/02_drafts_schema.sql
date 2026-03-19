-- ============================================================
-- TwitterYoldas — Taslak + Yayın + Performans Şeması
-- Versiyon: 1.0
-- ============================================================

-- ============================================================
-- THREAD DRAFTS — Creator çıktılarını saklar
-- status: 'öneri'=üretildi/taslak | 'atılmış'=X'e gönderildi | 'arşiv'=kullanılmadı
-- ============================================================
CREATE TABLE IF NOT EXISTS thread_drafts (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Benzersiz anahtar: thread'i tanımlar (duplicate önleme)
    draft_key       VARCHAR(200) NOT NULL UNIQUE,
    -- Format: slugified_title__YYYY-MM-DD (örn: "ai-startup-factory-bulgu-1__2026-03-18")

    thread_title    TEXT         NOT NULL,
    generated_at    TIMESTAMPTZ  NOT NULL,
    author_name     VARCHAR(200),
    author_handle   VARCHAR(100),

    -- Tam JSON içerik
    tweets_json     JSONB        NOT NULL,   -- tweets[] dizisinin tamamı
    analysis_json   JSONB,                   -- analysis nesnesi

    -- Durum: 'öneri' | 'atılmış' | 'arşiv'
    status          VARCHAR(20)  NOT NULL DEFAULT 'öneri'
                    CHECK (status IN ('öneri', 'atılmış', 'arşiv')),

    -- Atıldığında doldurulur
    posted_at           TIMESTAMPTZ,
    tweet_url           TEXT,                -- Kullanıcının girdiği tam URL
    first_tweet_id      VARCHAR(30),         -- URL'den ayrıştırılan tweet ID'si

    -- İsteğe bağlı notlar
    notes           TEXT,

    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_thread_drafts_status     ON thread_drafts(status);
CREATE INDEX IF NOT EXISTS idx_thread_drafts_posted_at  ON thread_drafts(posted_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_thread_drafts_created_at ON thread_drafts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_thread_drafts_tweet_id   ON thread_drafts(first_tweet_id);

-- updated_at otomatik güncelleme trigger'ı
CREATE TRIGGER thread_drafts_updated_at
    BEFORE UPDATE ON thread_drafts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- PERFORMANCE SNAPSHOTS — İlk 3 gün metrik anlık görüntüleri
-- ============================================================
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_id        UUID         NOT NULL REFERENCES thread_drafts(id) ON DELETE CASCADE,
    first_tweet_id  VARCHAR(30)  NOT NULL,

    -- 0=atış anı | 1=1.gün | 2=2.gün | 3=3.gün
    day_number      SMALLINT     NOT NULL CHECK (day_number BETWEEN 0 AND 3),

    -- X API public_metrics
    likes           INTEGER      DEFAULT 0,
    retweets        INTEGER      DEFAULT 0,
    replies         INTEGER      DEFAULT 0,
    quotes          INTEGER      DEFAULT 0,
    bookmarks       INTEGER      DEFAULT 0,
    impressions     INTEGER      DEFAULT 0,

    -- Hesaplanmış: (likes+rt+reply+quote+bookmark) / max(impressions,1)
    engagement_rate FLOAT,

    -- Kaynak: 'twikit' | 'x_api' | 'manual'
    source          VARCHAR(20)  DEFAULT 'twikit',

    fetched_at      TIMESTAMPTZ  DEFAULT NOW(),

    UNIQUE (draft_id, day_number)
);

CREATE INDEX IF NOT EXISTS idx_perf_snapshots_draft_id  ON performance_snapshots(draft_id);
CREATE INDEX IF NOT EXISTS idx_perf_snapshots_tweet_id  ON performance_snapshots(first_tweet_id);


-- ============================================================
-- VIEW — Draft + son performans birleştirmesi
-- ============================================================
CREATE OR REPLACE VIEW v_drafts_with_performance AS
SELECT
    d.id,
    d.draft_key,
    d.thread_title,
    d.generated_at,
    d.author_handle,
    d.status,
    d.posted_at,
    d.tweet_url,
    d.first_tweet_id,
    d.created_at,
    d.notes,
    -- Son snapshot
    ps.day_number    AS latest_day,
    ps.likes,
    ps.retweets,
    ps.replies,
    ps.quotes,
    ps.bookmarks,
    ps.impressions,
    ps.engagement_rate,
    ps.fetched_at    AS last_fetched_at,
    -- Toplam snapshot sayısı
    (SELECT COUNT(*) FROM performance_snapshots p2 WHERE p2.draft_id = d.id) AS snapshot_count
FROM thread_drafts d
LEFT JOIN LATERAL (
    SELECT * FROM performance_snapshots
    WHERE draft_id = d.id
    ORDER BY day_number DESC
    LIMIT 1
) ps ON true
ORDER BY d.created_at DESC;
