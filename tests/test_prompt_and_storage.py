import pytest

from app.channels import get_channel_profile
from app.rag.prompt_builder import build_system_prompt, build_user_prompt
from app.rag.retriever import RetrievedChunk
from app.storage.conversation_store import ConversationStore


def _chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        doc_id="doc-1",
        source_type="shipping_policy",
        channel="site",
        product_id=None,
        title="Kargo",
        content=content,
        score=0.9,
    )


def test_unknown_channel_falls_back_to_site_profile():
    assert get_channel_profile("bilinmeyen").name == "site"
    assert get_channel_profile(None).name == "site"
    assert get_channel_profile("Trendyol").name == "trendyol"


def test_system_prompt_contains_retrieved_context_and_channel_rules():
    profile = get_channel_profile("hepsiburada")

    prompt = build_system_prompt(profile, [_chunk("15:00'e kadar verilen siparisler ayni gun kargoda.")])

    assert "15:00'e kadar" in prompt
    assert "Kanal: hepsiburada" in prompt
    assert f"Maksimum {profile.max_sentences} cumle" in prompt


def test_system_prompt_marks_missing_context():
    prompt = build_system_prompt(get_channel_profile("site"), [])

    assert "(ilgili kaynak bulunamadi)" in prompt


def test_user_prompt_includes_history_and_latest_message():
    history = [{"role": "user", "content": "Tisort var mi?"}, {"role": "assistant", "content": "Evet."}]

    prompt = build_user_prompt("  Hangi renkler?  ", history)

    assert "user: Tisort var mi?" in prompt
    assert prompt.endswith("Hangi renkler?")


def test_conversation_store_returns_last_messages_in_order(tmp_path):
    store = ConversationStore(str(tmp_path / "chat.db"))
    conversation = store.create_conversation(
        title="Test", channel="site", product_id=None, marketplace=None, language="tr"
    )
    for i in range(5):
        store.add_message(conversation_id=conversation.id, role="user", content=f"mesaj {i}")

    last_three = store.list_messages(conversation.id, limit=3)

    assert [m.content for m in last_three] == ["mesaj 2", "mesaj 3", "mesaj 4"]
    assert len(store.list_messages(conversation.id)) == 5


def test_missing_conversation_raises_key_error(tmp_path):
    store = ConversationStore(str(tmp_path / "chat.db"))

    with pytest.raises(KeyError):
        store.get_conversation(42)
