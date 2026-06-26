from __future__ import annotations

from dataclasses import dataclass

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER, LLM_TIMEOUT_SECONDS


@dataclass(slots=True)
class LLMResponse:
    content: str
    used_llm: bool
    provider: str
    model: str


class LLMService:
    """OpenAI-compatible chat service with mock default for tests/offline demos."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = LLM_TIMEOUT_SECONDS,
    ) -> None:
        self.provider = (provider or LLM_PROVIDER or "mock").lower()
        self.api_key = api_key if api_key is not None else LLM_API_KEY
        self.base_url = base_url if base_url is not None else LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.timeout_seconds = timeout_seconds

    @property
    def effective_model(self) -> str:
        if self.provider == "mock":
            return "mock"
        return self.model

    def chat(self, prompt: str) -> LLMResponse:
        if self.provider == "mock":
            return LLMResponse(
                content=self._mock_answer(prompt),
                used_llm=True,
                provider=self.provider,
                model=self.effective_model,
            )
        return self._openai_compatible_chat(prompt)

    def _openai_compatible_chat(self, prompt: str) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is required for real LLM providers.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed.") from exc

        kwargs = {"api_key": self.api_key, "timeout": self.timeout_seconds}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        elif self.provider == "deepseek":
            kwargs["base_url"] = "https://api.deepseek.com"

        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是严谨的企业知识库问答助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(
            content=content.strip(),
            used_llm=True,
            provider=self.provider,
            model=self.model,
        )

    @staticmethod
    def _mock_answer(prompt: str) -> str:
        lines = []
        in_context = False
        for raw_line in prompt.splitlines():
            line = raw_line.strip()
            if line.startswith("检索上下文"):
                in_context = True
                continue
            if not in_context or not line or line.startswith("[") or line.startswith("#"):
                continue
            lines.append(line.strip(" -"))
            if len(lines) >= 5:
                break
        if not lines:
            return "当前知识库中没有找到足够的信息支持该问题。建议补充相关业务文档后再查询。"
        return "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))
