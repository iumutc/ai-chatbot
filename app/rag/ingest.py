import argparse
import json
from pathlib import Path
from typing import Any


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    if len(text) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start = max(end - overlap, 0)
    return chunks


def load_documents(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Input file must contain a JSON list")
    return data


def build_index(docs: list[dict[str, Any]], chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc in docs:
        base_id = str(doc.get("doc_id", "doc"))
        content = str(doc.get("content", ""))
        pieces = chunk_text(content, chunk_size=chunk_size, overlap=overlap)

        for idx, piece in enumerate(pieces, start=1):
            out.append(
                {
                    "doc_id": f"{base_id}-chunk-{idx}",
                    "source_type": doc.get("source_type", "unknown"),
                    "channel": doc.get("channel"),
                    "marketplace": doc.get("marketplace"),
                    "product_id": doc.get("product_id"),
                    "title": doc.get("title", "Basliksiz"),
                    "content": piece,
                    "updated_at": doc.get("updated_at"),
                }
            )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a JSON RAG index with chunking")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    docs = load_documents(input_path)
    index = build_index(docs, chunk_size=args.chunk_size, overlap=args.overlap)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(index)} chunks to {output_path}")


if __name__ == "__main__":
    main()
