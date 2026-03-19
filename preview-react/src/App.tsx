import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RefreshCw, Copy, Check, Twitter } from "lucide-react";
import { TweetCard } from "./components/TweetCard";
import { AnalysisPanel } from "./components/AnalysisPanel";
import { FeedbackPanel } from "./components/FeedbackPanel";
import { VisualModal } from "./components/VisualModal";
import { DraftControls } from "./components/DraftControls";
import { PerformanceCard } from "./components/PerformanceCard";
import type { ThreadData, TweetItem, DraftInfo, PerformanceSnapshot } from "./types";
import { cn } from "./lib/utils";

// ── db_manager.make_draft_key ile aynı mantık ─────────────────
function makeDraftKey(title: string, generatedAt: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .slice(0, 80)
    .replace(/^-|-$/g, "");
  const date = (generatedAt || "").slice(0, 10);
  return `${slug}__${date}`;
}

// ── Per-tweet comments hook ───────────────────────────────────
function useTweetComments() {
  const [comments, setComments] = useState<Record<number, string>>(() => {
    try { return JSON.parse(localStorage.getItem("tweetComments") || "{}"); }
    catch { return {}; }
  });

  function save(idx: number, val: string) {
    const next = { ...comments, [idx]: val };
    if (!val) delete next[idx];
    setComments(next);
    localStorage.setItem("tweetComments", JSON.stringify(next));
  }

  function clear(idx: number) {
    const next = { ...comments };
    delete next[idx];
    setComments(next);
    localStorage.setItem("tweetComments", JSON.stringify(next));
  }

  return { comments, save, clear };
}

