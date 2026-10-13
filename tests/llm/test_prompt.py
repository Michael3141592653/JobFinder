import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from jobfinder.llm.prompt import Prompt

PROMPT = Prompt.model_validate(
    {
        "description": "Find a person's name.",
        "version": 1,
        "parameters": {"temperature": 0},
        "messages": [
            {"role": "system", "content": "Find the {field}."},
            {"role": "user", "content": "<cv>{cv_markdown}</cv>"},
        ],
    }
)


def test_build_messages_turns_each_role_into_its_message_type():
    messages = PROMPT.build_messages(field="name", cv_markdown="I am Ada.")

    assert messages == [
        SystemMessage("Find the name."),
        HumanMessage("<cv>I am Ada.</cv>"),
    ]


def test_build_messages_keeps_braces_in_the_values():
    messages = PROMPT.build_messages(field="name", cv_markdown="Skills: {Python}")

    assert messages[-1].content == "<cv>Skills: {Python}</cv>"


def test_unset_parameters_keep_the_model_default():
    assert PROMPT.parameters.reasoning is None


def test_misspelled_parameter_fails():
    with pytest.raises(ValidationError):
        Prompt.model_validate(PROMPT.model_dump() | {"parameters": {"temprature": 0}})


def test_load_reads_the_prompt_file():
    assert Prompt.load("parse_cv_section").messages
