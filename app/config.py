import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
MOCK_DATA_DIR = DATA_DIR / "mock"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
VECTOR_INDEX_PATH = VECTOR_STORE_DIR / "index.json"
PROMPT_DIR = BASE_DIR / "app" / "prompts"
LOG_DIR = BASE_DIR / "logs"
TRACE_LOG_PATH = LOG_DIR / "agent_trace.jsonl"

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 80
DEFAULT_TOP_K = 5
NO_ANSWER_TEXT = "当前知识库中没有找到足够的信息支持该问题。建议补充相关业务文档后再查询。"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hash").strip().lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5").strip()

VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "chroma").strip().lower()
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "enterprise_rag_docs").strip()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat").strip()
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
