import json

import pytest

from app.rag.retriever import RAGRetriever

DOCS = [
    {
        "doc_id": "site-return",
        "source_type": "return_policy",
        "channel": "site",
        "title": "Site Iade Politikasi",
        "content": "Kullanilmamis urunler 14 gun icinde iade edilebilir.",
    },
    {
        "doc_id": "trendyol-shipping",
        "source_type": "shipping_policy",
        "channel": "trendyol",
        "product_id": "1001",
        "title": "Trendyol Teslimat Bilgisi",
        "content": "Trendyol siparisleri 2 is gunu icinde kargoya verilir.",
    },
    {
        "doc_id": "hb-blender",
        "source_type": "product_spec",
        "channel": "hepsiburada",
        "product_id": "2002",
        "title": "700W Blender",
        "content": "700W motor, 1.5 litre cam hazne.",
    },
]


@pytest.fixture
def make_retriever(tmp_path, monkeypatch):
    """Build a retriever over DOCS without downloading an embedding model."""
    monkeypatch.setattr(RAGRetriever, "_try_enable_vector_search", lambda self: None)
    index_path = tmp_path / "rag_index.json"
    index_path.write_text(json.dumps(DOCS), encoding="utf-8")

    def _make(min_score: float = 0.15) -> RAGRetriever:
        return RAGRetriever(index_path=str(index_path), embedding_model="unused", min_score=min_score)

    return _make


def test_keyword_fallback_finds_the_relevant_document(make_retriever):
    retriever = make_retriever()

    results = retriever.retrieve("iade kac gun icinde", top_k=2)

    assert results[0].doc_id == "site-return"


def test_channel_filter_hides_other_marketplaces(make_retriever):
    retriever = make_retriever(min_score=0.0)

    results = retriever.retrieve("kargo", top_k=10, channel="trendyol")

    ids = {chunk.doc_id for chunk in results}
    assert "hb-blender" not in ids
    assert "site-return" not in ids
    assert "trendyol-shipping" in ids


def test_product_filter_keeps_only_that_product(make_retriever):
    retriever = make_retriever(min_score=0.0)

    results = retriever.retrieve("blender", top_k=10, product_id="2002")

    ids = {chunk.doc_id for chunk in results}
    assert "trendyol-shipping" not in ids
    assert "hb-blender" in ids


def test_min_score_drops_unrelated_documents(make_retriever):
    retriever = make_retriever(min_score=0.5)

    assert retriever.retrieve("bambaska bir soru", top_k=3) == []


class FakeEmbedder:
    """Maps each text to a 2-d vector so cosine similarity is easy to reason about."""

    VECTORS = {
        "iade": [1.0, 0.0],
        "kargo": [0.0, 1.0],
        "blender": [0.7, 0.7],
    }

    def encode(self, texts, normalize_embeddings=True):
        class Vector(list):
            def tolist(self):
                return list(self)

        out = []
        for text in texts:
            key = next((k for k in self.VECTORS if k in text.lower()), "blender")
            out.append(Vector(self.VECTORS[key]))
        return out


def test_vector_search_ranks_by_cosine_similarity(make_retriever):
    retriever = make_retriever(min_score=0.0)
    retriever._embedder = FakeEmbedder()
    retriever._doc_vectors = [[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]]
    retriever._enable_vector = True

    results = retriever.retrieve("kargo ne zaman", top_k=3)

    assert [chunk.doc_id for chunk in results] == ["trendyol-shipping", "hb-blender", "site-return"]
    assert results[0].score == pytest.approx(1.0)
