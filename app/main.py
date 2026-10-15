from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.channels import get_channel_profile
from app.config import (
    CHANNEL_DATA_PROVIDER,
    CHAT_DB_PATH,
    CHAT_HISTORY_LIMIT,
    DEVICE,
    ENTEGRA_API_KEY,
    ENTEGRA_API_KEY_HEADER,
    ENTEGRA_API_SECRET,
    ENTEGRA_API_SECRET_HEADER,
    ENTEGRA_AUTH_ENDPOINT,
    ENTEGRA_AUTH_TYPE,
    ENTEGRA_BASE_URL,
    ENTEGRA_ENABLED,
    ENTEGRA_MAX_PAGES,
    ENTEGRA_PASSWORD,
    ENTEGRA_PRODUCTS_ENDPOINT,
    ENTEGRA_STOCK_CACHE_PATH,
    ENTEGRA_STOCK_ENDPOINT,
    ENTEGRA_TIMEOUT_SEC,
    ENTEGRA_TOKEN,
    ENTEGRA_USERNAME,
    MAX_NEW_TOKENS,
    MODEL_ID,
    RAG_EMBEDDING_MODEL,
    RAG_ENABLED,
    RAG_INDEX_PATH,
    RAG_KB_PATH,
    RAG_MIN_SCORE,
    RAG_TOP_K,
)
from app.integrations.entegra import EntegraSyncService
from app.llm import LocalLLM
from app.providers.base import ProductSnapshot
from app.providers.factory import build_channel_provider
from app.rag.prompt_builder import build_system_prompt, build_user_prompt
from app.rag.retriever import RAGRetriever, RetrievedChunk
from app.storage.conversation_store import ConversationStore, Message
from app.ui.test_ui import TEST_UI_HTML


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading model...")
    app.state.llm = LocalLLM(model_id=MODEL_ID, device=DEVICE)
    print("Model loaded.")

    app.state.rag = None
    if RAG_ENABLED:
        print("Loading RAG index...")
        app.state.rag = RAGRetriever(
            index_path=RAG_INDEX_PATH,
            embedding_model=RAG_EMBEDDING_MODEL,
            min_score=RAG_MIN_SCORE,
        )
        print("RAG index loaded.")

    app.state.entegra = EntegraSyncService(
        enabled=ENTEGRA_ENABLED,
        base_url=ENTEGRA_BASE_URL,
        products_endpoint=ENTEGRA_PRODUCTS_ENDPOINT,
        stock_endpoint=ENTEGRA_STOCK_ENDPOINT,
        timeout_sec=ENTEGRA_TIMEOUT_SEC,
        auth_type=ENTEGRA_AUTH_TYPE,
        token=ENTEGRA_TOKEN,
        api_key=ENTEGRA_API_KEY,
        api_secret=ENTEGRA_API_SECRET,
        api_key_header=ENTEGRA_API_KEY_HEADER,
        api_secret_header=ENTEGRA_API_SECRET_HEADER,
        kb_path=RAG_KB_PATH,
        index_path=RAG_INDEX_PATH,
        stock_cache_path=ENTEGRA_STOCK_CACHE_PATH,
        username=ENTEGRA_USERNAME,
        password=ENTEGRA_PASSWORD,
        auth_endpoint=ENTEGRA_AUTH_ENDPOINT,
        max_pages=ENTEGRA_MAX_PAGES,
    )

    app.state.channel_provider = build_channel_provider(
        entegra_service=app.state.entegra,
        kb_path=RAG_KB_PATH,
    )
    app.state.conversations = ConversationStore(CHAT_DB_PATH)

    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    channel: str = Field(default="site")
    marketplace: str | None = None
    product_id: str | None = None
    language: str = Field(default="tr")


class SyncRequest(BaseModel):
    reload_retriever: bool = True


class ConversationCreateRequest(BaseModel):
    title: str = Field(min_length=1, default="Yeni konusma")
    channel: str = Field(default="site")
    marketplace: str | None = None
    product_id: str | None = None
    language: str = Field(default="tr")


class ConversationMessageRequest(BaseModel):
    message: str = Field(min_length=1)


@app.get("/")
def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE,
        "rag_enabled": RAG_ENABLED,
        "rag_index_path": RAG_INDEX_PATH,
        "entegra_enabled": ENTEGRA_ENABLED,
        "entegra_base_url_set": bool(ENTEGRA_BASE_URL),
        "channel_data_provider": CHANNEL_DATA_PROVIDER,
        "chat_db_path": CHAT_DB_PATH,
    }


@app.get("/ui", response_class=HTMLResponse)
def test_ui():
    return HTMLResponse(TEST_UI_HTML)


@app.get("/conversations")
def list_conversations():
    store: ConversationStore = app.state.conversations
    conversations = store.list_conversations()
    return {"conversations": [_conversation_to_dict(item) for item in conversations]}


