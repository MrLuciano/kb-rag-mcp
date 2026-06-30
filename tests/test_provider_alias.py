import tempfile
from pathlib import Path

import pytest

from kb_server.config.loader import ConfigLoader


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def loader(db_path):
    ldr = ConfigLoader(db_path=db_path)
    return ldr


# ── ConfigLoader Alias Tests ───────────────────────────────────


class TestConfigLoaderAliases:
    @pytest.mark.asyncio
    async def test_get_aliases_empty(self, loader):
        aliases = await loader.get_aliases()
        assert aliases == {}

    @pytest.mark.asyncio
    async def test_get_aliases(self, loader):
        await loader.set(
            "provider_alias.aliyun",
            "dashscope",
            group_name="provider_alias",
        )
        await loader.set(
            "provider_alias.my-local",
            "lmstudio-rest",
            group_name="provider_alias",
        )
        aliases = await loader.get_aliases()
        assert aliases == {
            "aliyun": "dashscope",
            "my-local": "lmstudio-rest",
        }

    @pytest.mark.asyncio
    async def test_resolve_alias(self, loader):
        await loader.set(
            "provider_alias.aliyun",
            "dashscope",
            group_name="provider_alias",
        )
        result = await loader.resolve_alias("aliyun")
        assert result == "dashscope"

    @pytest.mark.asyncio
    async def test_resolve_alias_missing(self, loader):
        result = await loader.resolve_alias("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_alias_ignores_other_groups(self, loader):
        await loader.set(
            "some_other_key",
            "value",
            group_name="other_group",
        )
        result = await loader.resolve_alias("some_other_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_aliases_ignores_non_alias_entries(self, loader):
        await loader.set(
            "provider_alias.valid",
            "canonical",
            group_name="provider_alias",
        )
        await loader.set(
            "unrelated_key",
            "value",
            group_name="general",
        )
        aliases = await loader.get_aliases()
        assert aliases == {"valid": "canonical"}

    @pytest.mark.asyncio
    async def test_wildcard_observer(self, loader):
        changes = []

        def callback(key, value):
            changes.append((key, value))

        loader.on_change("provider_alias.*", callback)
        await loader.set(
            "provider_alias.test_alias",
            "test_val",
            group_name="provider_alias",
        )
        assert len(changes) == 1
        assert changes[0] == ("provider_alias.test_alias", "test_val")

    @pytest.mark.asyncio
    async def test_wildcard_observer_ignores_other_keys(self, loader):
        changes = []

        def callback(key, value):
            changes.append((key, value))

        loader.on_change("provider_alias.*", callback)
        loader._notify_observers("other_key", "val")
        assert len(changes) == 0

    @pytest.mark.asyncio
    async def test_exact_match_observer_still_works(self, loader):
        changes = []

        def callback(key, value):
            changes.append((key, value))

        loader.on_change("exact_key", callback)
        loader._notify_observers("exact_key", "val")
        assert len(changes) == 1
        assert changes[0] == ("exact_key", "val")

    @pytest.mark.asyncio
    async def test_star_observer_still_works(self, loader):
        changes = []

        def callback(key, value):
            changes.append((key, value))

        loader.on_change("*", callback)
        loader._notify_observers("any_key", "val")
        assert len(changes) == 1


# ── EmbedClient Alias Integration Tests ────────────────────────


class TestEmbedClientAliases:
    @pytest.mark.asyncio
    async def test_resolve_alias_returns_none_when_no_loader(self, loader):
        from kb_server.embed_client import _resolve_alias

        result = await _resolve_alias("any_alias")
        assert result is None

    @pytest.mark.asyncio
    async def test_init_alias_resolution_sets_loader(self, loader):
        import kb_server.embed_client as ec

        assert ec._config_loader is None
        ec.init_alias_resolution(loader)
        assert ec._config_loader is not None

    @pytest.mark.asyncio
    async def test_resolve_alias_with_loader(self, loader):
        await loader.set(
            "provider_alias.aliyun",
            "dashscope",
            group_name="provider_alias",
        )

        import kb_server.embed_client as ec

        ec.init_alias_resolution(loader)
        result = await ec._resolve_alias("aliyun")
        assert result == "dashscope"

    @pytest.mark.asyncio
    async def test_resolve_alias_missing_with_loader(self, loader):
        import kb_server.embed_client as ec

        ec.init_alias_resolution(loader)
        result = await ec._resolve_alias("nonexistent")
        assert result is None
