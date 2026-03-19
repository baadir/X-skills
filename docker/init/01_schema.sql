-- ============================================================
-- TwitterYoldas — PostgreSQL + pgvector Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TAG CATALOG
-- 11 kategoride 55 etiket. Ingestion'da referans tablo.
-- ============================================================
CREATE TABLE tag_catalog (
    id          SERIAL PRIMARY KEY,
    category    VARCHAR(50)  NOT NULL,
    tag_key     VARCHAR(100) NOT NULL UNIQUE,
    display_tr  VARCHAR(100),
    display_en  VARCHAR(100),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

INSERT INTO tag_catalog (category, tag_key, display_tr, display_en) VALUES
-- 1. İçerik Formu (7)
('icerik_formu',    'thread',           'Thread',           'Thread'),
('icerik_formu',    'liste',            'Liste',            'List'),
('icerik_formu',    'soru',             'Soru',             'Question'),
('icerik_formu',    'karşıt_görüş',     'Karşıt Görüş',     'Contrarian'),
('icerik_formu',    'hikaye',           'Hikaye',           'Story'),
('icerik_formu',    'veri_paylaşımı',   'Veri Paylaşımı',   'Data Share'),
('icerik_formu',    'deneyim',          'Deneyim',          'Experience'),
-- 2. Kanca Tipi (8)
('kanca_tipi',      'soru',             'Soru',             'Question'),
('kanca_tipi',      'provokasyon',      'Provokasyon',      'Provocation'),
('kanca_tipi',      'rakam_ile_bas',    'Rakamla Başla',    'Lead with Number'),
('kanca_tipi',      'karsi_gorus',      'Karşı Görüş',      'Counter-view'),
('kanca_tipi',      'hikaye',           'Hikaye',           'Story'),
('kanca_tipi',      'liste_vaadi',      'Liste Vaadi',      'List Promise'),
('kanca_tipi',      'cesur_iddia',      'Cesur İddia',      'Bold Claim'),
('kanca_tipi',      'diger',            'Diğer',            'Other'),
-- 3. Ton (5)
('ton',             'alaycı',           'Alaycı',           'Sarcastic'),
('ton',             'heyecanli',        'Heyecanlı',        'Enthusiastic'),
('ton',             'egitici',          'Eğitici',          'Educational'),
('ton',             'samimi',           'Samimi',           'Intimate'),
('ton',             'profesyonel',      'Profesyonel',      'Professional'),
-- 4. Psikolojik Tetikleyici (7)
('psikolojik',      'öfke',             'Öfke',             'Anger'),
('psikolojik',      'fomo',             'FOMO',             'FOMO'),
('psikolojik',      'merak',            'Merak',            'Curiosity'),
('psikolojik',      'mizah',            'Mizah',            'Humor'),
('psikolojik',      'empati',           'Empati',           'Empathy'),
('psikolojik',      'şok',              'Şok',              'Shock'),
('psikolojik',      'gurur',            'Gurur',            'Pride'),
-- 5. Görsel Format (4)
('gorsel_format',   'video',            'Video',            'Video'),
('gorsel_format',   'görsel',           'Görsel',           'Image'),
('gorsel_format',   'gif',              'GIF',              'GIF'),
('gorsel_format',   'yok',              'Yok',              'None'),
-- 6. Algoritma Sinyali (7)
('algo_sinyal',     'like_odaklı',      'Like Odaklı',      'Like-driven'),
('algo_sinyal',     'retweet_odaklı',   'RT Odaklı',        'RT-driven'),
('algo_sinyal',     'reply_odaklı',     'Yanıt Odaklı',     'Reply-driven'),
('algo_sinyal',     'bookmark_odaklı',  'Bookmark Odaklı',  'Bookmark-driven'),
('algo_sinyal',     'dwell_odaklı',     'Dwell Odaklı',     'Dwell-driven'),
('algo_sinyal',     'dm_share_odaklı',  'DM Odaklı',        'DM-driven'),
('algo_sinyal',     'follow_odaklı',    'Takip Odaklı',     'Follow-driven'),
-- 7. Kalite Tier (4)
('kalite',          's_tier',           'S Tier (9-10)',     'S Tier (9-10)'),
('kalite',          'a_tier',           'A Tier (7-8)',      'A Tier (7-8)'),
('kalite',          'b_tier',           'B Tier (4-6)',      'B Tier (4-6)'),
('kalite',          'c_tier',           'C Tier (1-3)',      'C Tier (1-3)'),
-- 8. Dil (2)
('dil',             'en',               'İngilizce',         'English'),
('dil',             'tr',               'Türkçe',            'Turkish'),
-- 9. Kaynak (3)
('kaynak',          'x_api',            'X API',             'X API'),
('kaynak',          'arxiv',            'arXiv',             'arXiv'),
('kaynak',          'kaggle',           'Kaggle',            'Kaggle'),
-- 10. Thread Rolü (4)
('thread_rol',      'hook_tweet',       'Hook Tweet',        'Hook Tweet'),
('thread_rol',      'body_tweet',       'Body Tweet',        'Body Tweet'),
('thread_rol',      'close_tweet',      'Kapanış Tweet',     'Close Tweet'),
('thread_rol',      'tek_tweet',        'Tek Tweet',         'Single Tweet'),
-- 11. Viral Seviye (4)
('viral_seviye',    'viral',            'Viral (≥12)',        'Viral (≥12)'),
('viral_seviye',    'high',             'Yüksek (8-12)',      'High (8-12)'),
('viral_seviye',    'medium',           'Orta (4-8)',         'Medium (4-8)'),
('viral_seviye',    'low',              'Düşük (<4)',         'Low (<4)');

-- ============================================================
-- MINER SESSIONS
-- ============================================================
CREATE TABLE miner_sessions (
    id                    UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id            VARCHAR(50)  NOT NULL UNIQUE,  -- "session_20250317_001"
    collected_at          TIMESTAMPTZ,
    target_user           VARCHAR(100),
    niche                 VARCHAR(100),
    mode                  VARCHAR(20),                   -- quick | deep | account_analysis
    tweet_count_raw       INTEGER      DEFAULT 0,
    tweet_count_filtered  INTEGER      DEFAULT 0,
    paper_count           INTEGER      DEFAULT 0,
    dataset_count         INTEGER      DEFAULT 0,
    api_calls_made        INTEGER      DEFAULT 0,
    filter_pass_rate      FLOAT,
    avg_engagement_rate   FLOAT,
    errors                JSONB        DEFAULT '[]',
    warnings              JSONB        DEFAULT '[]',
    raw_json              JSONB,                         -- orijinal session JSON yedek
    created_at            TIMESTAMPTZ  DEFAULT NOW()
);

-- ============================================================
-- TWEETS — Ana tablo
-- ============================================================
CREATE TABLE tweets (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tweet_id                VARCHAR(30) NOT NULL UNIQUE,
    session_id              VARCHAR(50) REFERENCES miner_sessions(session_id) ON DELETE SET NULL,

    -- İçerik
    text                    TEXT        NOT NULL,
    language                VARCHAR(5),                  -- en | tr
    hook_text               TEXT,                        -- Lab tarafından doldurulur

    -- Yazar
    username                VARCHAR(100),
    display_name            VARCHAR(200),
    author_followers        INTEGER,
    author_verified         BOOLEAN     DEFAULT FALSE,

    -- Zamanlama
    created_at              TIMESTAMPTZ,
    collected_at            TIMESTAMPTZ,

    -- Etkileşim metrikleri
    likes                   INTEGER     DEFAULT 0,
    retweets                INTEGER     DEFAULT 0,
    replies                 INTEGER     DEFAULT 0,
    quotes                  INTEGER     DEFAULT 0,
    bookmarks               INTEGER     DEFAULT 0,
    impressions             INTEGER     DEFAULT 0,

    -- Hesaplanmış oranlar
    engagement_rate         FLOAT,
    bookmark_rate           FLOAT,
    reply_to_like_ratio     FLOAT,
    priority_score          FLOAT,
    priority                VARCHAR(10),                 -- high | normal

    -- Medya
    has_media               BOOLEAN     DEFAULT FALSE,
    media_type              VARCHAR(20),                 -- video | görsel | gif | yok
    media_count             INTEGER     DEFAULT 0,

    -- Thread
    is_thread               BOOLEAN     DEFAULT FALSE,
    thread_position         INTEGER     DEFAULT 1,
    thread_length           INTEGER     DEFAULT 1,
    thread_tweet_ids        TEXT[],                      -- tüm kardeş tweet ID'leri
    thread_complete         BOOLEAN     DEFAULT FALSE,   -- tüm kardeşler DB'de mi?

    -- Link
    has_link                BOOLEAN     DEFAULT FALSE,
    link_domain             VARCHAR(200),

    -- Hashtag/Mention
    hashtags                TEXT[],
    hashtag_count           INTEGER     DEFAULT 0,
    mention_count           INTEGER     DEFAULT 0,

    -- Koleksiyon metadata
    source                  VARCHAR(20) DEFAULT 'x_api',
    query_used              TEXT,

    -- Türetilmiş tag'ler (ingestion'da hesaplanır)
    thread_role             VARCHAR(20),                 -- hook_tweet | body_tweet | close_tweet | tek_tweet
    viral_level             VARCHAR(10),                 -- viral | high | medium | low

    -- Vektör embedding (OpenAI text-embedding-3-small, 1536 boyut)
    embedding               vector(1536),

    -- Full-text search (embedding gerektirmez — agent SQL sorgusu için)
    search_vector           tsvector,

    -- İşlem durumu
    lab_processed           BOOLEAN     DEFAULT FALSE,
    embedding_generated     BOOLEAN     DEFAULT FALSE,

    created_at_db           TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TWEET LABELS — Lab sınıflandırması (1-to-1 tweets ile)
-- ============================================================
CREATE TABLE tweet_labels (
    id                        UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tweet_id                  VARCHAR(30) NOT NULL UNIQUE REFERENCES tweets(tweet_id) ON DELETE CASCADE,

    -- 6 Lab Boyutu
    psikolojik_tetikleyici    TEXT[],                    -- ['merak', 'fomo'] — çoklu seçim
    primary_trigger           VARCHAR(50),               -- baskın tetikleyici
    icerik_formu              VARCHAR(50),               -- tek seçim
    ton                       VARCHAR(50),               -- tek seçim
    kanca_tipi                VARCHAR(50),               -- tek seçim
    gorsel_format             VARCHAR(20),               -- tek seçim
    algoritma_sinyal          TEXT[],                    -- sıralı: ['bookmark_odaklı', 'reply_odaklı']

    -- Kalite
    quality_score             INTEGER     CHECK (quality_score BETWEEN 1 AND 10),
    quality_tier              CHAR(1),                   -- S | A | B | C

    -- Lab metadata
    hook_text                 TEXT,                      -- açılış cümlesi
    reasoning                 TEXT,                      -- 1-2 cümle açıklama
    processed_at              TIMESTAMPTZ,
    model_used                VARCHAR(100),
    lab_session_id            VARCHAR(50),

    created_at                TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ARXIV PAPERS
-- ============================================================
CREATE TABLE arxiv_papers (
    id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id        VARCHAR(50) REFERENCES miner_sessions(session_id) ON DELETE SET NULL,
    arxiv_id          VARCHAR(30) NOT NULL UNIQUE,
    title             TEXT,
    abstract_snippet  TEXT,
    authors           TEXT[],
    submitted_date    DATE,
    pdf_url           TEXT,
    relevance_score   FLOAT,
    primary_category  VARCHAR(50),
    embedding         vector(384),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- KAGGLE DATASETS
-- ============================================================
CREATE TABLE kaggle_datasets (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          VARCHAR(50) REFERENCES miner_sessions(session_id) ON DELETE SET NULL,
    dataset_id          VARCHAR(200) NOT NULL UNIQUE,
    title               TEXT,
    url                 TEXT,
    usability_rating    FLOAT,
    total_votes         INTEGER,
    last_updated        DATE,
    file_formats        TEXT[],
    row_count_estimate  INTEGER,
    relevant_columns    TEXT[],
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- pgvector similarity search (IVFFlat — 100K tweet için yeterli)
-- NOT: lists = 1 ile başla, 10K+ tweet sonrası DROP INDEX + REINDEX WITH (lists=100)
CREATE INDEX tweets_embedding_idx
    ON tweets USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1);
CREATE INDEX arxiv_embedding_idx
    ON arxiv_papers USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1);

-- Full-text search — embedding gerektirmez (GIN index)
CREATE INDEX tweets_fts_idx ON tweets USING GIN(search_vector);

-- Standart filtre index'leri
CREATE INDEX ON tweets(session_id);
CREATE INDEX ON tweets(engagement_rate DESC);
CREATE INDEX ON tweets(priority_score DESC);
CREATE INDEX ON tweets(created_at DESC);
CREATE INDEX ON tweets(language);
CREATE INDEX ON tweets(lab_processed);
CREATE INDEX ON tweets(is_thread);
CREATE INDEX ON tweets(thread_complete);
CREATE INDEX ON tweets(viral_level);
CREATE INDEX ON tweets(thread_role);
CREATE INDEX ON tweets USING GIN(hashtags);
CREATE INDEX ON tweets USING GIN(thread_tweet_ids);

-- tweet_labels index'leri
CREATE INDEX ON tweet_labels(quality_score DESC);
CREATE INDEX ON tweet_labels(quality_tier);
CREATE INDEX ON tweet_labels(icerik_formu);
CREATE INDEX ON tweet_labels(ton);
CREATE INDEX ON tweet_labels(kanca_tipi);
CREATE INDEX ON tweet_labels USING GIN(psikolojik_tetikleyici);
CREATE INDEX ON tweet_labels USING GIN(algoritma_sinyal);

-- ============================================================
-- VIEWS — Sık kullanılan sorgular
-- ============================================================

-- Tam tweet + label join
CREATE VIEW v_tweets_labeled AS
SELECT
    t.*,
    tl.psikolojik_tetikleyici,
    tl.primary_trigger,
    tl.icerik_formu,
    tl.ton,
    tl.kanca_tipi,
    tl.gorsel_format,
    tl.algoritma_sinyal,
    tl.quality_score,
    tl.quality_tier,
    tl.hook_text       AS lab_hook_text,
    tl.reasoning
FROM tweets t
LEFT JOIN tweet_labels tl ON t.tweet_id = tl.tweet_id;

-- S+A tier tweet'ler (Creator için referans havuzu)
CREATE VIEW v_high_quality_tweets AS
SELECT * FROM v_tweets_labeled
WHERE quality_tier IN ('S', 'A')
ORDER BY quality_score DESC, priority_score DESC;

-- Tamamlanmamış thread'ler (ingestion monitoring)
CREATE VIEW v_incomplete_threads AS
SELECT DISTINCT
    tweet_id,
    thread_tweet_ids,
    thread_length,
    (SELECT COUNT(*) FROM tweets t2 WHERE t2.tweet_id = ANY(t.thread_tweet_ids)) AS found_count
FROM tweets t
WHERE is_thread = TRUE AND thread_complete = FALSE;

-- ============================================================
-- updated_at otomatik güncelleme
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tweets_updated_at
    BEFORE UPDATE ON tweets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- search_vector otomatik güncelleme (embedding gerektirmez)
-- ============================================================
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.hook_text, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.text, '')), 'B') ||
        setweight(to_tsvector('simple',  coalesce(NEW.username, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tweets_search_vector
    BEFORE INSERT OR UPDATE OF text, hook_text, username ON tweets
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();
