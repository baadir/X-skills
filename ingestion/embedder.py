"""
Text → vector(1536) dönüşümü via OpenAI text-embedding-3-small.

OPENAI_API_KEY env değişkeni gerekli.

Kullanım:
  from ingestion.embedder import Embedder
  emb = Embedder()
  vec = emb.embed("agentic AI is the future")        # list[float] — 1536 boyut
  vecs = emb.embed_batch(["tweet1", "tweet2"])        # list[list[float]]
"""
from __future__ import annotations

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

OPENAI_DIM = 1536
OPENAI_MODEL = "text-embedding-3-small"


class Embedder:
    """
    OpenAI text-embedding-3-small wrapper.
    OPENAI_API_KEY env değişkeni init sırasında okunur.
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY env değişkeni set edilmemiş.\n"
                ".env dosyasına OPENAI_API_KEY=sk-... ekle."
            )
        try:
            from openai import OpenAI  # type: ignore
            self._client = OpenAI(api_key=api_key)
        except ImportError:
            raise RuntimeError("openai paketi bulunamadı: pip install openai")

        self.dim = OPENAI_DIM
        self.active_backend = "openai"
        logger.info(f"Embedder hazır — model: {OPENAI_MODEL}, boyut: {self.dim}")

    def embed(self, text: str) -> List[float]:
        """Tek metin → float listesi (1536 boyut)."""
        if not text or not text.strip():
            return [0.0] * self.dim

        resp = self._client.embeddings.create(
            model=OPENAI_MODEL,
            input=text.strip(),
        )
        return resp.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Toplu embed — OpenAI max 2048 input/request.
        batch_size=100 → güvenli ve hızlı.
        """
        if not texts:
            return []

        results: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = [t.strip() if t and t.strip() else " " for t in texts[i:i + batch_size]]
            resp = self._client.embeddings.create(
                model=OPENAI_MODEL,
                input=chunk,
            )
            # API girdi sırasını korur
            results.extend([item.embedding for item in resp.data])
        return results

    def embed_tweet(self, text: str, hook_text: str | None = None) -> List[float]:
        """
        Tweet için özel embed:
        Hook mevcutsa 'hook | tam_metin' formatında birleştir.
        Hook semantik arama kalitesini artırır.
        """
        if hook_text and hook_text.strip():
            combined = f"{hook_text.strip()} | {text.strip()}"
        else:
            combined = text.strip()
        return self.embed(combined)
