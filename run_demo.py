from __future__ import annotations

import argparse
import json

from app.config import DOCS_DIR, DEFAULT_TOP_K
from app.services.agent_service import AgentService
from app.services.rag_service import RagService


def main() -> None:
    parser = argparse.ArgumentParser(description="Enterprise RAG MVP demo")
    parser.add_argument("--build-index", action="store_true", help="Build or rebuild vector index")
    parser.add_argument("--docs-dir", default=str(DOCS_DIR), help="Knowledge document directory")
    parser.add_argument("--question", help="Question to ask the local RAG pipeline")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="TopK chunks to retrieve")
    parser.add_argument("--confirm", action="store_true", help="Confirm high-risk mock tool execution")
    args = parser.parse_args()

    if args.build_index:
        result = RagService().build_index(args.docs_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.question:
        result = AgentService().chat(args.question, top_k=args.top_k, confirm=args.confirm)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.build_index and not args.question:
        parser.print_help()


if __name__ == "__main__":
    main()
