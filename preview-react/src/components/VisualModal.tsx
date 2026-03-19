import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { TweetItem } from "../types";

interface VisualModalProps {
  tweet: TweetItem | null;
  idx: number;
  onClose: () => void;
}

export function VisualModal({ tweet, idx, onClose }: VisualModalProps) {
  if (!tweet) return null;

  const visualSrc = tweet.visual_local
    ? `/visuals/${tweet.visual_local.split(/[\\/]/).pop()}`
    : tweet.visual_url || null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
        onClick={onClose}
      >
        {visualSrc ? (
          /* ── Full-screen image lightbox ── */
          <motion.div
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="relative flex items-center justify-center"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={onClose}
              className="absolute -top-3 -right-3 z-10 bg-zinc-800 hover:bg-zinc-700 text-white rounded-full w-8 h-8 flex items-center justify-center shadow-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
            <img
              src={visualSrc}
              alt="Tweet görseli"
              className="max-w-[90vw] max-h-[85vh] rounded-2xl shadow-2xl object-contain"
            />
          </motion.div>
        ) : (
          /* ── Visual suggestion modal ── */
          <motion.div
            initial={{ scale: 0.93, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.93, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="relative bg-zinc-900 border border-zinc-700/50 rounded-2xl p-5 max-w-lg w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-sm font-medium text-white mb-4">
              Tweet {idx + 1} — Görsel Önerisi
            </h3>

            {tweet.visual_suggestion ? (
              <>
                <div className="rounded-xl bg-zinc-800/50 border border-zinc-700/40 p-4 mb-3">
                  <div className="text-xs text-violet-400 font-medium mb-1">
                    Görsel Önerisi
                  </div>
                  <p className="text-sm text-zinc-300 leading-relaxed">
                    {tweet.visual_suggestion}
                  </p>
                </div>
                {tweet.wiro_prompt && (
                  <div className="rounded-xl bg-zinc-800/50 border border-zinc-700/40 p-4">
                    <div className="text-xs text-zinc-500 font-medium mb-1 uppercase tracking-wider">
                      Wiro.ai Prompt
                    </div>
                    <p className="text-xs text-zinc-400 font-mono leading-relaxed">
                      {tweet.wiro_prompt}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-zinc-500">Görsel yok.</p>
            )}
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
