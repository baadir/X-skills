import { motion } from "framer-motion";
import { cn } from "../lib/utils";
import type { ThreadAnalysis } from "../types";

interface AnalysisPanelProps {
  analysis: ThreadAnalysis;
}

function ScoreBadge({ score }: { score?: string }) {
  if (!score) return null;
  const s = score.toLowerCase();
  const isHigh = s.includes("yüksek") || s.includes("high");
  const isLow = s.includes("düşük") || s.includes("low");

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border",
        isHigh
          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          : isLow
          ? "bg-red-500/10 text-red-400 border-red-500/20"
          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full",
          isHigh ? "bg-emerald-400" : isLow ? "bg-red-400" : "bg-amber-400"
        )}
      />
      {score}
    </span>
  );
}

function SignalTag({
  label,
  value,
  variant = "default",
}: {
  label: string;
  value?: string | null;
  variant?: "green" | "purple" | "yellow" | "red" | "default";
}) {
  if (!value) return null;
  const colors = {
    green: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    yellow: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    red: "bg-red-500/10 text-red-400 border-red-500/20",
    default: "bg-zinc-800 text-zinc-400 border-zinc-700",
  };

  return (
    <div className="flex items-start justify-between gap-2 py-2 border-b border-zinc-800 last:border-0">
      <span className="text-xs text-zinc-500 shrink-0 mt-0.5">{label}</span>
      <span
        className={cn(
          "text-xs px-2 py-0.5 rounded-full border text-right",
          colors[variant]
        )}
      >
        {value}
      </span>
    </div>
  );
}

function Section({
  title,
  children,
  delay = 0,
}: {
  title: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4"
    >
      <div className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
        {title}
      </div>
      {children}
    </motion.div>
  );
}

export function AnalysisPanel({ analysis }: AnalysisPanelProps) {
  const ep = analysis.engagement_profile;
  const lp = analysis.lab_pattern;

  return (
    <div className="flex flex-col gap-3">
      {/* Mode + X Score */}
      <Section title="Creator Modu & X Skoru" delay={0.1}>
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-violet-600/15 text-violet-300 text-xs font-medium border border-violet-500/20">
            {analysis.mode || "MOD 2 — THREAD"}
          </span>
          <ScoreBadge score={analysis.x_score} />
        </div>
        {analysis.x_score_reason && (
          <p className="text-xs text-zinc-400 leading-relaxed">
            {analysis.x_score_reason}
          </p>
        )}
      </Section>

      {/* Engagement Profile */}
      {ep && (
        <Section title="Engagement Profili" delay={0.15}>
          <SignalTag label="Dominant" value={ep.dominant_signal} variant="green" />
          <SignalTag label="İkincil" value={ep.secondary_signal} variant="purple" />
          <SignalTag label="Üçüncül" value={ep.tertiary_signal} variant="yellow" />
          {ep.risk_signal && (
            <SignalTag label="Risk" value={ep.risk_signal} variant="red" />
          )}
        </Section>
      )}

      {/* Lab Pattern */}
      {lp && (
        <Section title="Lab Pattern" delay={0.2}>
          <SignalTag label="Kanca Tipi" value={lp.kanca_tipi} />
          <SignalTag label="Psikolojik" value={lp.psikolojik_tetikleyici} />
          <SignalTag label="Format" value={lp.format} />
        </Section>
      )}

      {/* Mirror DNA */}
      <Section title="Mirror DNA Uyumu" delay={0.25}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs text-zinc-500">Uyum</span>
          <ScoreBadge score={analysis.mirror_dna_match} />
        </div>
        {analysis.mirror_dna_notes && (
          <p className="text-xs text-zinc-400 leading-relaxed italic">
            {analysis.mirror_dna_notes}
          </p>
        )}
      </Section>

      {/* Why this tweet */}
      {analysis.why_this_tweet && (
        <Section title="Neden Bu Tweet?" delay={0.3}>
          <div className="text-xs text-zinc-400 leading-relaxed space-y-1.5">
            {analysis.why_this_tweet.split("\n").map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        </Section>
      )}

      {/* Publish time */}
      {analysis.publish_time && (
        <Section title="Optimal Yayın Zamanı" delay={0.35}>
          <div className="flex items-center gap-2 text-xs text-zinc-300">
            <span className="text-base">📅</span>
            <span>{analysis.publish_time}</span>
          </div>
        </Section>
      )}
    </div>
  );
}
