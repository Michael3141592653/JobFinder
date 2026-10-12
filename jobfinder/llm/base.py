from abc import ABC, abstractmethod
from collections.abc import Sequence

from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class LLMError(RuntimeError):
    pass


class LLMUnavailableError(LLMError):
    """The model can't answer: unreachable, not installed, or too slow."""


class InvalidLLMOutputError(LLMError):
    """The model answered, but not in the shape asked for."""


class LLMClient(ABC):
    """Subclasses adapt one provider and turn its failures into the errors above."""

    @abstractmethod
    async def generate_structured[OutputModel: BaseModel](
        self,
        messages: Sequence[BaseMessage],
        output_type: type[OutputModel],
        *,
        temperature: float | None = None,
        reasoning: bool | None = None,
    ) -> OutputModel:
        """Fails with LLMUnavailableError or InvalidLLMOutputError. None keeps the model's
        default."""
