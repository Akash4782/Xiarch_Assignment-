"""
dedup.py — Semantic deduplication for the Research Agent.

Uses sentence-transformers to encode text chunks into vector embeddings,
then removes any chunk whose cosine similarity to an already-kept chunk
exceeds a configurable threshold.  This prevents the LLM synthesizer
from receiving redundant information that would waste context window space.

Model: all-MiniLM-L6-v2 (runs locally, ~80 MB, no internet required after
first download).
"""

# Singleton pattern — loading the model is expensive (~1-2 seconds)
_model = None


def _get_model():
    """Lazily load and cache the sentence-transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    """
    Split a body of text into fixed-size word chunks.

    Parameters
    ----------
    text       : The raw text to split.
    chunk_size : Approximate number of words per chunk.

    Returns
    -------
    List of text chunk strings.
    """
    words = text.split()
    return [
        " ".join(words[i : i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]


def deduplicate(chunks: list[str], threshold: float = 0.85) -> list[str]:
    """
    Remove semantically near-duplicate chunks using cosine similarity.

    Algorithm (O(n²) greedy):
      For each chunk, compare its embedding against all already-kept
      chunks.  If cosine similarity > threshold with any kept chunk,
      discard it as a duplicate.

    Parameters
    ----------
    chunks    : List of text chunks to deduplicate.
    threshold : Cosine similarity cutoff (0–1).  Higher = stricter.

    Returns
    -------
    Subset of the input chunks with near-duplicates removed.
    """
    if not chunks:
        return []

    model = _get_model()
    embeddings = model.encode(chunks, convert_to_tensor=True)

    from sentence_transformers import util
    kept_indices: list[int] = []
    for i, embedding in enumerate(embeddings):
        is_duplicate = any(
            util.cos_sim(embedding, embeddings[j]).item() > threshold
            for j in kept_indices
        )
        if not is_duplicate:
            kept_indices.append(i)

    return [chunks[i] for i in kept_indices]
