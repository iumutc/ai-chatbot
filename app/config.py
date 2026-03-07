import os
from dotenv import load_dotenv

load_dotenv()

MODEL_ID = os.getenv("MODEL_ID", "bigscience/bloomz-3b")
DEVICE = os.getenv("DEVICE", "cuda")
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "256"))