// ════════════════════════════════════════════════════════════
export default function App() {
  const [thread,       setThread]       = useState<ThreadData | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [spinning,     setSpinning]     = useState(false);
  const [copyAllDone,  setCopyAllDone]  = useState(false);
  const [modalTweet,   setModalTweet]   = useState<TweetItem | null>(null);
  const [modalIdx,     setModalIdx]     = useState(0);

  // Draft + Performance state
  const [draft,        setDraft]        = useState<DraftInfo | null>(null);
  const [snapshots,    setSnapshots]    = useState<PerformanceSnapshot[]>([]);
  const [draftChecked, setDraftChecked] = useState(false); // thread yüklenince bir kez kontrol et

  const prevJson = useRef<string>("");
  const { comments, save: saveComment, clear: clearComment } = useTweetComments();

  // ── Thread yükle ──────────────────────────────────────────
  const loadThread = useCallback(async (manual = false) => {
    if (manual) setSpinning(true);
    try {
      const res = await fetch("/api/thread");
      if (!res.ok) { setLoading(false); return; }
      const data: ThreadData = await res.json();
      const json = JSON.stringify(data);
      if (json !== prevJson.current) {
        prevJson.current = json;
        setThread(data);
        setDraft(null);         // Yeni thread → draft durumunu sıfırla
        setSnapshots([]);
        setDraftChecked(false); // Yeniden kontrol et
      }
    } catch { /* ignore */ }
    setLoading(false);
    if (manual) setTimeout(() => setSpinning(false), 600);
  }, []);

  useEffect(() => {
    loadThread();
    const id = setInterval(() => loadThread(), 5000);
    return () => clearInterval(id);
  }, [loadThread]);

  // ── Draft varlık kontrolü (thread değişince) ──────────────
  useEffect(() => {
    if (!thread || draftChecked) return;
    setDraftChecked(true);
    const key = makeDraftKey(thread.thread_title, thread.generated_at);
    fetch(`/api/drafts/by-key/${encodeURIComponent(key)}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.exists) {
          setDraft({
            id:              data.id,
            draft_key:       key,
            thread_title:    thread.thread_title,
            status:          data.status,
            created_at:      data.created_at || "",
            posted_at:       data.posted_at,
            tweet_url:       data.tweet_url,
            first_tweet_id:  data.first_tweet_id,
          });
          // Atıldıysa performans snapshot'larını da çek
          if (data.status === "atılmış") {
            loadSnapshots(data.id);
          }
        }
      })
      .catch(() => { /* DB yoksa sessizce geç */ });
  }, [thread, draftChecked]);

  // ── Performans snapshot'larını yükle ─────────────────────
  async function loadSnapshots(draftId: string) {
    try {
      const res = await fetch(`/api/performance/${draftId}`);
      if (!res.ok) return;
      const data = await res.json();
      setSnapshots(data.snapshots || []);
    } catch { /* ignore */ }
  }

  // ── Copy All ──────────────────────────────────────────────
  function copyAll() {
    if (!thread?.tweets?.length) return;
    const text = thread.tweets
      .map((t, i) => `${i + 1}/\n${t.text}`)
      .join("\n\n---\n\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopyAllDone(true);
      setTimeout(() => setCopyAllDone(false), 2500);
    });
  }

  const tweets   = thread?.tweets || [];
  const analysis = thread?.analysis;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-zinc-200 flex flex-col">
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-zinc-800/60">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-7 h-7 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center">
              <Twitter className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <span className="font-semibold text-white text-sm">TwitterYoldas</span>
            <span className="text-zinc-600 text-sm hidden sm:inline">Preview</span>
          </div>

          {/* Thread başlık */}
          {thread && (
            <div className="flex-1 min-w-0 hidden md:block">
              <p className="text-xs text-zinc-500 truncate text-center">
                {thread.thread_title} · {new Date(thread.generated_at).toLocaleString("tr-TR")}
              </p>
            </div>
          )}

          {/* Aksiyonlar */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Draft kontrolleri */}
            {thread && (
              <DraftControls
                thread={thread}
                draft={draft}
                onDraftSaved={(d) => setDraft(d)}
                onPosted={(d) => {
                  setDraft(d);
                  loadSnapshots(d.id);
                }}
              />
            )}

            {/* Copy All */}
            {tweets.length > 0 && (
              <button
                onClick={copyAll}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-violet-600/10 hover:text-violet-300 hover:border-violet-500/30"
              >
                {copyAllDone ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                <span className="hidden sm:inline">
                  {copyAllDone ? "Kopyalandı!" : `${tweets.length} tweet kopyala`}
                </span>
              </button>
            )}

            {/* Yenile */}
            <button
              onClick={() => loadThread(true)}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-zinc-700 transition-all"
            >
              <RefreshCw className={cn("w-3 h-3", spinning && "animate-spin")} />
              <span className="hidden sm:inline">Yenile</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin" />
              <p className="text-sm text-zinc-500">Yükleniyor...</p>
            </div>
          </div>
        ) : !thread ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-6 items-start">

            {/* LEFT — Thread önizleme */}
            <section>
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">Thread Önizleme</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500 text-xs border border-zinc-700">
                    {tweets.length} tweet
                  </span>
                </div>
              </div>

              <div className="space-y-0">
                <AnimatePresence>
                  {tweets.map((tweet, idx) => (
                    <TweetCard
                      key={idx}
                      tweet={tweet}
                      idx={idx}
                      total={tweets.length}
                      author={thread.author}
                      comment={comments[idx] || ""}
                      onCommentSave={saveComment}
                      onCommentClear={clearComment}
                      onVisualClick={(t, i) => {
                        setModalTweet(t);
                        setModalIdx(i);
                      }}
                    />
                  ))}
                </AnimatePresence>
              </div>
            </section>

            {/* RIGHT — Analiz + Performans */}
            <aside className="lg:sticky lg:top-20 flex flex-col gap-3">
              {analysis && (
                <>
                  <div className="text-sm font-medium text-white">Creator Analizi</div>
                  <AnalysisPanel analysis={analysis} />
                </>
              )}

              {/* Performans paneli — sadece 'atılmış' ise */}
              {draft?.status === "atılmış" && draft.id && (
                <>
                  <div className="text-sm font-medium text-white mt-2">Performans Takibi</div>
                  <PerformanceCard
                    draftId={draft.id}
                    snapshots={snapshots}
                    onRefresh={() => loadSnapshots(draft.id)}
                  />
                </>
              )}
            </aside>
          </div>
        )}
      </main>

      {/* Feedback FAB */}
      <FeedbackPanel tweets={tweets} tweetComments={comments} />

      {/* Visual Modal */}
      {modalTweet && (
        <VisualModal
          tweet={modalTweet}
          idx={modalIdx}
          onClose={() => setModalTweet(null)}
        />
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center h-64 gap-3"
    >
      <div className="w-14 h-14 rounded-2xl bg-zinc-800/80 border border-zinc-700/50 flex items-center justify-center text-2xl">
        ⏳
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-zinc-300">Creator skill çıktısı bekleniyor...</p>
        <p className="text-xs text-zinc-600 mt-1">Thread üretildikten sonra otomatik görünür.</p>
      </div>
    </motion.div>
  );
}
