import os
import json
from collections.abc import AsyncIterator
from collections.abc import Iterator

import httpx


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "DOUBAO_API_KEY",
        base_url_env: str = "DOUBAO_BASE_URL",
        model_env: str = "DOUBAO_MODEL",
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv(api_key_env) or os.getenv("ARK_API_KEY", "")
        self.base_url = (base_url or os.getenv(base_url_env) or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        self.model = model or os.getenv(model_env) or "doubao-seed-2-0-lite-260428"
        self.timeout = timeout or float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        payload = self._payload(messages, temperature=temperature, stream=False)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def stream_chat_sync(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        payload = self._payload(messages, temperature=temperature, stream=True)
        with httpx.Client(timeout=self._stream_timeout()) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    chunk = parse_openai_stream_line(line)
                    if chunk:
                        yield chunk

    async def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        payload = self._payload(messages, temperature=temperature, stream=False)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature=temperature, stream=True)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    chunk = parse_openai_stream_line(line)
                    if chunk:
                        yield chunk

    def _payload(self, messages: list[dict[str, str]], *, temperature: float, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("DOUBAO_API_KEY or ARK_API_KEY is required")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _stream_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self.timeout, connect=min(self.timeout, 10.0), read=self.timeout)


def parse_openai_stream_line(line: str) -> str:
    if not line.startswith("data: "):
        return ""
    data = line.removeprefix("data: ").strip()
    if not data or data == "[DONE]":
        return ""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return ""
    choice = (payload.get("choices") or [{}])[0]
    delta = choice.get("delta") or {}
    if isinstance(delta, dict) and delta.get("content"):
        return str(delta["content"])
    message = choice.get("message") or {}
    if isinstance(message, dict) and message.get("content"):
        return str(message["content"])
    return ""
