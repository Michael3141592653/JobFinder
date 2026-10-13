from collections.abc import Sequence
from typing import Self, cast

import httpx
import ollama
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

from jobfinder.llm.base import InvalidLLMOutputError, LLMClient, LLMUnavailableError
from jobfinder.settings import LLMSettings


class OllamaClient(LLMClient):
    def __init__(
        self,
        url: str,
        model: str,
        context_length: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._chat_model = ChatOllama(
            base_url=url,
            model=model,
            num_ctx=context_length,  # Ollama's name for the context length
            # the first call loads the model (about 40 s)
            client_kwargs={"timeout": httpx.Timeout(10, read=600)},
            async_client_kwargs={"transport": transport} if transport else {},
        )

    @classmethod
    def from_settings(cls, llm_settings: LLMSettings) -> Self:
        return cls(llm_settings.ollama_url, llm_settings.llm_model, llm_settings.llm_context_length)

    async def generate_structured[OutputModel: BaseModel](
        self,
        messages: Sequence[BaseMessage],
        output_type: type[OutputModel],
        *,
        temperature: float | None = None,
        reasoning: bool | None = None,
    ) -> OutputModel:
        """The model doesn't see `output_type`'s schema, Ollama only enforces it: put the schema
        in the messages too, so the model knows what each field means."""
        # ChatOllama can't take `temperature` per call without replacing every option
        chat_model = self._chat_model.model_copy(
            update={"temperature": temperature, "reasoning": reasoning}
        )
        structured_model = chat_model.with_structured_output(output_type, method="json_schema")
        try:
            return cast(OutputModel, await structured_model.ainvoke(list(messages)))
        except OutputParserException as error:
            raise InvalidLLMOutputError(
                f"the model's answer isn't a valid {output_type.__name__}"
            ) from error
        except ollama.ResponseError as error:
            raise LLMUnavailableError(
                f"Ollama answered {error.status_code}: {error.error}"
            ) from error
        # ValidationError: the response isn't Ollama's
        except (ConnectionError, httpx.HTTPError, ValidationError) as error:
            raise LLMUnavailableError(f"Ollama failed: {error!r}") from error
