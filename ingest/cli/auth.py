"""
CLI commands for API key management.

Allows operators to create, list, and revoke API keys used for
optional HTTP transport authentication.
"""

import click

from kb_server.auth_registry import AuthRegistry


@click.group(name="auth")
def auth_group() -> None:
    """Manage API keys for HTTP transport authentication."""


@auth_group.command(name="create")
@click.option(
    "--scope",
    type=click.Choice(["global", "kb"]),
    default="global",
    help="Key scope: global or per-knowledge-base",
)
@click.option(
    "--kb-name",
    default=None,
    help="Knowledge base name (required if scope=kb)",
)
@click.option(
    "--description",
    default="",
    help="Human-readable description for this key",
)
def create_key(scope: str, kb_name: str | None, description: str) -> None:
    """Create a new API key.

    Prints the key once. It cannot be retrieved later.
    """
    if scope == "kb" and not kb_name:
        click.echo("Error: --kb-name is required when scope=kb", err=True)
        return

    registry = AuthRegistry()
    raw_key = registry.create_key(
        scope=scope, kb_name=kb_name, description=description
    )

    click.echo("─" * 50)
    click.echo("New API key created.")
    click.echo("")
    click.echo(f"  Key:      {raw_key}")
    click.echo(f"  Scope:    {scope}")
    if kb_name:
        click.echo(f"  KB:       {kb_name}")
    if description:
        click.echo(f"  Desc:     {description}")
    click.echo("")
    click.echo("⚠ Store this key securely. It will not be shown again.")
    click.echo("─" * 50)


@auth_group.command(name="list")
def list_keys() -> None:
    """List all API keys (without revealing the raw keys)."""
    registry = AuthRegistry()
    keys = registry.list_keys()

    if not keys:
        click.echo("No API keys found.")
        return

    click.echo(f"{'Prefix':12} {'Scope':8} {'KB':24} {'Revoked':8} "
               f"{'Created':22} {'Description'}")
    click.echo("─" * 100)
    for k in keys:
        prefix = k["prefix"]
        scope = k["scope"]
        kb = k["kb_name"] or ""
        revoked = "✓" if k["revoked"] else "—"
        created = k["created_at"][:19] if k["created_at"] else ""
        desc = k["description"] or ""
        click.echo(f"{prefix:12} {scope:8} {kb:24} {revoked:8} "
                   f"{created:22} {desc}")


@auth_group.command(name="revoke")
@click.argument("prefix")
@click.confirmation_option(
    prompt="Are you sure you want to revoke this key?"
)
def revoke_key(prefix: str) -> None:
    """Revoke an API key by its 8-character prefix.

    Use ``kb-rag auth list`` to find the prefix.
    """
    registry = AuthRegistry()
    if registry.revoke_key(prefix):
        click.echo(f"Key with prefix '{prefix}' revoked.")
    else:
        click.echo(f"No active key found with prefix '{prefix}'.")
