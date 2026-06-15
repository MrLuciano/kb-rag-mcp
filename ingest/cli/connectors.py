"""
CLI commands for connector management.

Provides subcommands to list supported connector types and stage
connector sync requests.
"""

import logging
from pathlib import Path

import click

from ingest.connectors.models import ConnectorConfig

log = logging.getLogger("kb-ingest.cli.connectors")


@click.group(name="connectors")
def connectors_group() -> None:
    """Manage enterprise data source connectors (Confluence, JIRA, Git)."""


@connectors_group.command(name="list")
def list_connectors() -> None:
    """List all supported connector types."""
    types = list_supported_types()
    if types:
        click.echo("Supported connector types:")
        for t in types:
            click.echo(f"  - {t}")
    else:
        click.echo("No connectors registered.")


@connectors_group.command(name="stage")
@click.option(
    "--type",
    "connector_type",
    required=True,
    help="Connector type (e.g. confluence, jira, git)",
)
@click.option(
    "--source-key",
    required=True,
    help="Connector source key (e.g. confluence://myspace)",
)
@click.option(
    "--endpoint",
    required=True,
    help="Remote API endpoint URL",
)
@click.option(
    "--auth-method",
    default="basic",
    show_default=True,
    help="Authentication method (basic, token, oauth, ssh)",
)
@click.option(
    "--auth-credentials",
    default="",
    help="Auth credentials reference (env var name or token)",
)
@click.option(
    "--staging-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Override staging directory",
)
@click.option(
    "--clean",
    is_flag=True,
    default=False,
    help="Clean stale staging files before staging",
)
def stage_connector(
    connector_type: str,
    source_key: str,
    endpoint: str,
    auth_method: str,
    auth_credentials: str,
    staging_dir: Path | None,
    clean: bool,
) -> None:
    """Validate connector config and stage a sync request.

    This command validates that the connector type is registered,
    creates the connector configuration, and prepares the staging
    directory. Actual document fetching requires the connector
    implementation to be installed.
    """
    types = list_supported_types()
    if connector_type not in types:
        click.echo(
            f"Error: connector type '{connector_type}' not registered.\n"
            f"Supported types: {', '.join(types) if types else '(none)'}"
        )
        raise click.Abort()

    if clean and staging_dir:
        removed = cleanup_stale_staging(staging_root=staging_dir)
        if removed:
            click.echo(f"Cleaned {removed} stale staging files.")

    staging_root = staging_dir or get_staging_root()
    click.echo(f"Staging directory: {staging_root}")

    config = ConnectorConfig(
        source_key=source_key,
        connector_type=connector_type,
        endpoint=endpoint,
        auth_method=auth_method,
        auth_credentials=auth_credentials,
    )

    click.echo(
        f"Connector '{connector_type}' configured for {source_key}\n"
        f"  Endpoint: {endpoint}\n"
        f"  Auth: {auth_method}\n"
        f"  Staging: {staging_root}\n"
    )
    click.echo(
        "To run the connector sync, use a source-specific command "
        "once the connector implementation is installed."
    )
