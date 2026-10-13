"""Read a CV's Markdown into a ParsedCv with the LLM, one section per call: asked for every
section at once, the model mixed them up, e.g. listed the spoken languages among the skills."""

import asyncio
import json
from typing import Any

from pydantic import BaseModel, create_model

from jobfinder.cv.parsed_cv import ParsedCv
from jobfinder.llm.base import LLMClient
from jobfinder.llm.prompt import Prompt

_PARSE_SECTION_PROMPT = Prompt.load("parse_cv_section")


def _build_section_pydantic_model(section_name: str) -> type[BaseModel]:
    """A Pydantic class with only this ParsedCv field, so the LLM fills only that section."""
    field = ParsedCv.model_fields[section_name]
    field_definitions: dict[str, Any] = {section_name: (field.annotation, field)}
    return create_model(f"CvSection_{section_name}", **field_definitions)


class CvParser:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def _parse_section(self, markdown: str, section_name: str) -> Any:
        section_pydantic_model = _build_section_pydantic_model(section_name)
        messages = _PARSE_SECTION_PROMPT.build_messages(
            section=section_name,
            output_schema=json.dumps(section_pydantic_model.model_json_schema()),
            cv_markdown=markdown,
        )
        parameters = _PARSE_SECTION_PROMPT.parameters
        section = await self._llm_client.generate_structured(
            messages,
            section_pydantic_model,
            temperature=parameters.temperature,
            reasoning=parameters.reasoning,
        )
        return getattr(section, section_name)

    async def parse(self, markdown: str) -> ParsedCv:
        """Fails with LLMUnavailableError or InvalidLLMOutputError."""
        # Parallel only if Ollama has the memory (see OLLAMA_NUM_PARALLEL); else it queues them.
        section_names = list(ParsedCv.model_fields)
        sections = await asyncio.gather(
            *(self._parse_section(markdown, section_name) for section_name in section_names)
        )
        return ParsedCv(**dict(zip(section_names, sections, strict=True)))
