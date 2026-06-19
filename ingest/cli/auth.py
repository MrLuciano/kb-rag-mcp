"""
CLI commands for API key management.

Allows operators to create, list, and revoke API keys used for
optional HTTP transport authentication.
"""

import os
from pathlib import Path

import click

from kb_server.auth.service import AuthService


def _get_service() -> AuthService:
    db_path = Path(os.getenv("AUTH_DB_PATH", "data/auth.db"))
    return AuthService(db_path=db_path)


@click.group(name="auth")
def auth_group() -> None:
    """Manage API keys for HTTP transport authentication."""


@auth_group.command(name="create")
@click.option(
    "--description",
    default="",
    help="Human-readable description for this key",
)
def create_key(description: str) -> None:
    """Create a new API key.

    Prints the key once. It cannot be retrieved later.
    """
    svc = _get_service()

    admin = svc.get_user_by_username("admin")
    if admin is None:
        admin = svc.create_user(username="admin", role="admin")

    raw_key, api_key = svc.create_api_key(
        str(admin.id), description=description
    )

    click.echo("─" * 50)
    click.echo("New API key created.")
    click.echo("")
    click.echo(f"  Key:      {raw_key}")
    click.echo(f"  Prefix:   {api_key.prefix}")
    if description:
        click.echo(f"  Desc:     {description}")
    click.echo("")
    click.echo("⚠ Store this key securely. It will not be shown again.")
    click.echo("─" * 50)


@auth_group.command(name="list")
def list_keys() -> None:
    """List all API keys (without revealing the raw keys)."""
    svc = _get_service()
    keys = svc.list_all_api_keys()

    if not keys:
        click.echo("No API keys found.")
        return

    click.echo(
        f"{'Prefix':12} {'User':24} {'Revoked':8} "
        f"{'Created':22} {'Description'}"
    )
    click.echo("─" * 100)
    for k in keys:
        prefix = k.prefix
        user = k.user.username if k.user else k.user_id[:8]
        revoked = "✓" if k.is_revoked else "—"
        created = (
            str(k.created_at)[:19] if k.created_at else ""
        )
        desc = k.description or ""
        click.echo(
            f"{prefix:12} {user:24} {revoked:8} "
            f"{created:22} {desc}"
        )


@auth_group.command(name="revoke")
@click.argument("prefix")
@click.confirmation_option(prompt="Are you sure you want to revoke this key?")
def revoke_key(prefix: str) -> None:
    """Revoke an API key by its 8-character prefix.

    Use ``kb-rag auth list`` to find the prefix.
    """
    svc = _get_service()
    if svc.revoke_key_by_prefix(prefix):
        click.echo(f"Key with prefix '{prefix}' revoked.")
    else:
        click.echo(f"No active key found with prefix '{prefix}'.")
