from jobfinder.sources.base import Source
from jobfinder.sources.greenhouse import GreenhouseSource
from jobfinder.sources.lever import LeverSource

# source name (as in boards.toml) -> Source class
SOURCES: dict[str, type[Source]] = {
    source.name: source for source in (GreenhouseSource, LeverSource)
}
