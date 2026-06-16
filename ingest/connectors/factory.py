"""
Connector factory for mapping type strings to implementations.

Provides ``create_connector`` for runtime instantiation and
``list_supported_types`` for CLI discovery. Source-specific
connectors register themselves here as they are implemented.
"""

import logging
from typing import Optional

from ingest.connectors.base import ConnectorBase
from ingest.connectors.models import ConnectorConfig

log = logging.getLogger("kb-ingest.connectors.factory")

# Registry of connector implementations by type string.
# Populated by register() calls from source-specific modules.
_CONNECTOR_REGISTRY: dict[str, type[ConnectorBase]] = {}


def register(connector_type: str, cls: type[ConnectorBase]) -> None:
    """Register a connector implementation class for a type string.

    Args:
        connector_type: Type string (e.g. ``confluence``, ``jira``,
            ``git``).
        cls: The connector implementation class.
    """
    _CONNECTOR_REGISTRY[connector_type] = cls
    log.debug(
        "Registered connector type: %s -> %s", connector_type, cls.__name__
    )


def create_connector(
    connector_type: str, config: ConnectorConfig
) -> Optional[ConnectorBase]:
    """Create a connector instance by type string.

    Args:
        connector_type: Type string (e.g. ``confluence``, ``jira``,
            ``git``).
        config: Connector configuration.

    Returns:
        A connector instance, or ``None`` if the type is not registered.
    """
    cls = _CONNECTOR_REGISTRY.get(connector_type)
    if cls is None:
        log.warning("No connector registered for type: %s", connector_type)
        return None
    log.info(
        "Creating connector: %s (source=%s)", connector_type, config.source_key
    )
    return cls(config)


def list_supported_types() -> list[str]:
    """List all registered connector type strings.

    Returns:
        Sorted list of connector type strings.
    """
    return sorted(_CONNECTOR_REGISTRY.keys())
