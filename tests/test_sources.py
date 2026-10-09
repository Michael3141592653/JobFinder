from pathlib import Path

import pytest
from pydantic import ValidationError

from jobfinder.schema import JobSource
from jobfinder.sources import SourcesConfig


def _write_sources_file(tmp_path: Path, content: str) -> Path:
    sources_file = tmp_path / "sources.toml"
    sources_file.write_text(content)
    return sources_file


def test_sources_config_reads_providers_and_slugs_from_toml(tmp_path):
    content = 'greenhouse = ["datadog"]\nlever = ["spotify", "palantir"]'
    sources_file = _write_sources_file(tmp_path, content)

    sources_config = SourcesConfig.from_toml(sources_file)

    assert sources_config.sources() == [
        JobSource("greenhouse", "datadog"),
        JobSource("lever", "spotify"),
        JobSource("lever", "palantir"),
    ]


def test_sources_config_rejects_unknown_provider(tmp_path):
    sources_file = _write_sources_file(tmp_path, 'workday = ["acme"]\n')

    with pytest.raises(ValidationError, match="workday"):
        SourcesConfig.from_toml(sources_file)


def test_sources_config_rejects_slugs_that_are_not_a_list(tmp_path):
    sources_file = _write_sources_file(tmp_path, 'greenhouse = "datadog"\n')

    with pytest.raises(ValidationError):
        SourcesConfig.from_toml(sources_file)
