from app.rag.ingest import build_index, chunk_text


def test_short_text_is_a_single_chunk():
    assert chunk_text("Kargo ayni gun cikar.", chunk_size=500, overlap=100) == ["Kargo ayni gun cikar."]


def test_long_text_is_split_with_overlap():
    text = "".join(chr(ord("a") + (i % 26)) for i in range(1200))

    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert len(chunks) == 3
    assert all(len(chunk) <= 500 for chunk in chunks)
    # Each chunk starts with the last 100 characters of the previous one.
    assert chunks[0][-100:] == chunks[1][:100]
    assert chunks[1][-100:] == chunks[2][:100]
    # Nothing from the original text is lost.
    assert chunks[-1].endswith(text[-50:])


def test_build_index_keeps_metadata_and_numbers_chunks():
    docs = [
        {
            "doc_id": "prd-1001",
            "source_type": "product_spec",
            "channel": "site",
            "product_id": 1001,
            "title": "Pamuk Tisort",
            "content": "x" * 900,
        }
    ]

    index = build_index(docs, chunk_size=500, overlap=100)

    assert [item["doc_id"] for item in index] == ["prd-1001-chunk-1", "prd-1001-chunk-2"]
    assert all(item["product_id"] == 1001 for item in index)
    assert all(item["source_type"] == "product_spec" for item in index)
