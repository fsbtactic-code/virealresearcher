"""
ai_detector.py — Lightweight local AI-topic relevance scorer.

Operates in 3 levels, fastest first:
  1. Keyword match    — instant, exact keywords from AI_KEYWORDS list
  2. Contextual combo — pure Python, checks for co-occurring semantic clusters
  3. Alt-text / subs  — Instagram's own auto-generated image descriptions
                        and Reels subtitles (already captured via GraphQL)

No GPU, no ML inference, no external API. Pure string ops.
Returns a score 0.0–1.0. Threshold for "is AI post" = 0.5.
"""
import re
import logging

log = logging.getLogger(__name__)

# ── Contextual word clusters ──────────────────────────────────────────────────
# If ANY word from cluster_A appears WITH any word from cluster_B → likely AI post

CONTEXT_CLUSTERS = [
    # Creative generation patterns
    ({"generate", "generated", "creation", "creating", "made", "built", "designed",
      "write", "wrote", "written", "draw", "draws", "drawing", "animated", "render", "rendered"},
     {"image", "video", "photo", "art", "music", "voice", "text", "code", "script",
      "logo", "avatar", "thumbnail", "animation", "video", "clip", "reel"}),

    # Tool/automation patterns
    ({"automate", "automated", "automation", "workflow", "pipeline", "agent",
      "assistant", "chatbot", "bot", "tool", "tooling", "integrate", "integration"},
     {"business", "marketing", "content", "social", "email", "data", "task",
      "process", "work", "productivity", "startup", "freelance", "agency", "client"}),

    # Tech innovation / future patterns
    ({"future", "revolution", "changing", "disrupting", "transform", "replace",
      "replaced", "replacing", "new era", "next level", "game changer", "game-changer"},
     {"job", "jobs", "work", "industry", "technology", "tech", "digital", "creative",
      "designer", "developer", "marketer", "writer", "artist"}),

    # Learning/prompt patterns
    ({"learn", "learning", "use", "using", "how to", "tutorial", "guide", "tips",
      "trick", "tricks", "hack", "hacks", "secret", "secrets", "master"},
     {"prompt", "model", "gpt", "chatbot", "assistant", "automation", "ai", "ml"}),

    # Russian contextual patterns
    ({"создал", "сделал", "написал", "нарисовал", "сгенерировал", "автоматизировал",
      "использовал", "попробовал", "протестировал", "обучил", "запустил"},
     {"инструмент", "сервис", "приложение", "бот", "автоматизация", "видео",
      "картинку", "текст", "контент", "код", "голос", "музыку", "аватар"}),

    ({"будущее", "революция", "меняет", "заменит", "трансформирует", "автоматизирует"},
     {"работа", "профессия", "индустрия", "маркетинг", "дизайн", "разработка"}),
]

# Single high-signal words — alone enough to suggest AI topic
HIGH_SIGNAL_SINGLE = {
    # EN — very specific to AI space
    "midjourney", "stablediffusion", "comfyui", "llm", "llms", "rag", "finetuning",
    "fine-tuning", "tokenize", "embeddings", "inference", "openai", "anthropic",
    "deepseek", "multimodal", "diffusion", "langchain", "autogpt",
    "gpt4", "gpt-4", "gpt3", "gpt-3", "claude3", "claude-3",
    "dall-e", "dalle", "heygen", "elevenlabs", "synthesia", "suno", "udio",
    "gemini", "kling", "cursor", "vibe-coding", "vibecoding",
    # RU
    "нейросетью", "нейросети", "нейронку", "нейронкой", "промпт", "промптинг",
    "генеративный", "генеративной", "искусственным", "искусственного",
}


def _tokenize(text: str) -> set:
    """Fast lowercase word tokenization, including multi-word."""
    return set(re.findall(r'\b\w+\b', text.lower()))


def _contains_cluster(words: set, cluster_a: set, cluster_b: set) -> bool:
    """Check if the word set has overlap with both clusters."""
    return bool(words & cluster_a) and bool(words & cluster_b)


def score_ai_relevance(
    caption: str = "",
    alt_text: str = "",
    subtitles: str = "",
) -> float:
    """
    Returns 0.0–1.0. Use >= 0.5 as threshold for "is AI topic".

    Args:
        caption:    Post caption / description text
        alt_text:   Instagram auto-generated accessibility caption (image AI description)
        subtitles:  Reels subtitles / transcript text
    """
    # Combine all text signals
    all_text = " ".join(filter(None, [caption, alt_text, subtitles]))
    if not all_text.strip():
        return 0.0

    all_lower = all_text.lower()
    words = _tokenize(all_lower)

    # ── Level 1: High-signal single words ───────────────────────────────────
    if words & HIGH_SIGNAL_SINGLE:
        log.debug(f"[ai_detect] L1 hit: {words & HIGH_SIGNAL_SINGLE}")
        return 1.0

    # ── Level 2: Contextual co-occurrence clusters ───────────────────────────
    for cluster_a, cluster_b in CONTEXT_CLUSTERS:
        if _contains_cluster(words, cluster_a, cluster_b):
            log.debug(f"[ai_detect] L2 cluster hit")
            return 0.75

    # ── Level 3: Alt-text / subtitles only (weaker signal) ──────────────────
    # Instagram auto-generates alt like: "Photo of a person using a computer with AI interface"
    # We only run this if we have alt/subtitle data and caption alone didn't match
    if alt_text or subtitles:
        aux_text = f"{alt_text} {subtitles}".lower()
        aux_words = _tokenize(aux_text)

        # Light keyword check on auxiliary text
        ai_hints = {
            "robot", "algorithm", "neural", "artificial", "automated", "digital art",
            "generated", "synthetic", "hologram", "interface", "screen", "monitor",
            "robot", "drone", "futuristic", "code", "coding", "programming",
            # RU
            "экран", "компьютер", "разработка", "программирование", "цифровой"
        }
        if aux_words & ai_hints:
            for cluster_a, cluster_b in CONTEXT_CLUSTERS[:3]:  # Only first 3 clusters for aux
                if _contains_cluster(words | aux_words, cluster_a, cluster_b):
                    log.debug(f"[ai_detect] L3 alt-text cluster hit")
                    return 0.6

    return 0.0


def is_ai_content(
    caption: str = "",
    alt_text: str = "",
    subtitles: str = "",
    threshold: float = 0.5
) -> bool:
    """Convenience wrapper — returns bool for filter integration."""
    return score_ai_relevance(caption, alt_text, subtitles) >= threshold
