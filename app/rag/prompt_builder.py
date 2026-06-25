from __future__ import annotations

from pathlib import Path

from app.config import PROMPT_DIR


class RagPromptBuilder:
    def __init__(self, template_path: str | Path = PROMPT_DIR / "rag_answer_prompt.txt") -> None:
        self.template_path = Path(template_path)

    def build(self, question: str, chunks: list[dict]) -> str:
        template = self.template_path.read_text(encoding="utf-8")
        context = self.build_context(chunks)
        return template.format(question=question, context=context)

    @staticmethod
    def build_context(chunks: list[dict]) -> str:
        blocks = []
        for index, chunk in enumerate(chunks, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[{index}] source={chunk['source']} chunk_id={chunk['chunk_id']} score={chunk['score']}",
                        chunk["content"],
                    ]
                )
            )
        return "\n\n".join(blocks)
