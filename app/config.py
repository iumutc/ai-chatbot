import os
from dotenv import load_dotenv

load_dotenv()

MODEL_ID = os.getenv("MODEL_ID", "bigscience/bloomz-3b")
DEVICE = os.getenv("DEVICE", "cuda")
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "256"))
CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "8"))
CHAT_DB_PATH = os.getenv("CHAT_DB_PATH", "app/data/chat.db")

RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.15"))
RAG_INDEX_PATH = os.getenv("RAG_INDEX_PATH", "app/data/rag_index.json")
RAG_KB_PATH = os.getenv("RAG_KB_PATH", "app/data/knowledge_base.json")
RAG_EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

CHANNEL_DATA_PROVIDER = os.getenv("CHANNEL_DATA_PROVIDER", "mock").lower()

ENTEGRA_ENABLED = os.getenv("ENTEGRA_ENABLED", "false").lower() == "true"
ENTEGRA_BASE_URL = os.getenv("ENTEGRA_BASE_URL", "")
ENTEGRA_PRODUCTS_ENDPOINT = os.getenv("ENTEGRA_PRODUCTS_ENDPOINT", "/product/page={page}/")
ENTEGRA_STOCK_ENDPOINT = os.getenv("ENTEGRA_STOCK_ENDPOINT", "")
ENTEGRA_TIMEOUT_SEC = int(os.getenv("ENTEGRA_TIMEOUT_SEC", "15"))
ENTEGRA_MAX_PAGES = int(os.getenv("ENTEGRA_MAX_PAGES", "50"))

ENTEGRA_AUTH_TYPE = os.getenv("ENTEGRA_AUTH_TYPE", "jwt")
ENTEGRA_AUTH_ENDPOINT = os.getenv("ENTEGRA_AUTH_ENDPOINT", "/api/user/token/obtain/")
ENTEGRA_USERNAME = os.getenv("ENTEGRA_USERNAME", "")
ENTEGRA_PASSWORD = os.getenv("ENTEGRA_PASSWORD", "")
ENTEGRA_TOKEN = os.getenv("ENTEGRA_TOKEN", "")
ENTEGRA_API_KEY = os.getenv("ENTEGRA_API_KEY", "")
ENTEGRA_API_SECRET = os.getenv("ENTEGRA_API_SECRET", "")
ENTEGRA_API_KEY_HEADER = os.getenv("ENTEGRA_API_KEY_HEADER", "X-API-KEY")
ENTEGRA_API_SECRET_HEADER = os.getenv("ENTEGRA_API_SECRET_HEADER", "X-API-SECRET")

ENTEGRA_STOCK_CACHE_PATH = os.getenv("ENTEGRA_STOCK_CACHE_PATH", "app/data/stock_cache.json")
