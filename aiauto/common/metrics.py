
# aiauto/common/metrics.py
from __future__ import annotations

from typing import Tuple

# Cosine similarity
from sklearn.metrics.pairwise import cosine_similarity

# OpenAI embeddings via LangChain
try:
    from langchain_openai import OpenAIEmbeddings
except Exception as e:  # helpful message if missing
    OpenAIEmbeddings = None
    _IMPORT_ERR = e


def _require_embeddings():
    if OpenAIEmbeddings is None:
        raise RuntimeError(
            "OpenAIEmbeddings not available. Install and configure first:\n"
            "  pip install langchain-openai scikit-learn\n"
            "  export OPENAI_API_KEY=your_key_here\n"
            f"Underlying import error: {_IMPORT_ERR}"
        )


def semantic_agreement(text_a: str, text_b: str, threshold: float = 0.85) -> Tuple[bool, float]:
    """
    Return (is_match, score) where score is cosine similarity of embeddings in [-1, 1].
    is_match is True iff score >= threshold.

    Args:
        text_a: first text (e.g., UI answer)
        text_b: second text (e.g., RAG/ground-truth answer)
        threshold: decision boundary (typical 0.85–0.90 for semantic “same”)

    Example:
        ok, score = semantic_agreement("after 1 day", "in 24 hours", 0.86)
    """
    if not text_a or not text_b:
        return False, 0.0

    _require_embeddings()
    emb = OpenAIEmbeddings()  # uses OPENAI_API_KEY from env

    v_a = emb.embed_query(text_a)
    v_b = emb.embed_query(text_b)
    score = float(cosine_similarity([v_a], [v_b])[0][0])

    return (score >= threshold), score

def precision_recall_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}
