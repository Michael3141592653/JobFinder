import json

import httpx
import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from jobfinder.llm.base import InvalidLLMOutputError, LLMUnavailableError
from jobfinder.llm.ollama import OllamaClient

pytestmark = pytest.mark.anyio

MODEL = "hf.co/bartowski/Qwen2.5-7B-Instruct-GGUF"
CONTEXT_LENGTH = 8192
MESSAGES = [SystemMessage("Find the name."), HumanMessage("I am Ada.")]


class _Person(BaseModel):
    name: str


def _answer(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": MODEL,
            "created_at": "2026-10-12T09:00:00Z",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": content},
        },
    )


ADA = _answer('{"name": "Ada"}')


class _FakeOllama:
    def __init__(self, answer: httpx.Response) -> None:
        self._answer = answer
        self.request_bodies: list[dict] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.request_bodies.append(json.loads(request.content))
        return self._answer


def _ollama_client(fake_ollama: _FakeOllama) -> OllamaClient:
    transport = httpx.MockTransport(fake_ollama.handle)
    return OllamaClient("http://ollama.test", MODEL, CONTEXT_LENGTH, transport)


async def test_generate_structured_returns_the_answer_as_the_output_type():
    ollama_client = _ollama_client(_FakeOllama(ADA))

    person = await ollama_client.generate_structured(MESSAGES, _Person)

    assert person == _Person(name="Ada")


async def test_generate_structured_sends_the_configured_model_and_context_length():
    fake_ollama = _FakeOllama(ADA)

    await _ollama_client(fake_ollama).generate_structured(MESSAGES, _Person)

    [request_body] = fake_ollama.request_bodies
    assert (request_body["model"], request_body["options"]["num_ctx"]) == (MODEL, CONTEXT_LENGTH)


async def test_generate_structured_asks_ollama_to_enforce_the_output_schema():
    fake_ollama = _FakeOllama(ADA)

    await _ollama_client(fake_ollama).generate_structured(MESSAGES, _Person)

    [request_body] = fake_ollama.request_bodies
    assert request_body["format"] == _Person.model_json_schema()


async def test_generate_structured_with_temperature_and_reasoning_sends_them():
    fake_ollama = _FakeOllama(ADA)

    await _ollama_client(fake_ollama).generate_structured(
        MESSAGES, _Person, temperature=0, reasoning=False
    )

    [request_body] = fake_ollama.request_bodies
    assert (request_body["options"]["temperature"], request_body["think"]) == (0, False)


async def test_generate_structured_without_temperature_and_reasoning_leaves_the_model_defaults():
    fake_ollama = _FakeOllama(ADA)

    await _ollama_client(fake_ollama).generate_structured(MESSAGES, _Person)

    [request_body] = fake_ollama.request_bodies
    assert "temperature" not in request_body["options"]
    assert request_body.get("think") is None


async def test_generate_structured_settings_of_one_call_do_not_carry_over_to_the_next():
    fake_ollama = _FakeOllama(ADA)
    ollama_client = _ollama_client(fake_ollama)
    await ollama_client.generate_structured(MESSAGES, _Person, temperature=0, reasoning=False)

    await ollama_client.generate_structured(MESSAGES, _Person)

    second_request_body = fake_ollama.request_bodies[1]
    assert "temperature" not in second_request_body["options"]
    assert second_request_body.get("think") is None


async def test_generate_structured_when_ollama_refuses_raises_unavailable_with_its_reason():
    answer = httpx.Response(404, json={"error": f"model '{MODEL}' not found"})
    ollama_client = _ollama_client(_FakeOllama(answer))

    with pytest.raises(LLMUnavailableError, match="not found"):
        await ollama_client.generate_structured(MESSAGES, _Person)


@pytest.mark.parametrize(
    ("answer", "expected_error"),
    [
        pytest.param(httpx.Response(500), LLMUnavailableError, id="server-error"),
        pytest.param(httpx.Response(200, json={}), LLMUnavailableError, id="not-ollama-response"),
        pytest.param(_answer("{}"), InvalidLLMOutputError, id="wrong-shape"),
        pytest.param(_answer("not json"), InvalidLLMOutputError, id="not-json"),
    ],
)
async def test_generate_structured_tells_unavailable_from_invalid_output(answer, expected_error):
    ollama_client = _ollama_client(_FakeOllama(answer))

    with pytest.raises(expected_error):
        await ollama_client.generate_structured(MESSAGES, _Person)


async def test_generate_structured_when_ollama_is_unreachable_raises_unavailable():
    def refuse_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(refuse_connection)
    ollama_client = OllamaClient("http://ollama.test", MODEL, CONTEXT_LENGTH, transport)

    with pytest.raises(LLMUnavailableError, match="Ollama failed"):
        await ollama_client.generate_structured(MESSAGES, _Person)
