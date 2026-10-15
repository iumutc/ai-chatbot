import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RetrievedChunk:
    doc_id: str
    source_type: str
    channel: str | None
    product_id: str | None
    title: str
    content: str
    score: float


class RAGRetriever:
    def __init__(
        self,
        index_path: str,
        embedding_model: str,
        min_score: float = 0.15,
    ):
        self.index_path = Path(index_path)
        self.embedding_model = embedding_model
        self.min_score = min_score

        self._embedder = None
        self._doc_vectors: list[list[float]] = []
        self._enable_vector = False
        self.documents: list[dict[str, Any]] = []

        self.reload()

    def reload(self) -> None:
        self.documents = self._load_index()
        self._doc_vectors = []
        self._enable_vector = False
        self._try_enable_vector_search()

    def _load_index(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        with self.index_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        raise ValueError("RAG index must be a JSON list of documents")

    def _try_enable_vector_search(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            self._enable_vector = False
            return

        if not self.documents:
            self._enable_vector = False
            return

        self._embedder = SentenceTransformer(self.embedding_model)
        contents = [doc.get("content", "") for doc in self.documents]
        vectors = self._embedder.encode(contents, normalize_embeddings=True)
        self._doc_vectors = [vector.tolist() for vector in vectors]
        self._enable_vector = True

    def retrieve(
        self,
        query: str,
        top_k: int,
        channel: str | None = None,
        product_id: str | None = None,
        marketplace: str | None = None,
    ) -> list[RetrievedChunk]:
        docs = self._filter_documents(channel=channel, product_id=product_id, marketplace=marketplace)
        if not docs:
            return []

        scored = self._score_documents(query=query, docs=docs)
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)

        chunks: list[RetrievedChunk] = []
        for doc, score in ranked[:top_k]:
            if score < self.min_score:
                continue
            chunks.append(
                RetrievedChunk(
                    doc_id=doc.get("doc_id", "unknown"),
                    source_type=doc.get("source_type", "unknown"),
                    channel=doc.get("channel"),
                    product_id=doc.get("product_id"),
                    title=doc.get("title", "Basliksiz"),
                    content=doc.get("content", ""),
                    score=round(float(score), 4),
                )
            )
        return chunks

    def _filter_documents(
        self,
        channel: str | None,
        product_id: str | None,
        marketplace: str | None,
    ) -> list[dict[str, Any]]:
        normalized_channel = (marketplace or channel or "").lower()
        filtered: list[dict[str, Any]] = []

        for doc in self.documents:
            doc_channel = (doc.get("channel") or "").lower()
            doc_marketplace = (doc.get("marketplace") or "").lower()
            doc_product_id = doc.get("product_id")

            channel_match = (
                not normalized_channel
                or not doc_channel
                or doc_channel == normalized_channel
                or doc_marketplace == normalized_channel
            )
            product_match = (
                not product_id
                or not doc_product_id
                or str(doc_product_id) == str(product_id)
            )

            if channel_match and product_match:
                filtered.append(doc)

        return filtered

    def _score_documents(
        self,
        query: str,
        docs: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], float]]:
        if self._enable_vector:
            return self._vector_scores(query, docs)
        return self._lexical_scores(query, docs)

    def _vector_scores(
        self,
        query: str,
        docs: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], float]]:
        query_vector = self._embedder.encode([query], normalize_embeddings=True)[0].tolist()
        id_to_vector = {
            doc.get("doc_id", f"doc-{idx}"): vector
            for idx, (doc, vector) in enumerate(zip(self.documents, self._doc_vectors))
        }

        scored: list[tuple[dict[str, Any], float]] = []
        for doc in docs:
            doc_id = doc.get("doc_id")
            vector = id_to_vector.get(doc_id)
            if vector is None:
                score = 0.0
            else:
                score = self._cosine(query_vector, vector)
            scored.append((doc, score))
        return scored

    def _lexical_scores(
        self,
        query: str,
        docs: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], float]]:
        query_terms = set(self._tokenize(query))
        if not query_terms:
            return [(doc, 0.0) for doc in docs]

        scored: list[tuple[dict[str, Any], float]] = []
        for doc in docs:
            terms = set(self._tokenize(f"{doc.get('title', '')} {doc.get('content', '')}"))
            overlap = len(query_terms.intersection(terms))
            score = overlap / len(query_terms)
            scored.append((doc, score))
        return scored

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return [part for part in normalized.split() if len(part) > 1]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        a_norm = math.sqrt(sum(x * x for x in a))
        b_norm = math.sqrt(sum(y * y for y in b))
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return dot / (a_norm * b_norm)
