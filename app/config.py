from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
VECTOR_INDEX_PATH = VECTOR_STORE_DIR / "index.json"
PROMPT_DIR = BASE_DIR / "app" / "prompts"

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 80
DEFAULT_TOP_K = 5
NO_ANSWER_TEXT = "当前知识库中没有找到足够的信息支持该问题。建议补充相关业务文档后再查询。"
