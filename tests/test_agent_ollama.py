"""Ollama provider tests: scripted fake model + real MCP server, HTTP layer via MockTransport. No network."""

import json
import subprocess
import sys
from datetime import datetime

import anyio
import httpx2
import pytest
from mcp import Client

from gpower_clone.agent import DEFAULT_MODEL, CallLogger, build_parser, mcp_server_parameters, resolve_model
from gpower_clone.mcp_server import create_server
from gpower_clone.ollama_agent import (
    DEFAULT_OLLAMA_MODEL,
    NO_TOOL_CALL_ERROR,
    OllamaChat,
    OllamaError,
    OllamaPowerAnalysisAgent,
    UnverifiedAnswerError,
    normalize_host,
)

A_PRIORI_INPUT = {"test": "chi2-contingency", "mode": "a-priori", "w": 0.3, "alpha": 0.05, "power": 0.95, "df": 5}
QUESTION = "Kurgusal bir çalışmada w=0.3, alpha=0.05, power=0.95 ve df=5 için kaç katılımcı gerekir?"
LOG_KEYS = {"ts", "question", "tool_input", "tool_output", "tokens_in", "tokens_out"}


def tool_call_reply(*inputs, name="power_analysis", prompt_eval_count=210, eval_count=35):
    return {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": name, "arguments": args}} for args in inputs],
        },
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
    }


def text_reply(text):
    return {"message": {"role": "assistant", "content": text}, "prompt_eval_count": 300, "eval_count": 25}


