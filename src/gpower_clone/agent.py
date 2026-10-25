"""Turkish-speaking AI agent for gpower-clone (CONTRACT.md Section 8).

The agent never calculates anything itself: Claude decides which arguments to send,
the agent forwards the call to the `power_analysis` MCP tool over a real MCP
connection, and every tool call is appended as one line to logs/agent_calls.jsonl:

{"ts": ..., "question": ..., "tool_input": {...}, "tool_output": {...}, "tokens_in": N, "tokens_out": N}
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import anyio
from mcp import Client, StdioServerParameters

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_LOG_PATH = Path("logs") / "agent_calls.jsonl"
MAX_MODEL_TURNS = 8

SYSTEM_PROMPT = """Sen klinik araştırmacılara istatistiksel güç analizi konusunda yardım eden Türkçe konuşan bir asistansın.
Elindeki tek hesap aracı `power_analysis` MCP aracıdır (gpower-clone motoru; G*Power 3.1.9.7 davranışını izler).
Şu an yalnızca `chi2-contingency` testi (kontenjans tabloları, Cohen'in w etki büyüklüğü) desteklenir.

Kurallar:
1. Hiçbir sayısal sonucu (N, güç, α, kritik değer, ncp, etki büyüklüğü) kendin hesaplama, tahmin etme ya da yuvarlayarak uydurma. Her sonuç `power_analysis` aracının çıktısından gelmelidir. Yanıtında yalnızca araç çıktısındaki sayıları kullan.
2. Araç çağırmak için gereken her alanı kullanıcıdan almalısın; varsayılan değer yoktur. Eksik bir alan varsa aracı çağırmadan önce kullanıcıya sor.
3. "Küçük/orta/büyük etki" bir kategoridir, değer değildir. Kullanıcı yalnızca kategori söylediyse Cohen (1988) eşiğini (w için küçük 0.1, orta 0.3, büyük 0.5) öner ve hesaplamadan önce onay iste; sessizce varsayma.
4. Serbestlik derecesi kontenjans tablosu için df = (satır − 1) × (sütun − 1)'dir; kullanıcı tablo boyutunu verdiyse bu dönüşümü açıkça belirt.
5. Mod seçimi: gerekli örneklem → a-priori; ulaşılan güç → post-hoc; β/α oranı → compromise; gerekli α → criterion; saptanabilir en küçük etki → sensitivity. Yalnızca o modun alanlarını gönder.
6. Araç hata JSON'u dönerse (`error`, `code`, `field`), hatayı Türkçe ve anlaşılır biçimde açıkla, sonuç uydurma.
7. Desteklenmeyen bir test istenirse bunu açıkça söyle.
8. Yalnızca kurgusal araştırma senaryolarıyla çalış; gerçek hasta verisi veya kişiyi tanımlayabilecek bilgi isteme ve kaydetme.
Yanıtlarını kısa, net ve Türkçe ver; hangi girdilerle hangi modun çalıştırıldığını belirt."""


def mcp_tool_to_claude(tool: Any) -> Dict[str, Any]:
    """Convert an MCP tool definition to a Claude tool definition."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.input_schema,
    }


def parse_tool_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def call_mcp_tool(mcp_client: Client, tool_names: set, name: str, tool_input: Dict[str, Any]) -> tuple[str, bool]:
    """Call a tool through MCP; returns (text content, is_error). Shared by all providers."""
    if name not in tool_names:
        return json.dumps({"error": f"Unknown tool '{name}'", "code": "UNSUPPORTED"}, ensure_ascii=False), True
    result = await mcp_client.call_tool(name, tool_input)
    text = "".join(block.text for block in result.content if block.type == "text")
    return text, bool(result.is_error)


class CallLogger:
    """Append one JSON line per tool call to the agent log."""

    def __init__(self, path: Path | str = DEFAULT_LOG_PATH):
        self.path = Path(path)

    def log(self, question: str, tool_input: Dict[str, Any], tool_output: Any, tokens_in: int, tokens_out: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "question": question,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class PowerAnalysisAgent:
    """Claude tool-use loop whose only tool is the MCP `power_analysis` tool.

    messages_api: an object with `async create(**kwargs)` (AsyncAnthropic().beta.messages,
    or a fake in tests). mcp_client: a connected mcp.Client.
    """

    def __init__(
        self,
        messages_api: Any,
        mcp_client: Client,
        tools: List[Any],
        logger: CallLogger,
        model: str = DEFAULT_MODEL,
    ):
        self.messages_api = messages_api
        self.mcp_client = mcp_client
        self.tool_names = {t.name for t in tools}
        self.claude_tools = [mcp_tool_to_claude(t) for t in tools]
        self.logger = logger
        self.model = model
        # Conversation history is kept across questions so follow-ups ("evet, 0.3 kullan") work.
        self.messages: List[Dict[str, Any]] = []

    async def _create(self) -> Any:
        return await self.messages_api.create(
            model=self.model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=self.claude_tools,
            messages=self.messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    async def _call_tool(self, name: str, tool_input: Dict[str, Any]) -> tuple[str, bool]:
        return await call_mcp_tool(self.mcp_client, self.tool_names, name, tool_input)

    async def ask(self, question: str) -> str:
        """Answer one user question; every tool call goes through MCP and is logged."""
        self.messages.append({"role": "user", "content": question})

        for _ in range(MAX_MODEL_TURNS):
            response = await self._create()
            # Keep the full content (thinking blocks included) in history.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "Bu isteği yanıtlayamıyorum."

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                return "".join(b.text for b in response.content if b.type == "text").strip()

            # A response's token usage is attributed to its first tool call only, so totals are not double-counted.
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
            tool_results = []
            for block in tool_uses:
                tool_input = dict(block.input or {})
                text, is_error = await self._call_tool(block.name, tool_input)
                self.logger.log(question, tool_input, parse_tool_text(text), tokens_in, tokens_out)
                tokens_in = tokens_out = 0
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error}
                )
            self.messages.append({"role": "user", "content": tool_results})

        return "Üzgünüm, bu soruyu izin verilen adım sayısı içinde yanıtlayamadım."


