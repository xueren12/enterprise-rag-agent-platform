from __future__ import annotations

import argparse
import json

from app.config import DOCS_DIR, DEFAULT_TOP_K
from app.services.rag_service import RagService


def main() -> None:
    parser = argparse.ArgumentParser(description="Enterprise RAG MVP demo")
    parser.add_argument("--build-index", action="store_true", help="Build or rebuild vector index")
    parser.add_argument("--docs-dir", default=str(DOCS_DIR), help="Knowledge document directory")
    parser.add_argument("--question", help="Question to ask the local RAG pipeline")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="TopK chunks to retrieve")
    args = parser.parse_args()

    service = RagService()
    if args.build_index:
        result = service.build_index(args.docs_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.question:
        result = service.answer(args.question, top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.build_index and not args.question:
        parser.print_help()


if __name__ == "__main__":
    main()
