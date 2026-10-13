"""Load the LLM prompts: one .yaml file each in jobfinder/prompts, kept out of the Python code."""

from importlib.resources import files
from typing import Literal, Self

import yaml
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict

PROMPTS = files("jobfinder.prompts")

_MESSAGE_TYPE_BY_ROLE: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "user": HumanMessage,
}


class PromptParameters(BaseModel):
    """None keeps the model's default."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature: float | None = None
    reasoning: bool | None = None


class PromptMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: Literal["system", "user"]
    content: str


class Prompt(BaseModel):
    """Instructions in the system message, the input to read in a user message: the input can't
    pass for instructions. Bump `version` when the messages or the parameters change."""

    # extra="forbid": a misspelled key fails at load instead of being ignored
    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str
    version: int
    parameters: PromptParameters
    messages: list[PromptMessage]

    @classmethod
    def load(cls, name: str) -> Self:
        prompt_yaml = (PROMPTS / f"{name}.yaml").read_text(encoding="utf-8")
        return cls.model_validate(yaml.safe_load(prompt_yaml))

    def build_messages(self, **values: str) -> list[BaseMessage]:
        """Fill the messages' {placeholders}; each takes only the values it names."""
        return [
            _MESSAGE_TYPE_BY_ROLE[message.role](message.content.format(**values))
            for message in self.messages
        ]