def mcp_server_parameters() -> StdioServerParameters:
    """Launch the gpower-clone MCP server as a stdio subprocess of this Python."""
    return StdioServerParameters(command=sys.executable, args=["-m", "gpower_clone.mcp_server"])


def describe_api_error(error: Exception) -> str | None:
    """Turkish message for Claude API / credential failures, None for anything else."""
    import anthropic

    if isinstance(error, anthropic.AuthenticationError):
        return "Kimlik doğrulama başarısız: ANTHROPIC_API_KEY geçersiz."
    if isinstance(error, anthropic.APIConnectionError):
        return "Claude API'ye bağlanılamadı; ağ bağlantısını kontrol edin."
    if isinstance(error, anthropic.APIStatusError):
        return f"Claude API hatası ({error.status_code}): {error.message}"
    if isinstance(error, TypeError) and "authentication" in str(error):
        return "Claude API kimlik bilgisi bulunamadı: ANTHROPIC_API_KEY ortam değişkenini ayarlayın."
    return None


PROVIDERS = ("anthropic", "ollama")


def resolve_model(provider: str, model: str | None) -> str:
    """Explicit model, else GPOWER_AGENT_MODEL, else the provider's default."""
    if model:
        return model
    if os.environ.get("GPOWER_AGENT_MODEL"):
        return os.environ["GPOWER_AGENT_MODEL"]
    if provider == "ollama":
        from gpower_clone.ollama_agent import DEFAULT_OLLAMA_MODEL

        return DEFAULT_OLLAMA_MODEL
    return DEFAULT_MODEL


async def run(
    questions: List[str],
    model: str,
    log_path: Path,
    provider: str = "anthropic",
    ollama_host: str | None = None,
) -> int:
    async with Client(mcp_server_parameters()) as mcp_client:
        tools = (await mcp_client.list_tools()).tools
        if provider == "ollama":
            # The anthropic package is never imported on this path, so no API key is needed.
            from gpower_clone.ollama_agent import OllamaChat, OllamaError, OllamaPowerAnalysisAgent, UnverifiedAnswerError

            agent: Any = OllamaPowerAnalysisAgent(
                chat=OllamaChat(model=model, host=ollama_host),
                mcp_client=mcp_client,
                tools=tools,
                logger=CallLogger(log_path),
            )
        else:
            from anthropic import AsyncAnthropic

            agent = PowerAnalysisAgent(
                messages_api=AsyncAnthropic().beta.messages,
                mcp_client=mcp_client,
                tools=tools,
                logger=CallLogger(log_path),
                model=model,
            )

        async def answer(question: str) -> str:
            """Returns 'ok', 'rejected' (answer withheld, conversation can go on) or 'fatal'."""
            try:
                print(await agent.ask(question))
                return "ok"
            except Exception as e:
                if provider == "ollama":
                    if isinstance(e, UnverifiedAnswerError):
                        print(str(e), file=sys.stderr)
                        return "rejected"
                    if isinstance(e, OllamaError):
                        print(str(e), file=sys.stderr)
                        return "fatal"
                    raise
                message = describe_api_error(e)
                if message is None:
                    raise
                print(message, file=sys.stderr)
                return "fatal"

        if questions:
            for question in questions:
                if await answer(question) != "ok":
                    return 1
            return 0

        print(f"gpower-clone ajanı ({provider}: {model}). Sorunuzu yazın (çıkmak için boş satır ya da 'çık').")
        while True:
            try:
                question = (await anyio.to_thread.run_sync(input, "> ")).strip()
            except EOFError:
                break
            if not question or question.lower() in {"çık", "cik", "exit", "quit"}:
                break
            if await answer(question) == "fatal":
                return 1
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpower-clone-agent", description="Türkçe güç analizi ajanı (MCP power_analysis aracını kullanır)")
    parser.add_argument("question", nargs="*", help="Tek seferlik soru; verilmezse etkileşimli mod açılır")
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=os.environ.get("GPOWER_AGENT_PROVIDER", "anthropic"),
        help="Dil modeli sağlayıcısı (varsayılan: anthropic; ortam: GPOWER_AGENT_PROVIDER)",
    )
    parser.add_argument("--model", default=None, help="Model adı (ortam: GPOWER_AGENT_MODEL; varsayılan sağlayıcıya göre)")
    parser.add_argument("--ollama-host", default=os.environ.get("OLLAMA_HOST"), help="Ollama adresi (varsayılan: http://localhost:11434)")
    parser.add_argument("--log", default=os.environ.get("GPOWER_AGENT_LOG", str(DEFAULT_LOG_PATH)))
    return parser


def main(argv: List[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = build_parser().parse_args(argv)
    model = resolve_model(args.provider, args.model)
    questions = [" ".join(args.question)] if args.question else []
    return anyio.run(run, questions, model, Path(args.log), args.provider, args.ollama_host)


if __name__ == "__main__":
    sys.exit(main())