class FakeChat:
    """Stands in for OllamaChat. Each script step receives the message history."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    async def __call__(self, messages, tools):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        return self.steps.pop(0)(messages)


def last_tool_output(messages):
    return json.loads(messages[-1]["content"])


def answer_from_tool(messages):
    result = last_tool_output(messages)
    if "error" in result:
        return text_reply(f"Hata kodu: {result['code']}")
    return text_reply(f"Gerekli toplam örneklem: {result['n_total']}")


def make_agent_runner(fake, log_path, server=None):
    """Return an async function that runs several questions on one agent (history kept)."""

    async def _run(questions):
        async with Client(server or create_server()) as mcp_client:
            tools = (await mcp_client.list_tools()).tools
            agent = OllamaPowerAnalysisAgent(fake, mcp_client, tools, CallLogger(log_path))
            answers = []
            for q in questions:
                try:
                    answers.append(await agent.ask(q))
                except UnverifiedAnswerError as e:
                    answers.append(e)
            return answers, agent

    return _run


def ask(fake, question, log_path, server=None):
    answers, agent = anyio.run(make_agent_runner(fake, log_path, server), [question])
    return answers[0], agent


def read_log(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# --- Agent loop -----------------------------------------------------------------------------


def test_ollama_agent_calls_mcp_and_logs_220(tmp_path):
    log_path = tmp_path / "logs" / "agent_calls.jsonl"
    fake = FakeChat([lambda m: tool_call_reply(A_PRIORI_INPUT), answer_from_tool])

    answer, _ = ask(fake, QUESTION, log_path)

    assert answer.startswith("Gerekli toplam örneklem: 220")
    # The raw MCP output is always shown under the model's answer
    assert "MCP power_analysis çıktısı:" in answer
    assert '"n_total": 220' in answer
    rec = read_log(log_path)[0]
    assert set(rec) == LOG_KEYS
    assert rec["question"] == QUESTION
    assert rec["tool_input"] == A_PRIORI_INPUT
    assert rec["tool_output"]["n_total"] == 220
    assert abs(rec["tool_output"]["actual_power"] - 0.9502155) < 1e-6
    assert (rec["tokens_in"], rec["tokens_out"]) == (210, 35)
    assert datetime.fromisoformat(rec["ts"]).tzinfo is not None


def test_ollama_agent_sends_mcp_tool_as_function(tmp_path):
    fake = FakeChat([lambda m: text_reply("Hangi df değerini kullanalım?")])
    ask(fake, "w=0.3 için güç analizi yap", tmp_path / "log.jsonl")
    call = fake.calls[0]
    assert [t["function"]["name"] for t in call["tools"]] == ["power_analysis"]
    assert call["tools"][0]["type"] == "function"
    assert call["tools"][0]["function"]["parameters"]["required"] == ["test", "mode"]
    assert call["messages"][0]["role"] == "system"
    assert "power_analysis" in call["messages"][0]["content"]


def test_ollama_tool_result_is_sent_back_as_tool_message(tmp_path):
    fake = FakeChat([lambda m: tool_call_reply(A_PRIORI_INPUT), answer_from_tool])
    ask(fake, QUESTION, tmp_path / "log.jsonl")
    tool_msg = fake.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_name"] == "power_analysis"
    assert json.loads(tool_msg["content"])["n_total"] == 220


def test_ollama_arguments_as_json_string(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeChat([lambda m: tool_call_reply(json.dumps(A_PRIORI_INPUT)), answer_from_tool])
    answer, _ = ask(fake, QUESTION, log_path)
    assert answer.startswith("Gerekli toplam örneklem: 220")
    assert read_log(log_path)[0]["tool_input"] == A_PRIORI_INPUT


def test_ollama_tool_error_is_logged(tmp_path):
    log_path = tmp_path / "log.jsonl"
    bad = {**A_PRIORI_INPUT, "alpha": 1.5}
    fake = FakeChat([lambda m: tool_call_reply(bad), answer_from_tool])
    answer, _ = ask(fake, "Kurgusal: alfa 1.5", log_path)
    assert answer.startswith("Hata kodu: OUT_OF_RANGE")
    rec = read_log(log_path)[0]
    assert rec["tool_output"]["code"] == "OUT_OF_RANGE"
    assert rec["tool_output"]["field"] == "alpha"


def test_ollama_parallel_calls_tokens_attributed_once(tmp_path):
    log_path = tmp_path / "log.jsonl"
    post_hoc = {"test": "chi2-contingency", "mode": "post-hoc", "w": 0.3, "alpha": 0.05, "n_total": 100, "df": 5}
    fake = FakeChat([
        lambda m: tool_call_reply(A_PRIORI_INPUT, post_hoc, prompt_eval_count=400, eval_count=80),
        lambda m: text_reply("İki analiz tamamlandı."),
    ])
    ask(fake, "İki analiz", log_path)
    records = read_log(log_path)
    assert [r["tool_input"]["mode"] for r in records] == ["a-priori", "post-hoc"]
    assert [(r["tokens_in"], r["tokens_out"]) for r in records] == [(400, 80), (0, 0)]


def test_ollama_unknown_tool_name_rejected_by_agent(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeChat([lambda m: tool_call_reply(A_PRIORI_INPUT, name="calculator"), lambda m: text_reply("Araç bulunamadı.")])
    ask(fake, "soru", log_path)
    assert read_log(log_path)[0]["tool_output"]["code"] == "UNSUPPORTED"


# --- Guard against made-up results ----------------------------------------------------------


def test_textual_tool_call_is_not_executed(tmp_path):
    log_path = tmp_path / "log.jsonl"
    textual = '{"name": "power_analysis", "arguments": ' + json.dumps(A_PRIORI_INPUT) + "}"
    fake = FakeChat([lambda m: text_reply(textual)])

    result, agent = ask(fake, QUESTION, log_path)

    assert isinstance(result, UnverifiedAnswerError)
    assert str(result).startswith(NO_TOOL_CALL_ERROR)
    assert not log_path.exists()  # nothing was executed or logged
    assert agent.messages[-1] == {"role": "assistant", "content": NO_TOOL_CALL_ERROR}


def test_numeric_answer_without_tool_call_is_rejected(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeChat([lambda m: text_reply("Bu parametrelerle yaklaşık 220 katılımcı gerekir.")])
    result, _ = ask(fake, QUESTION, log_path)
    assert isinstance(result, UnverifiedAnswerError)
    assert "araç çağrılmadan" in result.reason
    assert not log_path.exists()


def test_clarifying_question_with_user_numbers_passes(tmp_path):
    fake = FakeChat([lambda m: text_reply("w=0.3 ve alfa 0.05 verdiniz; güç (%95 mi?) ve df değerini belirtir misiniz?")])
    answer, _ = ask(fake, "w=0.3, alfa 0.05, güç 0.95 ile örneklem hesapla", tmp_path / "log.jsonl")
    assert answer.startswith("w=0.3 ve alfa 0.05 verdiniz")


def test_cohen_threshold_suggestion_passes(tmp_path):
    fake = FakeChat([lambda m: text_reply("'Orta etki' için Cohen eşiği w = 0.3'tür. Bu değeri kullanmamı onaylıyor musunuz?")])
    answer, _ = ask(fake, "Orta etki bekliyoruz, kaç kişi gerekir?", tmp_path / "log.jsonl")
    assert "onaylıyor musunuz" in answer


def test_follow_up_may_repeat_earlier_tool_output(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeChat([
        lambda m: tool_call_reply(A_PRIORI_INPUT),
        answer_from_tool,
        lambda m: text_reply("Önceki hesapta gerekli örneklem 220 idi."),
    ])
    answers, _ = anyio.run(make_agent_runner(fake, log_path), [QUESTION, "N neydi?"])
    assert answers[1] == "Önceki hesapta gerekli örneklem 220 idi."
    assert len(read_log(log_path)) == 1


# --- HTTP layer (MockTransport) --------------------------------------------------------------


def run_chat(handler, model=DEFAULT_OLLAMA_MODEL, host=None):
    chat = OllamaChat(model=model, host=host, transport=httpx2.MockTransport(handler))
    return anyio.run(chat, [{"role": "user", "content": "x"}], [{"type": "function", "function": {"name": "power_analysis"}}])


def test_ollama_chat_request_body_and_response():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json=text_reply("merhaba"))

    data = run_chat(handler, host="127.0.0.1:11500")
    assert data["message"]["content"] == "merhaba"
    assert seen["url"] == "http://127.0.0.1:11500/api/chat"
    body = seen["body"]
    assert body["model"] == "qwen2.5:7b"
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0}
    assert body["tools"][0]["function"]["name"] == "power_analysis"


def test_ollama_chat_unreachable_server():
    def handler(request):
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(OllamaError, match="ollama serve"):
        run_chat(handler)


def test_ollama_chat_missing_model():
    def handler(request):
        return httpx2.Response(404, json={"error": "model 'qwen2.5:7b' not found, try pulling it first"})

    with pytest.raises(OllamaError, match=r"ollama pull qwen2\.5:7b"):
        run_chat(handler)


def test_ollama_chat_server_error():
    def handler(request):
        return httpx2.Response(500, text="boom")

    with pytest.raises(OllamaError, match="500"):
        run_chat(handler)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "http://localhost:11434"),
        ("127.0.0.1", "http://127.0.0.1:11434"),
        ("0.0.0.0:11434", "http://127.0.0.1:11434"),
        ("http://gpu-box:8080/", "http://gpu-box:8080"),
    ],
)
def test_normalize_host(raw, expected):
    assert normalize_host(raw) == expected


# --- Configuration / CLI --------------------------------------------------------------------


def test_default_provider_is_anthropic(monkeypatch):
    monkeypatch.delenv("GPOWER_AGENT_PROVIDER", raising=False)
    monkeypatch.delenv("GPOWER_AGENT_MODEL", raising=False)
    args = build_parser().parse_args(["soru"])
    assert args.provider == "anthropic"
    assert resolve_model(args.provider, args.model) == DEFAULT_MODEL == "claude-opus-5-5"


def test_provider_and_model_configuration(monkeypatch):
    monkeypatch.delenv("GPOWER_AGENT_MODEL", raising=False)
    monkeypatch.setenv("GPOWER_AGENT_PROVIDER", "ollama")
    args = build_parser().parse_args([])
    assert args.provider == "ollama"
    assert resolve_model("ollama", None) == "qwen2.5:7b"
    assert resolve_model("ollama", "llama3.1:8b") == "llama3.1:8b"
    monkeypatch.setenv("GPOWER_AGENT_MODEL", "qwen2.5:3b")
    assert resolve_model("ollama", None) == "qwen2.5:3b"


def test_cli_ollama_needs_no_anthropic_key(tmp_path):
    """Run the agent CLI with provider=ollama, no API key and a closed port: clear Ollama error, anthropic never imported."""
    code = (
        "import sys; from gpower_clone.agent import main; "
        "rc = main(['--provider', 'ollama', '--ollama-host', 'http://127.0.0.1:9', '--log', sys.argv[1], 'soru']); "
        "print('ANTHROPIC_IMPORTED=' + str('anthropic' in sys.modules)); sys.exit(rc)"
    )
    env = {k: v for k, v in __import__("os").environ.items() if not k.startswith("ANTHROPIC")}
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path / "log.jsonl")],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=120,
    )
    assert proc.returncode == 1
    assert "Ollama sunucusuna ulaşılamadı" in proc.stderr
    assert "ANTHROPIC_IMPORTED=False" in proc.stdout
    assert "ANTHROPIC_API_KEY" not in proc.stderr


def test_ollama_agent_over_stdio_subprocess(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeChat([lambda m: tool_call_reply(A_PRIORI_INPUT), answer_from_tool])
    answer, _ = ask(fake, QUESTION, log_path, server=mcp_server_parameters())
    assert answer.startswith("Gerekli toplam örneklem: 220")
    assert read_log(log_path)[0]["tool_output"]["n_total"] == 220
