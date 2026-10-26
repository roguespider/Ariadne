"""Adapter for local or hosted OpenAI-compatible chat-completions APIs."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .core import ChatMessage, ModelTurn, ToolCall


class OpenAICompatibleModel:
    """Send conversation turns to an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    def respond(self, messages: list[ChatMessage], tools: list[dict]) -> ModelTurn:
        payload: dict = {
            "model": self._model,
            "messages": [self._message_payload(message) for message in messages],
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        request = Request(
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Model endpoint returned HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Could not reach model endpoint {self._url}: {exc.reason}"
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Model endpoint returned invalid JSON.") from exc

        try:
            message = result["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Model endpoint response did not contain a chat completion."
            ) from exc

        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            try:
                function = item["function"]
                raw_arguments = function.get("arguments", "{}")
                if not isinstance(raw_arguments, str):
                    raw_arguments = json.dumps(raw_arguments)
                calls.append(
                    ToolCall(
                        id=str(item.get("id") or uuid4().hex),
                        name=str(function["name"]),
                        arguments_json=raw_arguments,
                    )
                )
            except (KeyError, TypeError) as exc:
                raise RuntimeError("Model endpoint returned a malformed tool call.") from exc

        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise RuntimeError("Model endpoint returned non-text message content.")
        if content is None and not calls:
            raise RuntimeError("Model endpoint returned neither text nor tool calls.")
        return ModelTurn(content=content, tool_calls=calls)

    @staticmethod
    def _message_payload(message: ChatMessage) -> dict:
        item: dict = {"role": message.role, "content": message.content}
        if message.tool_call_id is not None:
            item["tool_call_id"] = message.tool_call_id
        if message.name is not None:
            item["name"] = message.name
        if message.tool_calls:
            item["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": call.arguments_json,
                    },
                }
                for call in message.tool_calls
            ]
        return item
