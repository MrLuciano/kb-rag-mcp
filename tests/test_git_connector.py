"""
Tests for Git connector.

Creates temporary git repositories to exercise the connector
against real git operations (clone, diff, log, checkout).
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingest.connectors.models import ConnectorConfig


@pytest.fixture
def git_config():
    return ConnectorConfig(
        source_key="git://myorg/myrepo",
        connector_type="git",
        endpoint="https://github.com/myorg/myrepo.git",
        auth_method="token",
        auth_credentials="GITHUB_TOKEN",
    )


@pytest.fixture
def git_config_ssh():
    return ConnectorConfig(
        source_key="git://myorg/myrepo",
        connector_type="git",
        endpoint="git@github.com:myorg/myrepo.git",
        auth_method="ssh-key",
        auth_credentials="GIT_SSH_KEY",
    )


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repo with files at multiple commits."""
    import subprocess

    tmpdir = Path(tempfile.mkdtemp())

    subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmpdir,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmpdir,
        capture_output=True,
    )

    (tmpdir / "README.md").write_text("# My Project\n\nDocs here.\n")
    (tmpdir / "src").mkdir()
    (tmpdir / "src" / "main.py").write_text("def main():\n    pass\n")
    subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmpdir,
        capture_output=True,
    )
    first_sha = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    (tmpdir / "docs").mkdir()
    (tmpdir / "docs" / "guide.md").write_text("# Guide\n\nStep 1.\n")
    (tmpdir / "config.yaml").write_text("key: value\n")
    subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add docs and config"],
        cwd=tmpdir,
        capture_output=True,
    )
    second_sha = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    (tmpdir / "src" / "utils.py").write_text("def util():\n    return 1\n")
    (tmpdir / "README.md").write_text("# My Project\n\nUpdated.\n")
    subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add utils, update README"],
        cwd=tmpdir,
        capture_output=True,
    )
    third_sha = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    yield tmpdir, first_sha, second_sha, third_sha

    import shutil

    shutil.rmtree(tmpdir, ignore_errors=True)


class TestGitConnect:
    @patch("subprocess.run")
    def test_connect_validates_git_available(self, mock_run, git_config):
        from ingest.connectors.git import GitConnector

        mock_run.return_value = MagicMock(
            returncode=0, stdout="git version 2.40.0"
        )
        conn = GitConnector(git_config)
        result = conn._check_git_available()
        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_connect_git_not_available(self, mock_run, git_config):
        from ingest.connectors.git import GitConnector

        mock_run.side_effect = FileNotFoundError()
        conn = GitConnector(git_config)
        result = conn._check_git_available()
        assert result is False


