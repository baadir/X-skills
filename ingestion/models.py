"""
Pydantic v2 şemaları — Miner JSON çıktısının tip-güvenli validasyonu.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Tweet
# ─────────────────────────────────────────────

class TweetRecord(BaseModel):
    tweet_id:               str
    text:                   str
    username:               Optional[str] = None
    display_name:           Optional[str] = None
    author_followers:       Optional[int] = None
    author_verified:        bool = False
    created_at:             Optional[datetime] = None
    collected_at:           Optional[datetime] = None

    likes:                  int = 0
    retweets:               int = 0
    replies:                int = 0
    quotes:                 int = 0
    bookmarks:              int = 0
    impressions:            int = 0

    engagement_rate:        Optional[float] = None
    bookmark_rate:          Optional[float] = None
    reply_to_like_ratio:    Optional[float] = None
    priority_score:         Optional[float] = None
    priority:               Optional[str] = None

    has_media:              bool = False
    media_type:             Optional[str] = None
    media_count:            int = 0

    is_thread:              bool = False
    thread_position:        int = 1
    thread_length:          int = 1
    thread_tweet_ids:       List[str] = Field(default_factory=list)

    has_link:               bool = False
    link_domain:            Optional[str] = None

    language:               Optional[str] = None
    hashtag_count:          int = 0
    hashtags:               List[str] = Field(default_factory=list)
    mention_count:          int = 0

    source:                 str = "x_api"
    query_used:             Optional[str] = None
    collection_session_id:  Optional[str] = None

    tweet_url:              Optional[str] = None
    virality_punch:         float = 0.0

    @field_validator("tweet_id")
    @classmethod
    def tweet_id_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tweet_id boş olamaz")
        return v.strip()

    @model_validator(mode="after")
    def compute_derived_fields(self) -> TweetRecord:
        """Eksik hesaplamaları tamamla."""
        # engagement_rate
        if self.engagement_rate is None and self.impressions and self.impressions > 0:
            total = self.likes + self.retweets + self.replies + self.quotes
            self.engagement_rate = round(total / self.impressions, 6)

        # bookmark_rate
        if self.bookmark_rate is None and self.impressions and self.impressions > 0:
            self.bookmark_rate = round(self.bookmarks / self.impressions, 6)

        # reply_to_like_ratio
        if self.reply_to_like_ratio is None and self.likes and self.likes > 0:
            self.reply_to_like_ratio = round(self.replies / self.likes, 6)

        # tweet_url
        if not self.tweet_url and self.username and self.tweet_id:
            self.tweet_url = f"https://x.com/{self.username}/status/{self.tweet_id}"

        # virality_punch: takipçi başına like oranı (%)
        if self.virality_punch == 0.0 and self.likes > 0:
            followers = max(self.author_followers or 0, 100)
            self.virality_punch = round((self.likes / followers) * 100, 4)

        # priority_score
        if self.priority_score is None and self.impressions and self.impressions > 0:
            raw = (
                self.likes * 1.0
                + self.retweets * 2.5
                + self.replies * 1.5
                + self.quotes * 3.0
                + self.bookmarks * 4.0
            ) / self.impressions * 100
            self.priority_score = round(raw, 4)

        return self


# ─────────────────────────────────────────────
# arXiv Paper
# ─────────────────────────────────────────────

class ArxivPaper(BaseModel):
    arxiv_id:           str
    title:              Optional[str] = None
    abstract_snippet:   Optional[str] = None
    authors:            List[str] = Field(default_factory=list)
    submitted_date:     Optional[str] = None    # "YYYY-MM-DD"
    pdf_url:            Optional[str] = None
    relevance_score:    Optional[float] = None
    primary_category:   Optional[str] = None


# ─────────────────────────────────────────────
# Kaggle Dataset
# ─────────────────────────────────────────────

class KaggleDataset(BaseModel):
    dataset_id:         str
    title:              Optional[str] = None
    url:                Optional[str] = None
    usability_rating:   Optional[float] = None
    total_votes:        Optional[int] = None
    last_updated:       Optional[str] = None    # "YYYY-MM-DD"
    file_formats:       List[str] = Field(default_factory=list)
    row_count_estimate: Optional[int] = None
    relevant_columns:   List[str] = Field(default_factory=list)
    notes:              Optional[str] = None


# ─────────────────────────────────────────────
# Collection Stats
# ─────────────────────────────────────────────

class CollectionStats(BaseModel):
    api_calls_made:         int = 0
    tweets_fetched_raw:     int = 0
    tweets_after_filter:    int = 0
    filter_pass_rate:       Optional[float] = None
    avg_engagement_rate:    Optional[float] = None
    avg_bookmarks:          Optional[float] = None
    top_media_type:         Optional[str] = None
    thread_percentage:      Optional[float] = None


# ─────────────────────────────────────────────
# Miner Session (wrapper)
# ─────────────────────────────────────────────

class MinerSession(BaseModel):
    session_id:         str
    collected_at:       Optional[datetime] = None
    target_user:        Optional[str] = None
    niche:              Optional[str] = None

    tweets:             List[TweetRecord] = Field(default_factory=list)
    tweet_count:        int = 0
    arxiv_papers:       List[ArxivPaper] = Field(default_factory=list)
    paper_count:        int = 0
    kaggle_datasets:    List[KaggleDataset] = Field(default_factory=list)
    dataset_count:      int = 0

    collection_stats:   Optional[CollectionStats] = None
    errors:             List[Any] = Field(default_factory=list)
    warnings:           List[Any] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_counts(self) -> MinerSession:
        """Count alanlarını gerçek listelerle senkronize et."""
        self.tweet_count = len(self.tweets)
        self.paper_count = len(self.arxiv_papers)
        self.dataset_count = len(self.kaggle_datasets)
        return self


# ─────────────────────────────────────────────
# Lab Label (tweet_labels tablosuna yazılır)
# ─────────────────────────────────────────────

QUALITY_TIER_MAP = {
    range(9, 11): "S",
    range(7, 9):  "A",
    range(4, 7):  "B",
    range(1, 4):  "C",
}


def score_to_tier(score: int) -> str:
    for r, tier in QUALITY_TIER_MAP.items():
        if score in r:
            return tier
    return "C"


class LabLabel(BaseModel):
    tweet_id:                   str
    psikolojik_tetikleyici:     List[str] = Field(default_factory=list)
    primary_trigger:            Optional[str] = None
    icerik_formu:               Optional[str] = None
    ton:                        Optional[str] = None
    kanca_tipi:                 Optional[str] = None
    gorsel_format:              Optional[str] = None
    algoritma_sinyal:           List[str] = Field(default_factory=list)
    quality_score:              Optional[int] = None
    quality_tier:               Optional[str] = None
    hook_text:                  Optional[str] = None
    reasoning:                  Optional[str] = None
    processed_at:               Optional[datetime] = None
    model_used:                 Optional[str] = None
    lab_session_id:             Optional[str] = None

    @model_validator(mode="after")
    def derive_quality_tier(self) -> LabLabel:
        if self.quality_score is not None and self.quality_tier is None:
            self.quality_tier = score_to_tier(self.quality_score)
        return self