@app.post("/conversations")
def create_conversation(req: ConversationCreateRequest):
    store: ConversationStore = app.state.conversations
    conversation = store.create_conversation(
        title=req.title,
        channel=req.channel,
        product_id=req.product_id,
        marketplace=req.marketplace,
        language=req.language,
    )
    return {"conversation": _conversation_to_dict(conversation)}


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int):
    store: ConversationStore = app.state.conversations
    try:
        conversation = store.get_conversation(conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    messages = store.list_messages(conversation_id)
    return {
        "conversation": _conversation_to_dict(conversation),
        "messages": [_message_to_dict(item) for item in messages],
    }


@app.post("/conversations/{conversation_id}/messages")
def send_conversation_message(conversation_id: int, req: ConversationMessageRequest):
    store: ConversationStore = app.state.conversations
    try:
        conversation = store.get_conversation(conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    user_message = store.add_message(
        conversation_id=conversation_id,
        role="user",
        content=req.message.strip(),
    )

    result = _generate_chat_response(
        message=req.message,
        channel=conversation.channel,
        marketplace=conversation.marketplace,
        product_id=conversation.product_id,
        language=conversation.language,
        history_messages=store.list_messages(conversation_id, limit=CHAT_HISTORY_LIMIT),
    )

    assistant_message = store.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=result["response"],
    )

    return {
        "conversation": _conversation_to_dict(store.get_conversation(conversation_id)),
        "user_message": _message_to_dict(user_message),
        "assistant_message": _message_to_dict(assistant_message),
        "response": result,
    }


@app.post("/sync/entegra")
def sync_entegra(req: SyncRequest):
    service: EntegraSyncService = app.state.entegra
    retriever: RAGRetriever | None = app.state.rag

    try:
        result = service.sync_products_to_rag()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Entegra sync failed: {exc}") from exc

    reloaded = False
    if req.reload_retriever and retriever is not None:
        retriever.reload()
        reloaded = True

    return {
        "status": "ok",
        "products_fetched": result.products_fetched,
        "products_upserted": result.products_upserted,
        "index_chunks_written": result.index_chunks_written,
        "synced_at": result.synced_at,
        "retriever_reloaded": reloaded,
    }


@app.post("/chat")
def chat(req: ChatRequest):
    return _generate_chat_response(
        message=req.message,
        channel=req.channel,
        marketplace=req.marketplace,
        product_id=req.product_id,
        language=req.language,
        history_messages=[],
    )


def _generate_chat_response(
    *,
    message: str,
    channel: str,
    marketplace: str | None,
    product_id: str | None,
    language: str,
    history_messages: list[Message],
):
    del language
    model = app.state.llm
    retriever: RAGRetriever | None = app.state.rag
    channel_provider = app.state.channel_provider

    resolved_channel = marketplace or channel
    profile = get_channel_profile(resolved_channel)

    chunks: list[RetrievedChunk] = []
    if retriever is not None:
        chunks = retriever.retrieve(
            query=message,
            top_k=RAG_TOP_K,
            channel=channel,
            product_id=product_id,
            marketplace=marketplace,
        )

    live_stock = None
    product_snapshot: ProductSnapshot | None = None

    if product_id:
        try:
            product_snapshot = channel_provider.get_product_snapshot(product_id, resolved_channel)
        except Exception:
            product_snapshot = None

        if _is_stock_question(message):
            try:
                live_stock = channel_provider.get_stock(product_id, resolved_channel)
            except Exception:
                live_stock = None

        if product_snapshot is not None:
            chunks.append(_chunk_from_product_snapshot(product_snapshot))

        if live_stock is not None:
            chunks.append(
                RetrievedChunk(
                    doc_id=f"channel-live-stock-{product_id}",
                    source_type="live_stock",
                    channel=channel,
                    product_id=product_id,
                    title="Canli Stok Bilgisi",
                    content=f"Urun {product_id} icin guncel stok adedi: {live_stock}",
                    score=1.0,
                )
            )

    history = [
        {"role": item.role, "content": item.content}
        for item in history_messages[:-1]
    ]

    system_prompt = build_system_prompt(profile=profile, chunks=chunks)
    user_prompt = build_user_prompt(message, history=history)

    response = model.generate(
        system_prompt,
        user_prompt,
        max_new_tokens=MAX_NEW_TOKENS,
    )

    sources = [
        {
            "doc_id": chunk.doc_id,
            "title": chunk.title,
            "source_type": chunk.source_type,
            "score": chunk.score,
        }
        for chunk in chunks
    ]

    return {
        "response": response,
        "sources": sources,
        "channel": profile.name,
        "product_id": product_id,
        "live_stock": live_stock,
        "provider_product": _snapshot_to_dict(product_snapshot),
        "history_count": len(history),
    }


def _is_stock_question(message: str) -> bool:
    text = message.lower()
    keywords = [
        "stok",
        "kac adet",
        "mevcut",
        "kalmis",
        "tukendi",
        "var mi",
    ]
    return any(keyword in text for keyword in keywords)


def _chunk_from_product_snapshot(snapshot: ProductSnapshot) -> RetrievedChunk:
    parts = [
        f"Urun ID: {snapshot.product_id}",
        f"Urun adi: {snapshot.name}" if snapshot.name else "",
        f"Aciklama: {snapshot.description}" if snapshot.description else "",
        f"Fiyat: {snapshot.price}" if snapshot.price is not None else "",
        f"Stok: {snapshot.stock}" if snapshot.stock is not None else "",
        f"Kaynak: {snapshot.source}",
    ]
    return RetrievedChunk(
        doc_id=f"provider-product-{snapshot.product_id}",
        source_type="channel_product",
        channel=snapshot.channel,
        product_id=snapshot.product_id,
        title=snapshot.name or f"Urun {snapshot.product_id}",
        content="\n".join([part for part in parts if part]),
        score=1.0,
    )


def _snapshot_to_dict(snapshot: ProductSnapshot | None) -> dict | None:
    if snapshot is None:
        return None
    return {
        "product_id": snapshot.product_id,
        "name": snapshot.name,
        "description": snapshot.description,
        "price": snapshot.price,
        "stock": snapshot.stock,
        "channel": snapshot.channel,
        "source": snapshot.source,
    }


def _conversation_to_dict(conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "channel": conversation.channel,
        "product_id": conversation.product_id,
        "marketplace": conversation.marketplace,
        "language": conversation.language,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def _message_to_dict(message: Message) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }
