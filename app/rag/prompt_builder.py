from app.channels import ChannelProfile
from app.rag.retriever import RetrievedChunk


def build_system_prompt(
    profile: ChannelProfile,
    chunks: list[RetrievedChunk],
) -> str:
    context_block = _build_context_block(chunks)

    return (
        "Sen bir e-ticaret musteri destek asistanisin.\n"
        f"- Kanal: {profile.name}\n"
        f"- Ton: {profile.tone}\n"
        f"- Maksimum {profile.max_sentences} cumle kullan.\n"
        f"- Format kurali: {profile.formatting_rule}\n"
        "- Cevap dili Turkce olsun.\n"
        "- Sadece verilen BAGLAM bilgisini kullan.\n"
        "- Konusma gecmisindeki son kullanici niyetini dikkate al.\n"
        "- Emin olmadigin bir bilgiyi uydurma.\n"
        "- BAGLAM yetersizse su kalibi kullan: \"Bu bilgi bende net degil. Su detayi paylasir misiniz: ...?\"\n"
        "- Asla 'Human:' veya 'Assistant:' etiketi yazma.\n\n"
        f"BAGLAM:\n{context_block}"
    )


def build_user_prompt(message: str, history: list[dict[str, str]] | None = None) -> str:
    history_block = _build_history_block(history or [])
    return (
        f"KONUSMA GECMISI:\n{history_block}\n\n"
        "SON KULLANICI MESAJI:\n"
        f"{message.strip()}"
    )


def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(ilgili kaynak bulunamadi)"

    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{idx}] doc_id={chunk.doc_id} | source={chunk.source_type} | score={chunk.score}\n"
            f"baslik: {chunk.title}\n"
            f"icerik: {chunk.content}"
        )
    return "\n\n".join(lines)


def _build_history_block(history: list[dict[str, str]]) -> str:
    if not history:
        return "(onceki mesaj yok)"

    lines: list[str] = []
    for item in history:
        role = item.get("role", "unknown")
        content = item.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
