import pytest

from app.config import DOCS_DIR
from app.rag.document_loader import Document
from app.rag.embedding_service import HashEmbeddingProvider, SentenceTransformerEmbeddingProvider
from app.rag.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.services.rag_service import RagService


class FailingLLMService:
    def chat(self, prompt: str):
        raise RuntimeError("llm failed")


def test_hash_embedding_provider_is_available_for_tests():
    provider = HashEmbeddingProvider()
    vector = provider.embed("订单退款流程")

    assert provider.name == "hash"
    assert len(vector) == 512
    assert any(value != 0 for value in vector)


def test_sentence_transformer_provider_can_be_initialized_without_download():
    provider = SentenceTransformerEmbeddingProvider("BAAI/bge-small-zh-v1.5")

    assert provider.name == "sentence_transformer"
    assert provider.model_name == "BAAI/bge-small-zh-v1.5"


def test_chroma_vector_store_result_format_with_local_fallback(tmp_path):
    provider = HashEmbeddingProvider()
    vector_store = VectorStoreService(
        index_path=tmp_path / "index.json",
        embedding_provider=provider,
        vector_store_type="chroma",
    )
    docs = [
        Document(
            content="订单退款状态为 processing，需要同步退款状态。",
            metadata={
                "source": "mock.md",
                "title": "Mock",
                "chunk_id": "mock_001",
                "start_index": 0,
                "end_index": 20,
            },
        )
    ]

    vector_store.build_index(docs)
    results = vector_store.similarity_search("订单退款状态", top_k=1)

    assert results
    assert {"content", "source", "title", "chunk_id", "score"}.issubset(results[0])
    assert vector_store.vector_store_type in {"chroma", "local_fallback", "local"}


def test_mock_llm_generates_answer():
    rag = RagService(
        vector_store=VectorStoreService(index_path=__import__("tempfile").NamedTemporaryFile().name),
        llm_service=LLMService(provider="mock"),
    )
    rag.build_index(DOCS_DIR)

    result = rag.answer("订单退款流程是什么？")

    assert result["status"] == "success"
    assert result["used_llm"] is True
    assert result["answer"]
    assert result["citations"]


def test_llm_failure_falls_back_to_extractive_answer(tmp_path):
    rag = RagService(
        vector_store=VectorStoreService(index_path=tmp_path / "index.json"),
        llm_service=FailingLLMService(),
    )
    rag.build_index(DOCS_DIR)

    result = rag.answer("订单退款流程是什么？")

    assert result["status"] == "success"
    assert result["used_llm"] is False
    assert result["answer"]


def test_no_context_returns_refusal(tmp_path):
    rag = RagService(
        vector_store=VectorStoreService(index_path=tmp_path / "index.json"),
        llm_service=LLMService(provider="mock"),
    )
    rag.build_index(DOCS_DIR)

    result = rag.answer("火星基地报销制度是什么？")

    assert result["status"] == "no_answer"
    assert result["used_llm"] is False
    assert result["citations"] == []


def test_agent_chat_returns_real_rag_metadata():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    client.post("/knowledge/index", json={"docs_dir": str(DOCS_DIR)})
    response = client.post("/agent/chat", json={"question": "订单退款流程是什么？"})
    payload = response.json()

    assert response.status_code == 200
    assert "used_llm" in payload
    assert "embedding_provider" in payload
    assert "vector_store_type" in payload
