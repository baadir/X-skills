import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Trash2, Plus } from "lucide-react";
import { cn } from "../lib/utils";
import type { FeedbackItem, TweetItem } from "../types";

interface FeedbackPanelProps {
  tweets: TweetItem[];
  tweetComments: Record<number, string>;
}

const CATEGORIES = ["ton", "kanca", "uzunluk", "dil", "içerik", "genel"];

export function FeedbackPanel({ tweets, tweetComments }: FeedbackPanelProps) {
  const [open, setOpen] = useState(false);
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([]);
  const [comment, setComment] = useState("");
  const [tweetNum, setTweetNum] = useState("0");
  const [category, setCategory] = useState("ton");
  const [sent, setSent] = useState(false);

  const inlineCount = Object.values(tweetComments).filter(Boolean).length;
  const totalCount = feedbackItems.length + inlineCount;

  useEffect(() => {
    if (open) loadFeedback();
  }, [open]);

  async function loadFeedback() {
    try {
      const res = await fetch("/api/feedback");
      if (res.ok) {
        const data = await res.json();
        setFeedbackItems(data.items || []);
      }
    } catch {}
  }

  async function addItem() {
    if (!comment.trim()) return;
    const item: FeedbackItem = {
      tweet_num: tweetNum === "0" ? "genel" : parseInt(tweetNum),
      tweet_total: tweets.length,
      category,
      comment: comment.trim(),
      timestamp: new Date().toLocaleTimeString("tr-TR"),
    };
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "add", item }),
    });
    setComment("");
    loadFeedback();
  }

  async function deleteItem(idx: number) {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", idx }),
    });
    loadFeedback();
  }

  async function clearAll() {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "clear" }),
    });
    setFeedbackItems([]);
  }

  async function sendAll() {
    const inlineItems = Object.entries(tweetComments)
      .filter(([, v]) => v)
      .map(([idx, c]) => ({
        tweet_num: parseInt(idx) + 1,
        tweet_total: tweets.length,
        category: "yorum",
        comment: c,
        timestamp: new Date().toLocaleTimeString("tr-TR"),
      }));

    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "send_all", inline_items: inlineItems }),
    });

    setSent(true);
    setTimeout(() => setSent(false), 3000);
    loadFeedback();
  }

  return (
    <>
      {/* FAB */}
      <motion.button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-6 right-6 flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium shadow-xl transition-all z-50",
          "bg-violet-600 text-white hover:bg-violet-500",
          totalCount > 0 && "bg-violet-700"
        )}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
      >
        <MessageCircle className="w-4 h-4" />
        {totalCount > 0 ? (
          <>
            <span>{totalCount} yorum</span>
            <span className="w-5 h-5 rounded-full bg-white text-violet-700 text-xs font-bold flex items-center justify-center">
              {totalCount}
            </span>
          </>
        ) : (
          "Feedback"
        )}
      </motion.button>

      {/* Panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, x: 24, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 24, scale: 0.97 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-20 right-6 w-[380px] max-h-[70vh] flex flex-col z-40 rounded-2xl border border-zinc-700/50 bg-zinc-900/95 backdrop-blur-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
              <span className="text-sm font-medium text-white">
                Tweet Feedback
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={clearAll}
                  className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" />
                  Temizle
                </button>
                <button
                  onClick={sendAll}
                  className={cn(
                    "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all",
                    sent
                      ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                      : "bg-violet-600/20 text-violet-300 border border-violet-500/30 hover:bg-violet-600/30"
                  )}
                >
                  <Send className="w-3 h-3" />
                  {sent ? "Gönderildi!" : "Claude'a Gönder"}
                </button>
                <button
                  onClick={() => setOpen(false)}
                  className="text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Tweet select */}
              <div className="flex items-center gap-2">
                <label className="text-xs text-zinc-500 shrink-0">Tweet:</label>
                <select
                  value={tweetNum}
                  onChange={(e) => setTweetNum(e.target.value)}
                  className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs rounded-lg px-2 py-1.5 outline-none"
                >
                  <option value="0">Tüm thread</option>
                  {tweets.map((_, i) => (
                    <option key={i} value={String(i + 1)}>
                      Tweet {i + 1}
                    </option>
                  ))}
                </select>
              </div>

              {/* Category tabs */}
              <div className="flex flex-wrap gap-1.5">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategory(cat)}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-full border transition-all",
                      category === cat
                        ? "bg-violet-600/20 text-violet-300 border-violet-500/30"
                        : "bg-zinc-800 text-zinc-500 border-zinc-700 hover:border-zinc-600"
                    )}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Textarea */}
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Feedback'inizi yazın... (örn: '2. tweet çok uzun, kısalt')"
                rows={3}
                className="w-full bg-zinc-800/50 border border-zinc-700/50 text-sm text-zinc-200 placeholder-zinc-600 rounded-xl p-3 resize-none outline-none focus:border-violet-500/40 transition-colors"
              />
              <button
                onClick={addItem}
                disabled={!comment.trim()}
                className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg bg-violet-600/20 text-violet-300 border border-violet-500/30 hover:bg-violet-600/30 transition-all disabled:opacity-40"
              >
                <Plus className="w-3.5 h-3.5" />
                Ekle
              </button>

              {/* Feedback list */}
              {feedbackItems.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-zinc-600 uppercase tracking-wider">
                    Kayıtlı feedbackler
                  </div>
                  {feedbackItems.map((item, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 p-3 rounded-xl bg-zinc-800/50 border border-zinc-700/40"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="text-xs text-violet-400">
                            Tweet {item.tweet_num}
                          </span>
                          <span className="text-xs text-zinc-600">·</span>
                          <span className="text-xs text-zinc-500">
                            {item.category}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-300 leading-relaxed">
                          {item.comment}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteItem(i)}
                        className="text-zinc-600 hover:text-zinc-400 transition-colors shrink-0 mt-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Hint */}
              {sent && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3"
                >
                  Feedback kaydedildi. Claude Code'da bir sonraki mesajınızla
                  birlikte otomatik gönderilecek.
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
