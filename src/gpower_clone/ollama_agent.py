"""Ollama (local model) provider for the gpower-clone agent.

Same contract as the Claude agent: the model never calculates; every number comes
from the MCP `power_analysis` tool, and every tool call is logged in the same
logs/agent_calls.jsonl format. On top of that, because small local models often
write a tool call as plain text or answer from memory, a final answer is rejected
with an explicit error when:
- it contains a tool call written as text instead of a structured `tool_calls` entry, or
- no tool was called for the question and it contains numbers the conversation does not justify.

Talks to the Ollama REST API (`POST /api/chat`) with httpx2, which the MCP SDK already
depends on, so no extra package and no ANTHROPIC_API_KEY are needed.
"""

import json
import re
from typing import Any, Awaitable, Callable, Dict, List
from urllib.parse import urlparse

import httpx2
from mcp import Client

from gpower_clone.agent import MAX_MODEL_TURNS, SYSTEM_PROMPT, CallLogger, call_mcp_tool, parse_tool_text

DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_PORT = 11434

NO_TOOL_CALL_ERROR = "HATA: Model yapılandırılmış araç çağrısı üretmedi; hesap sonucu gösterilmiyor."

# A tool call written into the answer text instead of the structured tool_calls field.
TEXTUAL_TOOL_CALL = re.compile(r'"name"\s*:\s*"power_analysis"|\bpower_analysis\s*\(|"function"\s*:\s*\{')
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

ChatFn = Callable[[List[Dict[str, Any]], List[Dict[str, Any]]], Awaitable[Dict[str, Any]]]


class OllamaError(Exception):
    """Ollama is unreachable, the model is missing, or the server returned an error."""


class UnverifiedAnswerError(Exception):
    """The model answered without a structured MCP tool call; the answer is withheld."""

    def __init__(self, reason: str):
        super().__init__(f"{NO_TOOL_CALL_ERROR} ({reason})")
        self.reason = reason


def normalize_host(host: str | None) -> str:
    """Accept OLLAMA_HOST forms such as '127.0.0.1', '0.0.0.0:11434' or 'http://host:port'."""
    host = (host or DEFAULT_OLLAMA_HOST).strip().rstrip("/")
    if "://" not in host:
        host = "http://" + host
    parsed = urlparse(host)
    hostname = parsed.hostname or "localhost"
    if hostname == "0.0.0.0":
        hostname = "127.0.0.1"
    port = parsed.port or DEFAULT_OLLAMA_PORT
    return f"{parsed.scheme}://{hostname}:{port}"


def mcp_tool_to_ollama(tool: Any) -> Dict[str, Any]:
    """Convert an MCP tool definition to an Ollama/OpenAI-style function tool."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


class OllamaChat:
    """Minimal async client for Ollama's /api/chat endpoint."""

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        host: str | None = None,
        timeout: float = 600.0,
        transport: Any = None,
    ):
        self.model = model
        self.host = normalize_host(host)
        self.timeout = timeout
        self.transport = transport

    async def __call__(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": 0},
        }
        async with httpx2.AsyncClient(base_url=self.host, timeout=self.timeout, transport=self.transport) as client:
            try:
                response = await client.post("/api/chat", json=payload)
            except httpx2.ConnectError:
                raise OllamaError(
                    f"Ollama sunucusuna ulaşılamadı ({self.host}). Ollama'yı kurup `ollama serve` ile başlatın."
                )
            except httpx2.TimeoutException:
                raise OllamaError(f"Ollama {self.timeout:.0f} saniye içinde yanıt vermedi (zaman aşımı).")

        if response.status_code == 404:
            raise OllamaError(f"Ollama modeli bulunamadı: '{self.model}'. İndirmek için: ollama pull {self.model}")
        if response.status_code >= 400:
            raise OllamaError(f"Ollama hatası ({response.status_code}): {response.text[:300]}")
        return response.json()


def _numbers(text: str) -> set:
    return {round(float(n.replace(",", ".")), 10) for n in NUMBER.findall(text)}


class OllamaPowerAnalysisAgent:
    """Tool-calling loop over a local Ollama model whose only tool is MCP `power_analysis`."""

    def __init__(self, chat: ChatFn, mcp_client: Client, tools: List[Any], logger: CallLogger):
        self.chat = chat
        self.mcp_client = mcp_client
        self.tool_names = {t.name for t in tools}
        self.ollama_tools = [mcp_tool_to_ollama(t) for t in tools]
        self.logger = logger
        # Conversation history is kept across questions so follow-ups work.
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _justified_numbers(self) -> set:
        """Numbers the model may repeat without a new tool call: the user's, the prompt's and earlier tool outputs."""
        allowed: set = set()
        for message in self.messages:
            if message["role"] in {"system", "user", "tool"}:
                allowed |= _numbers(message["content"])
        return allowed

    def _check_answer(self, text: str, called_tool: bool) -> None:
        if TEXTUAL_TOOL_CALL.search(text):
            raise UnverifiedAnswerError("araç çağrısı metin olarak yazıldı, yapılandırılmış tool_calls alanı yok")
        if called_tool:
            return
        allowed = self._justified_numbers()
        unjustified = {n for n in _numbers(text) if n not in allowed and round(n / 100, 10) not in allowed}
        if unjustified:
            raise UnverifiedAnswerError("araç çağrılmadan sayısal sonuç üretildi")

    async def ask(self, question: str) -> str:
        """Answer one question; every number must come from an MCP tool call made through Ollama tool_calls."""
        self.messages.append({"role": "user", "content": question})
        tool_outputs: List[str] = []

        for _ in range(MAX_MODEL_TURNS):
            data = await self.chat(self.messages, self.ollama_tools)
            message = data.get("message") or {}
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            assistant: Dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant["tool_calls"] = tool_calls
            self.messages.append(assistant)

            if not tool_calls:
                text = content.strip()
                try:
                    self._check_answer(text, called_tool=bool(tool_outputs))
                except UnverifiedAnswerError:
                    # Do not leave the unverified answer in the history the model sees next time.
                    self.messages[-1] = {"role": "assistant", "content": NO_TOOL_CALL_ERROR}
                    raise
                if tool_outputs:
                    text += "\n\nMCP power_analysis çıktısı:\n" + "\n".join(tool_outputs)
                return text

            # Usage of one model response is attributed to its first tool call only (same rule as the Claude agent).
            tokens_in = int(data.get("prompt_eval_count") or 0)
            tokens_out = int(data.get("eval_count") or 0)
            for call in tool_calls:
                function = call.get("function") or {}
                name = function.get("name", "")
                arguments = function.get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                tool_input = dict(arguments) if isinstance(arguments, dict) else {}

                text, _is_error = await call_mcp_tool(self.mcp_client, self.tool_names, name, tool_input)
                self.logger.log(question, tool_input, parse_tool_text(text), tokens_in, tokens_out)
                tokens_in = tokens_out = 0
                tool_outputs.append(text)
                self.messages.append({"role": "tool", "content": text, "tool_name": name})

        return "Üzgünüm, bu soruyu izin verilen adım sayısı içinde yanıtlayamadım."
