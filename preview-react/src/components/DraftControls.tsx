/**
 * DraftControls — "Taslak Kaydet" + "Atıldı olarak işaretle" + durum badge'i
 * Header'a entegre edilir.
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookmarkPlus, CheckCircle2, ExternalLink, Loader2, X } from "lucide-react";
import { cn } from "../lib/utils";
import type { DraftInfo, ThreadData } from "../types";

interface DraftControlsProps {
  thread: ThreadData | null;
  draft: DraftInfo | null;
  onDraftSaved: (d: DraftInfo) => void;
  onPosted: (d: DraftInfo) => void;
}

// ── "Tweet Linki Gir" Modal ───────────────────────────────────
interface PostModalProps {
  draftId: string;
  threadTitle: string;
  onClose: () => void;
  onPosted: (info: DraftInfo) => void;
}

function PostModal({ draftId, threadTitle, onClose, onPosted }: PostModalProps) {
  const [url, setUrl]       = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const urlValid = /\/status\/\d{10,20}/.test(url) || /^\d{10,20}$/.test(url.trim());

  async function handleSubmit() {
    if (!urlValid) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft_id: draftId, tweet_url: url.trim() }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setError(data.error || "Bir hata oluştu.");
        return;
      }
      onPosted({
        id: draftId,
        draft_key: "",
        thread_title: threadTitle,
        status: "atılmış",
        created_at: "",
        posted_at: data.posted_at,
        tweet_url: url.trim(),
        first_tweet_id: data.tweet_id,
      });
      onClose();
    } catch {
      setError("Sunucu bağlantısı başarısız.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.94, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.94, opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="relative bg-zinc-900 border border-zinc-700/50 rounded-2xl p-6 w-full max-w-md shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <h3 className="text-sm font-semibold text-white mb-1">
          Tweet atıldı olarak işaretle
        </h3>
        <p className="text-xs text-zinc-500 mb-5 leading-relaxed">
          X'te attıktan sonra tweet linkini yapıştırın. Tweet ID otomatik alınır.
        </p>

        <div className="mb-1">
          <div className="text-xs text-zinc-500 mb-2">Thread başlığı</div>
          <div className="text-xs text-zinc-300 bg-zinc-800 rounded-lg px-3 py-2 line-clamp-2">
            {threadTitle}
          </div>
        </div>

        <div className="mt-4 mb-5">
          <div className="text-xs text-zinc-500 mb-2">Tweet linki veya ID</div>
          <input
            type="text"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setError(""); }}
            placeholder="https://x.com/ciftcibahadir/status/12345…"
            className="w-full bg-zinc-800/60 border border-zinc-700/50 text-sm text-zinc-200
                       placeholder-zinc-600 rounded-xl px-3 py-2.5 outline-none
                       focus:border-emerald-500/40 transition-colors"
            onKeyDown={(e) => e.key === "Enter" && urlValid && handleSubmit()}
            autoFocus
          />
          {url && !urlValid && (
            <p className="text-xs text-red-400 mt-1.5">
              Geçerli bir tweet URL'i veya ID girin (örn: https://x.com/.../status/12345…)
            </p>
          )}
          {error && (
            <p className="text-xs text-red-400 mt-1.5">{error}</p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSubmit}
            disabled={!urlValid || loading}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all",
              urlValid && !loading
                ? "bg-emerald-600 text-white hover:bg-emerald-500"
                : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
            )}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            {loading ? "Kaydediliyor..." : "Atıldı olarak kaydet"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            İptal
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Ana bileşen ───────────────────────────────────────────────
export function DraftControls({ thread, draft, onDraftSaved, onPosted }: DraftControlsProps) {
  const [saving,      setSaving]      = useState(false);
  const [saveMsg,     setSaveMsg]     = useState<"idle" | "saved" | "conflict" | "error">("idle");
  const [postModal,   setPostModal]   = useState(false);

  async function handleSaveDraft() {
    if (!thread || saving) return;
    setSaving(true);
    try {
      const res  = await fetch("/api/drafts", { method: "POST" });
      const data = await res.json();
      if (res.status === 409) {
        setSaveMsg("conflict");
        // Conflict durumunda mevcut draft bilgisini üst bileşene bildir
        onDraftSaved({
          id: data.draft_id,
          draft_key: data.draft_key,
          thread_title: thread.thread_title,
          status: "öneri",
          created_at: "",
        });
      } else if (data.ok) {
        setSaveMsg("saved");
        onDraftSaved({
          id: data.draft_id,
          draft_key: data.draft_key,
          thread_title: thread.thread_title,
          status: "öneri",
          created_at: new Date().toISOString(),
        });
      } else {
        setSaveMsg("error");
      }
    } catch {
      setSaveMsg("error");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg("idle"), 3000);
    }
  }

  // Durum badge'i
  const statusBadge = draft ? (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium",
        draft.status === "atılmış"
          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
      )}
    >
      <span className={cn(
        "w-1.5 h-1.5 rounded-full",
        draft.status === "atılmış" ? "bg-emerald-400" : "bg-amber-400"
      )} />
      {draft.status === "atılmış" ? "Atıldı" : "Öneri"}
    </span>
  ) : null;

  return (
    <>
      <div className="flex items-center gap-2">
        {statusBadge}

        {/* Taslak Kaydet */}
        {!draft && thread && (
          <button
            onClick={handleSaveDraft}
            disabled={saving}
            className={cn(
              "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all",
              saveMsg === "saved"    && "bg-emerald-600/20 text-emerald-400 border-emerald-500/30",
              saveMsg === "conflict" && "bg-amber-600/20 text-amber-400 border-amber-500/30",
              saveMsg === "error"    && "bg-red-600/20 text-red-400 border-red-500/30",
              saveMsg === "idle"     && !saving && "bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-violet-600/10 hover:text-violet-300 hover:border-violet-500/30",
              saving && "opacity-60 cursor-not-allowed"
            )}
          >
            {saving ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <BookmarkPlus className="w-3 h-3" />
            )}
            {saving        ? "Kaydediliyor..."
            : saveMsg === "saved"    ? "Kaydedildi!"
            : saveMsg === "conflict" ? "Zaten kayıtlı"
            : saveMsg === "error"    ? "Hata"
            : "Taslak Kaydet"}
          </button>
        )}

        {/* Atıldı İşaretle — sadece 'öneri' durumundaysa */}
        {draft?.status === "öneri" && (
          <button
            onClick={() => setPostModal(true)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-emerald-600/10 hover:text-emerald-300 hover:border-emerald-500/30 transition-all"
          >
            <ExternalLink className="w-3 h-3" />
            Attım, linkle
          </button>
        )}

        {/* Tweet linki — atıldıysa */}
        {draft?.status === "atılmış" && draft.tweet_url && (
          <a
            href={draft.tweet_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-sky-400 hover:border-sky-500/30 transition-all"
          >
            <ExternalLink className="w-3 h-3" />
            Tweet'i Gör
          </a>
        )}
      </div>

      <AnimatePresence>
        {postModal && draft && (
          <PostModal
            draftId={draft.id}
            threadTitle={thread?.thread_title || ""}
            onClose={() => setPostModal(false)}
            onPosted={(info) => {
              onPosted(info);
              setPostModal(false);
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
