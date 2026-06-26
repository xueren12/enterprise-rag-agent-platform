from app.config import DOCS_DIR
from app.rag.embedding_service import HashEmbeddingProvider
from app.rag.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.services.rag_service import RagService


EVAL_CASES = [
    {
        "name": "order_refund_flow",
        "question": "订单退款流程是什么？",
        "expected_source": "order_refund_guide.md",
        "expected_keywords": ["退款", "订单"],
        "should_refuse": False,
    },
    {
        "name": "error_code_e1001",
        "question": "错误码 E1001 是什么意思？",
        "expected_source": "error_code_manual.md",
        "expected_keywords": ["E1001", "错误码"],
        "should_refuse": False,
    },
    {
        "name": "user_u1001",
        "question": "查询用户 U1001 的账号状态。",
        "expected_source": "api_manual.md",
        "expected_keywords": ["U1001", "用户"],
        "should_refuse": False,
    },
    {
        "name": "mars_reimbursement",
        "question": "火星基地报销制度是什么？",
        "expected_source": None,
        "expected_keywords": [],
        "should_refuse": True,
    },
]


def test_minimal_rag_eval_set(tmp_path):
    rag = RagService(
        vector_store=VectorStoreService(
            index_path=tmp_path / "index.json",
            embedding_provider=HashEmbeddingProvider(),
            vector_store_type="local",
        ),
        llm_service=LLMService(provider="mock"),
    )
    rag.build_index(DOCS_DIR)

    for case in EVAL_CASES:
        result = rag.answer(case["question"], top_k=5)

        if case["should_refuse"]:
            assert result["status"] == "no_answer", case["name"]
            assert result["citations"] == [], case["name"]
            continue

        sources = {chunk["source"] for chunk in result["retrieved_chunks"][:3]}
        answer_and_context = result["answer"] + "\n" + "\n".join(
            chunk["content"] for chunk in result["retrieved_chunks"][:3]
        )

        assert result["status"] == "success", case["name"]
        assert case["expected_source"] in sources, case["name"]
        assert any(keyword in answer_and_context for keyword in case["expected_keywords"]), case["name"]
        assert result["citations"], case["name"]
