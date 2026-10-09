"""The sources file (sources.toml): which companies to follow, as slugs per provider."""

import tomllib
from pathlib import Path
from typing import Self

from pydantic import RootModel, field_validator

from jobfinder.providers import PROVIDERS
from jobfinder.schema import JobSource

SOURCES_FILE = Path("sources.toml")  # relative: the folder the app starts in


class SourcesConfig(RootModel[dict[str, list[str]]]):
    """The sources file's content: provider name -> slugs, e.g. greenhouse = ["datadog"]."""

    @field_validator("root")
    @classmethod
    def _providers_must_exist(cls, slugs_by_provider: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown_providers = slugs_by_provider.keys() - PROVIDERS.keys()
        if unknown_providers:
            raise ValueError(
                f"unknown providers {sorted(unknown_providers)}, known: {sorted(PROVIDERS)}"
            )
        return slugs_by_provider

    @classmethod
    def from_toml(cls, sources_file: Path) -> Self:
        with sources_file.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def sources(self) -> list[JobSource]:
        return [
            JobSource(provider, slug) for provider, slugs in self.root.items() for slug in slugs
        ]
