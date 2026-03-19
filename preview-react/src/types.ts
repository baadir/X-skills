export interface TweetItem {
  number: number;
  text: string;
  visual_suggestion?: string | null;
  wiro_prompt?: string | null;
  visual_local?: string | null;
  visual_url?: string | null;
}

export interface EngagementProfile {
  dominant_signal?: string;
  secondary_signal?: string;
  tertiary_signal?: string;
  risk_signal?: string | null;
}

export interface LabPattern {
  kanca_tipi?: string;
  psikolojik_tetikleyici?: string;
  format?: string;
}

export interface ThreadAnalysis {
  mode?: string;
  format_id?: string;
  engagement_profile?: EngagementProfile;
  x_score?: string;
  x_score_reason?: string;
  lab_pattern?: LabPattern;
  mirror_dna_match?: string;
  mirror_dna_notes?: string;
  why_this_tweet?: string;
  publish_time?: string;
}

export interface ThreadData {
  thread_title: string;
  generated_at: string;
  author: {
    name: string;
    handle: string;
  };
  visual_variables?: Record<string, string>;
  tweets: TweetItem[];
  analysis?: ThreadAnalysis;
}

// ── Draft + Performance ───────────────────────────────────────
export type DraftStatus = "öneri" | "atılmış" | "arşiv";

export interface DraftInfo {
  id: string;
  draft_key: string;
  thread_title: string;
  status: DraftStatus;
  created_at: string;
  posted_at?: string | null;
  tweet_url?: string | null;
  first_tweet_id?: string | null;
}

export interface PerformanceSnapshot {
  day_number: 0 | 1 | 2 | 3;
  likes: number;
  retweets: number;
  replies: number;
  quotes: number;
  bookmarks: number;
  impressions: number;
  engagement_rate: number;
  fetched_at: string;
  source?: string;
}

export interface FeedbackItem {
  tweet_num: number | string;
  tweet_total: number;
  category: string;
  comment: string;
  timestamp: string;
}
