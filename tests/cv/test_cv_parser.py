from collections.abc import Sequence

import pytest
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from jobfinder.cv.cv_parser import CvParser
from jobfinder.cv.parsed_cv import Experience, ParsedCv, YearMonth
from jobfinder.llm.base import LLMClient

pytestmark = pytest.mark.anyio

MARKDOWN = "## Experience\nML Engineer at Acme AI, Mar 2022 - Present"


PARSED_CV = ParsedCv(
    location="Milan, Italy",
    experiences=[
        Experience(
            title="ML Engineer",
            company="Acme AI",
            start=YearMonth(year=2022, month=3),
            end=None,
            description=None,
        )
    ],
    education=[],
    publications=[],
    skills=["Python", "PyTorch"],
    languages=["Italian (native)"],
)


class _FakeLLMClient(LLMClient):
    """Answers each section with PARSED_CV's, and keeps what it was sent and asked for."""

    def __init__(self) -> None:
        self.sent_messages: list[Sequence[BaseMessage]] = []
        self.asked_fields: list[list[str]] = []
        self.reasoning_flags: list[bool | None] = []

    async def generate_structured[OutputModel: BaseModel](
        self,
        messages: Sequence[BaseMessage],
        output_type: type[OutputModel],
        *,
        temperature: float | None = None,
        reasoning: bool | None = None,
    ) -> OutputModel:
        self.sent_messages.append(messages)
        self.asked_fields.append(list(output_type.model_fields))
        self.reasoning_flags.append(reasoning)
        return output_type.model_validate(
            PARSED_CV.model_dump(include=set(output_type.model_fields))
        )


async def test_parse_assembles_the_sections_into_a_parsed_cv():
    assert await CvParser(_FakeLLMClient()).parse(MARKDOWN) == PARSED_CV


async def test_parse_asks_for_one_section_per_call():
    fake_llm_client = _FakeLLMClient()

    await CvParser(fake_llm_client).parse(MARKDOWN)

    assert fake_llm_client.asked_fields == [[name] for name in ParsedCv.model_fields]


async def test_parse_sends_the_markdown_to_read():
    fake_llm_client = _FakeLLMClient()

    await CvParser(fake_llm_client).parse(MARKDOWN)

    assert all(MARKDOWN in messages[1].content for messages in fake_llm_client.sent_messages)


async def test_parse_turns_reasoning_off_whatever_the_model_default():
    fake_llm_client = _FakeLLMClient()

    await CvParser(fake_llm_client).parse(MARKDOWN)

    assert set(fake_llm_client.reasoning_flags) == {False}
