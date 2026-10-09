"""The boards file (boards.toml): which companies to follow, as slugs per source."""

import tomllib
from pathlib import Path
from typing import Self

from pydantic import RootModel, field_validator

from jobfinder.schema import Board
from jobfinder.sources import SOURCES


class BoardsConfig(RootModel[dict[str, list[str]]]):
    """The boards file's content: source name -> slugs, e.g. greenhouse = ["datadog"]."""

    @field_validator("root")
    @classmethod
    def _sources_must_exist(cls, slugs_by_source: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown = slugs_by_source.keys() - SOURCES.keys()
        if unknown:
            raise ValueError(f"unknown sources {sorted(unknown)}, known: {sorted(SOURCES)}")
        return slugs_by_source

    @classmethod
    def from_toml(cls, boards_file: Path) -> Self:
        with boards_file.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def boards(self) -> list[Board]:
        return [Board(source, slug) for source, slugs in self.root.items() for slug in slugs]
