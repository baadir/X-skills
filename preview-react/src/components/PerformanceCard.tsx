/**
 * PerformanceCard — İlk 3 gün tweet performans takip paneli
 * Sağ sidebar'a (AnalysisPanel altına) eklenir.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Heart, Repeat2, MessageCircle, Quote, Bookmark, Eye, TrendingUp } from "lucide-react";
import { cn } from "../lib/utils";
import type { PerformanceSnapshot } from "../types";

interface PerformanceCardProps {
  draftId: string;
  snapshots: PerformanceSnapshot[];
  onRefresh?: () => void;
}

const DAY_LABELS: Record<number, string> = {
  0: "Atış",
  1: "Gün 1",
  2: "Gün 2",
  3: "Gün 3",
};

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return "az önce";
  if (diff < 3600)  return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} saat önce`;
  return `${Math.floor(diff / 86400)} gün önce`;
}

interface MetricRowProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color?: string;
}

function MetricRow({ icon, label, value, color = "text-zinc-400" }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <div className={cn("flex items-center gap-2 text-xs", color)}>
        {icon}
        <span>{label}</span>
      </div>
      <span className="text-sm font-semibold text-zinc-200 tabular-nums">{fmt(value)}</span>
    </div>
  );
}

export function PerformanceCard({ draftId, snapshots, onRefresh }: PerformanceCardProps) {
  const [activeDay, setActiveDay] = useState<number>(() => {
    if (!snapshots.length) return 0;
    return Math.max(...snapshots.map((s) => s.day_number));
  });
  const [fetching, setFetching] = useState(false);

  const snap = snapshots.find((s) => s.day_number === activeDay);
  const hasDay = (d: number) => snapshots.some((s) => s.day_number === d);

  async function triggerFetch() {
    setFetching(true);
    try {
      await fetch(`/api/performance/${draftId}/fetch`, { method: "POST" });
      onRefresh?.();
    } catch { /* ignore */ }
    finally { setFetching(false); }
  }

  // Tamamlanma yüzdesi (4 günden kaçı var)
  const completedDays = [0,1,2,3].filter(hasDay).length;
  const progressPct   = (completedDays / 4) * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5 text-violet-400" />
          <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
            Performans
          </span>
        </div>
        <button
          onClick={triggerFetch}
          disabled={fetching}
          title="Yenile (manuel çekme)"
          className="text-zinc-600 hover:text-zinc-400 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", fetching && "animate-spin")} />
        </button>
      </div>

      {/* Gün tab'ları */}
      <div className="flex items-center gap-1 mb-4">
        {[0, 1, 2, 3].map((d) => (
          <button
            key={d}
            onClick={() => hasDay(d) && setActiveDay(d)}
            className={cn(
              "flex-1 text-xs py-1.5 rounded-lg border transition-all",
              hasDay(d)
                ? activeDay === d
                  ? "bg-violet-600/20 text-violet-300 border-violet-500/30"
                  : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-600"
                : "bg-zinc-900 text-zinc-700 border-zinc-800/50 cursor-not-allowed"
            )}
          >
            {DAY_LABELS[d]}
          </button>
        ))}
      </div>

      {/* Metrikler */}
      {snap ? (
        <div className="divide-y divide-zinc-800/50">
          <MetricRow
            icon={<Heart className="w-3.5 h-3.5" />}
            label="Beğeni"
            value={snap.likes}
            color="text-pink-400"
          />
          <MetricRow
            icon={<Repeat2 className="w-3.5 h-3.5" />}
            label="Retweet"
            value={snap.retweets}
            color="text-emerald-400"
          />
          <MetricRow
            icon={<MessageCircle className="w-3.5 h-3.5" />}
            label="Yanıt"
            value={snap.replies}
            color="text-sky-400"
          />
          <MetricRow
            icon={<Quote className="w-3.5 h-3.5" />}
            label="Alıntı"
            value={snap.quotes}
            color="text-amber-400"
          />
          <MetricRow
            icon={<Bookmark className="w-3.5 h-3.5" />}
            label="Kaydet"
            value={snap.bookmarks}
            color="text-violet-400"
          />
          {snap.impressions > 0 && (
            <MetricRow
              icon={<Eye className="w-3.5 h-3.5" />}
              label="Gösterim"
              value={snap.impressions}
              color="text-zinc-500"
            />
          )}

          {/* Engagement Rate */}
          {snap.engagement_rate !== undefined && (
            <div className="pt-2.5 mt-1">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-zinc-500">Engagement Rate</span>
                <span className="font-semibold text-violet-300">
                  {snap.engagement_rate.toFixed(2)}%
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-violet-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(snap.engagement_rate * 10, 100)}%` }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                />
              </div>
            </div>
          )}

          {/* Son güncelleme */}
          <div className="pt-2 text-xs text-zinc-700 text-right">
            {timeAgo(snap.fetched_at)} · {snap.source || "twikit"}
          </div>
        </div>
      ) : (
        <div className="text-center py-4">
          <p className="text-xs text-zinc-600">
            {hasDay(0) ? "Bu gün için veri yok." : "Henüz veri çekilmedi."}
          </p>
          <button
            onClick={triggerFetch}
            className="mt-2 text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            Şimdi çek →
          </button>
        </div>
      )}

      {/* 3-gün pencere progress */}
      <div className="mt-3 pt-3 border-t border-zinc-800">
        <div className="flex items-center justify-between text-xs text-zinc-600 mb-1.5">
          <span>3 günlük pencere</span>
          <span>{completedDays}/4 gün</span>
        </div>
        <div className="h-1 rounded-full bg-zinc-800 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-emerald-600/60"
            initial={{ width: 0 }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
