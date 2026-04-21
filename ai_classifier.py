"""
ai_classifier.py — Lightweight semantic topic classifier.

Uses sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) to
determine whether a post is topically relevant when exact keyword matching
fails.

Design principles (железобетонность):
  - sentence-transformers is an OPTIONAL dependency.
    If not installed → all methods degrade gracefully (bypass mode).
  - Model is loaded ONCE in a background thread at application startup.
    Never blocks the UI or scraping pipeline.
  - classify() always returns Optional[bool]:
      True  = post is on-topic
      False = post is off-topic
      None  = bypass (model not ready, text too short, etc.)
  - Every code path is wrapped in try/except.
  - Thread-safe: uses threading.Lock for model access.
"""

import logging
import threading
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model name — multilingual MiniLM, 118 MB, supports RU+EN+50 languages
# ---------------------------------------------------------------------------
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_MIN_TEXT_LEN = 10   # skip posts with very short text
_BATCH_SIZE = 32     # encode posts in batches for efficiency


class _TopicClassifier:
    """
    Singleton topic classifier backed by sentence-transformers.

    Usage:
        from ai_classifier import classifier

        # At app startup (non-blocking):
        classifier.warm_up("нейросети, AI, ChatGPT, машинное обучение")

        # During scraping:
        result = classifier.classify("Попробовал новый промпт в Клоде...")
        # True → on-topic, False → off-topic, None → bypass
    """

    def __init__(self):
        self._model = None
        self._ref_embedding = None   # encoded topic description
        self._topic_text: str = ""
        self._ready: bool = False
        self._loading: bool = False
        self._load_error: str = ""
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def warm_up(self, topic_text: str) -> None:
        """
        Encode topic description and (lazily) load the model.
        Call from a background thread — never from the main/GUI thread.

        topic_text: comma-separated or free-text description of the niche.
        """
        if not topic_text or not topic_text.strip():
            log.info("[AI] warm_up: empty topic_text — classifier stays in bypass mode")
            return

        topic_text = topic_text.strip()

        with self._lock:
            if self._loading:
                log.debug("[AI] warm_up: already loading, skipping duplicate call")
                return
            self._loading = True
            self._ready = False
            self._load_error = ""
            self._topic_text = topic_text

        log.info(f"[AI] Loading sentence-transformers model '{_MODEL_NAME}' ...")
        try:
            # Import inside function so missing library = graceful fail
            from sentence_transformers import SentenceTransformer  # noqa: import-outside-toplevel
            import numpy as np  # noqa: import-outside-toplevel

            model = SentenceTransformer(_MODEL_NAME)
            log.info("[AI] Model loaded successfully")

            # Encode the topic description
            ref_emb = model.encode(topic_text, convert_to_numpy=True, normalize_embeddings=True)

            with self._lock:
                self._model = model
                self._ref_embedding = ref_emb
                self._ready = True
                self._loading = False

            log.info(f"[AI] Classifier ready. Topic: '{topic_text[:80]}...' " if len(topic_text) > 80 else f"[AI] Classifier ready. Topic: '{topic_text}'")

        except ImportError:
            msg = "sentence-transformers not installed — AI classifier disabled (bypass mode)"
            log.warning(f"[AI] {msg}")
            with self._lock:
                self._loading = False
                self._load_error = msg

        except Exception as e:
            msg = f"Failed to load model: {e}"
            log.error(f"[AI] {msg}")
            with self._lock:
                self._loading = False
                self._load_error = msg

    def classify(self, post_text: str, threshold: float = 0.35) -> Optional[bool]:
        """
        Classify whether post_text is topically relevant.

        Returns:
            True  — semantically on-topic (include post)
            False — off-topic (exclude post)
            None  — bypass: model not ready, text too short
        """
        # Fast bypass checks (no lock needed for reads of stable values)
        if not self._ready:
            return None

        if not post_text or len(post_text.strip()) < _MIN_TEXT_LEN:
            return None

        try:
            import numpy as np  # noqa: import-outside-toplevel

            with self._lock:
                if not self._ready or self._model is None or self._ref_embedding is None:
                    return None
                model = self._model
                ref_emb = self._ref_embedding

            # Encode the post text
            post_emb = model.encode(
                post_text[:512],    # cap at 512 chars — more than enough for IG posts
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            # Cosine similarity (both vectors are L2-normalised → dot product = cosine)
            similarity = float(np.dot(post_emb, ref_emb))

            is_match = similarity >= threshold
            log.debug(f"[AI] similarity={similarity:.3f} threshold={threshold} → {'PASS' if is_match else 'FAIL'} | text[:60]={post_text[:60]!r}")
            return is_match

        except Exception as e:
            log.debug(f"[AI] classify() error (bypass): {e}")
            return None

    # ------------------------------------------------------------------
    # Status helpers (for UI / logging)
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        return self._ready

    def is_loading(self) -> bool:
        return self._loading

    def get_status(self) -> str:
        """Human-readable status string for UI indicators."""
        if self._ready:
            return "ready"
        if self._loading:
            return "loading"
        if self._load_error:
            return "unavailable"
        return "idle"

    def get_status_text(self) -> str:
        """Russian UI status string."""
        if self._ready:
            return "AI готов"
        if self._loading:
            return "AI загружается..."
        if "not installed" in self._load_error:
            return "AI недоступен (нет библиотеки)"
        if self._load_error:
            return "AI ошибка загрузки"
        return "AI не инициализирован"


# ---------------------------------------------------------------------------
# Module-level singleton — import from anywhere in the project
# ---------------------------------------------------------------------------
classifier = _TopicClassifier()


def warm_up_in_background(topic_text: str) -> None:
    """
    Convenience function: starts warm_up() in a daemon thread.
    Call this at application startup once the user's topic is known.
    """
    if not topic_text or not topic_text.strip():
        return
    t = threading.Thread(
        target=classifier.warm_up,
        args=(topic_text,),
        name="ai-classifier-warmup",
        daemon=True,
    )
    t.start()
    log.info("[AI] warm_up thread started")
