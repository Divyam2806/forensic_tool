from sentence_transformers import SentenceTransformer

_embedder = None

def build_embedding_text(artifact) -> str:
    try:
        if not isinstance(artifact, dict):
            return "unknown artifact"

        summary = artifact.get("artifact_summary")
        if isinstance(summary, str) and summary.strip():
            return summary

        parts = []

        try:
            if artifact.get("name"):
                parts.append(str(artifact["name"]))
        except Exception:
            pass

        try:
            if artifact.get("extension"):
                parts.append(f"({artifact['extension']} file)")
        except Exception:
            pass

        try:
            if artifact.get("path"):
                parts.append(f"located at {artifact['path']}")
        except Exception:
            pass

        try:
            if artifact.get("time_modified"):
                parts.append(f"modified {artifact['time_modified']}")
        except Exception:
            pass

        try:
            if artifact.get("size_human"):
                parts.append(f"size {artifact['size_human']}")
        except Exception:
            pass

        try:
            if artifact.get("author") and artifact["author"] != "unavailable":
                parts.append(f"authored by {artifact['author']}")
        except Exception:
            pass

        try:
            if artifact.get("domain"):
                parts.append(f"domain {artifact['domain']}")
        except Exception:
            pass

        try:
            if artifact.get("name") and artifact.get("domain"):
                parts.append(f"cookie named {artifact['name']}")
        except Exception:
            pass

        return ", ".join(parts) if parts else "unknown artifact"

    except Exception as e:
        print(f"[warn] build_embedding_text failed entirely, using fallback: {e}")
        return "unknown artifact"


def get_embedder():
    global _embedder
    try:
        if _embedder is None:
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedder
    except Exception as e:
        print(f"[error] Could not load embedding model: {e}")
        raise  # this one should NOT be silently swallowed -- if the model can't load, nothing will work


def get_embedding(text) -> list:
    try:
        if not isinstance(text, str) or not text.strip():
            text = "unknown artifact"
        embedder = get_embedder()
        vector = embedder.encode(text, normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        print(f"[warn] Embedding failed for text (using zero vector fallback): {e}")
        return [0.0] * 384


def safe_process_artifact_for_embedding(artifact) -> dict:
    """
    Top-level wrapper: never raises, always returns a usable result,
    even if artifact is completely malformed.
    """
    try:
        text = build_embedding_text(artifact)
        embedding = get_embedding(text)
        return {"embedding_text": text, "embedding": embedding, "status": "ok"}
    except Exception as e:
        print(f"[error] Unexpected failure processing artifact, using full fallback: {e}")
        return {"embedding_text": "unknown artifact", "embedding": [0.0] * 384, "status": "failed"}