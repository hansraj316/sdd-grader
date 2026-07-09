"""sddgrade — benchmark & review tool for Spec-Driven Development artifacts."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: the version in pyproject.toml, read from the
    # installed distribution metadata (works for wheels, sdists, and -e installs).
    __version__ = version("sddgrade")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0+unknown"
