import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Copy, Check, MessageCircle, Repeat2, Heart, Bookmark, Pencil, X, Image } from "lucide-react";
import { cn } from "../lib/utils";
import type { TweetItem } from "../types";

interface TweetCardProps {
  tweet: TweetItem;
  idx: number;
  total: number;
  author: { name: string; handle: string };
  comment: string;
  onCommentSave: (idx: number, val: string) => void;
  onCommentClear: (idx: number) => void;
  onVisualClick: (tweet: TweetItem, idx: number) => void;
}

function formatTweetText(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/→/g, '<span class="text-violet-400">→</span>')
    .replace(/```([\s\S]*?)```/g, (_: string, code: string) =>
      `<code class="block bg-zinc-800/80 rounded px-3 py-2 text-xs font-mono text-emerald-300 my-2 whitespace-pre">${code.trim()}</code>`
    )
    .replace(/(https?:\/\/[^\s]+)/g, '<span class="text-sky-400">$1</span>')
    .replace(/#(\w+)/g, '<span class="text-violet-400">#$1</span>')
    .replace(/@(\w+)/g, '<span class="text-sky-400">@$1</span>')
    .replace(/\n/g, "<br/>");
}

export function TweetCard({
  tweet,
  idx,
  total,
  author,
  comment,
  onCommentSave,
  onCommentClear,
  onVisualClick,
}: TweetCardProps) {
  const [copied, setCopied] = useState(false);
  const [commentOpen, setCommentOpen] = useState(false);
  const [commentVal, setCommentVal] = useState(comment);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const chars = tweet.text.length;
  const charOverflow = chars > 280;
  const charWarn = chars > 260 && !charOverflow;

  const isLast = idx === total - 1;

  function handleCopy() {
    navigator.clipboard.writeText(tweet.text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleCommentToggle() {
    setCommentOpen((v) => !v);
    if (!commentOpen) {
      setTimeout(() => textareaRef.current?.focus(), 80);
    }
  }

  function handleSave() {
    onCommentSave(idx, commentVal.trim());
    setCommentOpen(false);
  }

  function handleClear() {
    setCommentVal("");
    onCommentClear(idx);
    setCommentOpen(false);
  }

  const visualSrc = tweet.visual_local
    ? `/visuals/${tweet.visual_local.split(/[\\/]/).pop()}`
    : tweet.visual_url || null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: idx * 0.05 }}
      className="flex gap-3"
    >
      {/* Thread line */}
      <div className="flex flex-col items-center gap-0 shrink-0 w-10">
        <div className="w-9 h-9 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-xs font-bold text-violet-300 shrink-0">
          BC
        </div>
        {!isLast && (
          <div className="w-0.5 flex-1 mt-1 bg-zinc-700/50 min-h-[20px]" />
        )}
      </div>

      {/* Tweet body */}
      <div className="flex-1 pb-5 min-w-0">
        {/* Header row */}
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-1.5 text-sm">
            <span className="font-semibold text-white">{author.name}</span>
            <span className="text-zinc-500">{author.handle}</span>
            <span className="text-zinc-600 text-xs">
              {idx + 1}/{total}
            </span>
          </div>
          <button
            onClick={handleCopy}
            className={cn(
              "flex items-center gap-1 text-xs px-2.5 py-1 rounded-full transition-all",
              copied
                ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-violet-600/10 hover:text-violet-300 hover:border-violet-500/30"
            )}
          >
            {copied ? (
              <Check className="w-3 h-3" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
            {copied ? "Kopyalandı" : "Kopyala"}
          </button>
        </div>

        {/* Tweet text */}
        <div
          className="text-[15px] leading-relaxed text-zinc-200 whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: formatTweetText(tweet.text) }}
        />

        {/* Visual (Wiro.ai generated) */}
        {visualSrc && (
          <div
            className="mt-3 rounded-xl overflow-hidden border border-zinc-700/50 cursor-pointer hover:border-violet-500/40 transition-colors"
            onClick={() => onVisualClick(tweet, idx)}
          >
            <img
              src={visualSrc}
              alt="Tweet görseli"
              className="w-full object-cover max-h-64"
              loading="lazy"
            />
          </div>
        )}

        {/* Visual suggestion (no image generated yet) */}
        {!visualSrc && tweet.visual_suggestion && (
          <button
            onClick={() => onVisualClick(tweet, idx)}
            className="mt-3 w-full flex items-center gap-3 p-3 rounded-xl bg-zinc-800/50 border border-zinc-700/40 hover:border-violet-500/30 hover:bg-violet-600/5 transition-all text-left"
          >
            <Image className="w-4 h-4 text-violet-400 shrink-0" />
            <div>
              <div className="text-xs text-violet-400 font-medium mb-0.5">
                Görsel Önerisi
              </div>
              <div className="text-xs text-zinc-400 leading-relaxed">
                {tweet.visual_suggestion}
              </div>
            </div>
          </button>
        )}

        {/* Char count + actions */}
        <div className="flex items-center justify-between mt-2.5">
          <div className="flex items-center gap-4 text-zinc-600">
            <button className="flex items-center gap-1 text-xs hover:text-sky-400 transition-colors">
              <MessageCircle className="w-3.5 h-3.5" /> 0
            </button>
            <button className="flex items-center gap-1 text-xs hover:text-emerald-400 transition-colors">
              <Repeat2 className="w-3.5 h-3.5" /> 0
            </button>
            <button className="flex items-center gap-1 text-xs hover:text-pink-400 transition-colors">
              <Heart className="w-3.5 h-3.5" /> 0
            </button>
            <button className="flex items-center gap-1 text-xs hover:text-amber-400 transition-colors">
              <Bookmark className="w-3.5 h-3.5" /> 0
            </button>
          </div>
          <span
            className={cn(
              "text-xs font-mono tabular-nums",
              charOverflow
                ? "text-red-400"
                : charWarn
                ? "text-amber-400"
                : "text-zinc-600"
            )}
          >
            {chars}/280
          </span>
        </div>

        {/* Per-tweet inline comment */}
        <div className="mt-2">
          <button
            onClick={handleCommentToggle}
            className={cn(
              "flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg transition-all",
              comment
                ? "text-amber-400 bg-amber-500/10 border border-amber-500/20"
                : "text-zinc-500 hover:text-zinc-300"
            )}
          >
            <Pencil className="w-3 h-3" />
            {comment ? "Yorum var — düzenle" : "Yorum ekle"}
          </button>

          <AnimatePresence>
            {commentOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="mt-2 rounded-xl border border-zinc-700/50 bg-zinc-800/50 p-3">
                  <textarea
                    ref={textareaRef}
                    value={commentVal}
                    onChange={(e) => setCommentVal(e.target.value)}
                    placeholder="Bu tweet için notunuz... (örn: 'kanca daha güçlü olabilir', 'çok uzun kısalt')"
                    rows={3}
                    className="w-full bg-transparent text-sm text-zinc-200 placeholder-zinc-600 resize-none outline-none leading-relaxed"
                  />
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-zinc-700/50">
                    <button
                      onClick={handleSave}
                      className="text-xs px-3 py-1 rounded-lg bg-violet-600/20 text-violet-300 border border-violet-500/30 hover:bg-violet-600/30 transition-colors"
                    >
                      Kaydet
                    </button>
                    <button
                      onClick={handleClear}
                      className="text-xs px-3 py-1 rounded-lg bg-zinc-700/50 text-zinc-400 border border-zinc-600/30 hover:bg-zinc-700 transition-colors"
                    >
                      Temizle
                    </button>
                    <button
                      onClick={() => setCommentOpen(false)}
                      className="ml-auto text-zinc-600 hover:text-zinc-400 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
