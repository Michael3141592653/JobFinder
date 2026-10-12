"""Field descriptions are instructions to the model: the schema goes in its prompt."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Never empty: Ollama enforces the schema's minLength, so the model writes text or null, not "".
Text = Annotated[str, StringConstraints(min_length=1)]


class YearMonth(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)


class Experience(BaseModel):
    title: Text = Field(description="The job title, as written")
    company: Text
    start: YearMonth
    end: YearMonth | None = Field(description="null if it is the current job")
    description: Text | None = Field(
        description="What the person did there, as the CV says it; null if nothing"
    )


class Education(BaseModel):
    degree: Text = Field(description='e.g. "MSc"')
    field: Text = Field(description='e.g. "Computer Science"')
    institution: Text
    start_year: int | None
    end_year: int | None = Field(description="null if still studying")
    grade: Text | None = Field(
        description='The final mark only, as written with its label, e.g. "110/110 cum laude" '
        'or "GPA 3.8/4.0"; null if the CV gives none'
    )
    description: Text | None = Field(
        description="Anything else the CV says about it but the grade, e.g. thesis, "
        "associations; null if nothing"
    )


class Publication(BaseModel):
    title: Text
    venue: Text | None = Field(description='Journal or conference, e.g. "NeurIPS"')
    year: int | None


class ParsedCv(BaseModel):
    location: Text | None = Field(description="Where the person lives, if written")
    experiences: list[Experience] = Field(description="Every job, most recent first")
    education: list[Education]
    publications: list[Publication] = Field(description="Papers and articles; empty if none")
    skills: list[Text] = Field(description="Technical skills, tools and languages, one per item")
    languages: list[Text] = Field(description='Spoken languages with level, e.g. "English (C1)"')
