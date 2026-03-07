from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

from app.config import MODEL_ID, DEVICE, MAX_NEW_TOKENS
from app.llm import LocalLLM

SYSTEM_PROMPT_TR = (
    "Sen bir e-ticaret müşteri destek asistanısın.\n"
    "- Yalnızca kullanıcı sorusuna cevap ver.\n"
    "- Cevap Türkçe olsun.\n"
    "- 1-3 kısa cümleyle yanıtla.\n"
    "- Emin olmadığın hiçbir şeyi uydurma. Bilgin yoksa: "
    "\"Bu bilgi bende yok. Şu bilgiyi paylaşır mısınız: ...?\" diye sor.\n"
    "- Asla 'Human:' 'Assistant:' gibi etiketler yazma.\n"
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading model...")
    app.state.llm = LocalLLM(model_id=MODEL_ID, device=DEVICE)
    print("Model loaded.")
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE
    }


@app.post("/chat")
def chat(req: ChatRequest):
    model = app.state.llm

    response = model.generate(
        SYSTEM_PROMPT_TR,
        req.message,
        max_new_tokens=MAX_NEW_TOKENS
    )

    return {"response": response}
