from jobfinder.providers.base import Provider
from jobfinder.providers.greenhouse import GreenhouseProvider
from jobfinder.providers.lever import LeverProvider

# provider name (as in sources.toml) -> Provider class
PROVIDERS: dict[str, type[Provider]] = {
    provider.name: provider for provider in (GreenhouseProvider, LeverProvider)
}