class TestGitFileDiscovery:
    def test_discover_all_files(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        files = conn._list_repo_files(str(tmpdir))
        assert len(files) >= 5
        assert "README.md" in files
        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "docs/guide.md" in files
        assert "config.yaml" in files

    def test_discover_files_at_specific_commit(
        self, git_config, temp_git_repo
    ):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        files = conn._list_repo_files(str(tmpdir), at_commit=second_sha)
        assert "README.md" in files
        assert "src/main.py" in files
        assert "docs/guide.md" in files
        assert "config.yaml" in files
        assert "src/utils.py" not in files  # not in second commit


class TestGitDiffDiscovery:
    def test_diff_since_initial(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        changed = conn._get_changed_files_since(
            str(tmpdir), since_commit=first_sha
        )
        assert "docs/guide.md" in changed
        assert "config.yaml" in changed
        assert "README.md" in changed
        assert "src/utils.py" in changed
        assert "src/main.py" not in changed  # committed in first

    def test_diff_since_second(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        changed = conn._get_changed_files_since(
            str(tmpdir), since_commit=second_sha
        )
        assert "src/utils.py" in changed
        assert "README.md" in changed  # modified
        assert "docs/guide.md" not in changed
        assert "config.yaml" not in changed


class TestGitFileContentReading:
    def test_read_file_at_head(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        content = conn._read_file_at_commit(
            str(tmpdir), "README.md", "HEAD"
        )
        assert "Updated" in content  # third commit

    def test_read_file_at_earlier_commit(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        content = conn._read_file_at_commit(
            str(tmpdir), "README.md", first_sha
        )
        assert "My Project" in content
        assert "Updated" not in content

    def test_read_file_removed_returns_empty(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        content = conn._read_file_at_commit(
            str(tmpdir), "nonexistent.py", third_sha
        )
        assert content == ""


class TestGitParseDocument:
    def test_parse_markdown(self, git_config):
        from ingest.connectors.git import GitConnector

        conn = GitConnector(git_config)
        doc = conn._parse_document(
            filepath="README.md",
            content="# Hello\n\nWorld.\n",
            commit_sha="abc123",
            remote_url="https://github.com/myorg/myrepo",
        )
        assert doc is not None
        assert doc.remote_id == "README.md"
        assert doc.title == "README.md"
        assert doc.content == "# Hello\n\nWorld.\n"
        assert doc.content_type == "text/markdown"
        assert doc.metadata["commit_sha"] == "abc123"

    def test_parse_python(self, git_config):
        from ingest.connectors.git import GitConnector

        conn = GitConnector(git_config)
        doc = conn._parse_document(
            filepath="src/main.py",
            content="def main():\n    pass\n",
            commit_sha="abc123",
            remote_url="https://github.com/myorg/myrepo",
        )
        assert doc is not None
        assert doc.remote_id == "src/main.py"
        assert doc.content_type == "text/plain"

    def test_parse_yaml(self, git_config):
        from ingest.connectors.git import GitConnector

        conn = GitConnector(git_config)
        doc = conn._parse_document(
            filepath="config.yaml",
            content="key: value\n",
            commit_sha="abc123",
            remote_url="https://github.com/myorg/myrepo",
        )
        assert doc is not None
        assert doc.content_type == "text/plain"

    def test_parse_unsupported_extension(self, git_config):
        from ingest.connectors.git import GitConnector

        conn = GitConnector(git_config)
        doc = conn._parse_document(
            filepath="image.png",
            content="GARBAGE",
            commit_sha="abc123",
            remote_url="https://github.com/myorg/myrepo",
        )
        assert doc is None


class TestGitFetchDocuments:
    @pytest.mark.asyncio
    @patch("ingest.connectors.git.GitConnector._check_git_available")
    @patch("ingest.connectors.git.GitConnector._clone_or_pull")
    @patch("ingest.connectors.git.GitConnector._get_head_sha")
    async def test_fetch_no_checkpoint(
        self,
        mock_get_head,
        mock_clone_pull,
        mock_check_git,
        git_config,
        temp_git_repo,
    ):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        mock_check_git.return_value = True
        mock_clone_pull.side_effect = lambda repo_path: None
        mock_get_head.return_value = third_sha

        conn = GitConnector(git_config)
        conn._workspace = str(tmpdir)

        result = await conn.fetch_documents(since=None)

        assert result.total_fetched >= 4
        ids = {d.remote_id for d in result.documents}
        assert "README.md" in ids
        assert "src/main.py" in ids
        assert "src/utils.py" in ids
        assert "docs/guide.md" in ids
        assert "config.yaml" in ids
        assert result.checkpoint == third_sha
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    @patch("ingest.connectors.git.GitConnector._check_git_available")
    @patch("ingest.connectors.git.GitConnector._clone_or_pull")
    @patch("ingest.connectors.git.GitConnector._get_head_sha")
    @patch("ingest.connectors.git.GitConnector._get_changed_files_since")
    async def test_fetch_with_checkpoint(
        self,
        mock_diff,
        mock_get_head,
        mock_clone_pull,
        mock_check_git,
        git_config,
        temp_git_repo,
    ):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        mock_check_git.return_value = True
        mock_clone_pull.side_effect = lambda repo_path: None
        mock_get_head.return_value = third_sha
        mock_diff.return_value = ["README.md", "src/utils.py"]

        conn = GitConnector(git_config)
        conn._workspace = str(tmpdir)

        result = await conn.fetch_documents(since=second_sha)

        assert result.total_fetched == 2
        ids = {d.remote_id for d in result.documents}
        assert "README.md" in ids
        assert "src/utils.py" in ids
        mock_diff.assert_called_once_with(
            str(tmpdir), since_commit=second_sha
        )

    @pytest.mark.asyncio
    @patch("ingest.connectors.git.GitConnector._check_git_available")
    async def test_fetch_git_not_available(
        self, mock_check_git, git_config
    ):
        from ingest.connectors.git import GitConnector

        mock_check_git.return_value = False

        conn = GitConnector(git_config)
        result = await conn.fetch_documents(since=None)

        assert result.total_fetched == 0
        assert len(result.errors) == 1
        assert "git" in result.errors[0].lower()

    @pytest.mark.asyncio
    @patch("ingest.connectors.git.GitConnector._check_git_available")
    @patch("ingest.connectors.git.GitConnector._clone_or_pull")
    async def test_fetch_clone_failure(
        self, mock_clone_pull, mock_check_git, git_config
    ):
        from ingest.connectors.git import GitConnector

        mock_check_git.return_value = True
        mock_clone_pull.side_effect = RuntimeError(
            "Failed to clone repository"
        )

        conn = GitConnector(git_config)
        result = await conn.fetch_documents(since=None)

        assert result.total_fetched == 0
        assert len(result.errors) >= 1


class TestGitFetchDocument:
    @pytest.mark.asyncio
    @patch("ingest.connectors.git.GitConnector._check_git_available")
    @patch("ingest.connectors.git.GitConnector._clone_or_pull")
    @patch("ingest.connectors.git.GitConnector._get_head_sha")
    async def test_fetch_single_file(
        self,
        mock_get_head,
        mock_clone_pull,
        mock_check_git,
        git_config,
        temp_git_repo,
    ):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        mock_check_git.return_value = True
        mock_clone_pull.side_effect = lambda repo_path: None
        mock_get_head.return_value = third_sha

        conn = GitConnector(git_config)
        conn._workspace = str(tmpdir)

        doc = await conn.fetch_document("README.md")

        assert doc is not None
        assert doc.remote_id == "README.md"
        assert "Updated" in doc.content

    @pytest.mark.asyncio
    @patch("ingest.connectors.git.GitConnector._check_git_available")
    @patch("ingest.connectors.git.GitConnector._clone_or_pull")
    async def test_fetch_single_file_not_found(
        self, mock_clone_pull, mock_check_git, git_config
    ):
        from ingest.connectors.git import GitConnector

        mock_check_git.return_value = True
        mock_clone_pull.side_effect = lambda repo_path: None

        conn = GitConnector(git_config)
        conn._workspace = "/tmp/nonexistent"

        doc = await conn.fetch_document("nonexistent.py")
        assert doc is None


class TestGitContentTypeDetection:
    def test_content_type_mapping(self, git_config):
        from ingest.connectors.git import GitConnector

        conn = GitConnector(git_config)

        assert conn._get_content_type("readme.md") == "text/markdown"
        assert conn._get_content_type("doc.rst") == "text/markdown"
        assert conn._get_content_type("main.py") == "text/plain"
        assert conn._get_content_type("index.js") == "text/plain"
        assert conn._get_content_type("styles.css") == "text/plain"
        assert conn._get_content_type("data.json") == "text/plain"
        assert conn._get_content_type("config.yaml") == "text/plain"
        assert conn._get_content_type("config.yml") == "text/plain"
        assert conn._get_content_type("text.txt") == "text/plain"
        assert conn._get_content_type("image.png") == ""
        assert conn._get_content_type("archive.zip") == ""
        assert conn._get_content_type("binary.bin") == ""


class TestGitCheckpoint:
    def test_checkpoint_from_sha(self, git_config, temp_git_repo):
        from ingest.connectors.git import GitConnector

        tmpdir, first_sha, second_sha, third_sha = temp_git_repo

        conn = GitConnector(git_config)
        conn._workspace = str(tmpdir)

        cp = conn._get_head_sha(str(tmpdir))
        assert cp == third_sha
        assert len(cp) == 40


class TestFactoryRegistration:
    def test_registered_in_factory(self):
        from ingest.connectors.factory import list_supported_types

        types = list_supported_types()
        assert "git" in types

    def test_can_create_via_factory(self, git_config):
        from ingest.connectors.factory import create_connector, list_supported_types

        conn = create_connector("git", git_config)
        assert conn is not None
        from ingest.connectors.git import GitConnector

        assert isinstance(conn, GitConnector)
