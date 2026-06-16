"""
Git connector for ingesting repository files.

Supports public and private git repositories via HTTPS or SSH.
Performs incremental sync by comparing commit SHAs and using
``git diff --name-only`` to discover changed files.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ingest.connectors.base import ConnectorBase
from ingest.connectors.factory import register
from ingest.connectors.models import (
    ConnectorConfig,
    RemoteDocument,
    SyncResult,
)

log = logging.getLogger("kb-ingest.connectors.git")

_SUPPORTED_EXTENSIONS: set[str] = {
    ".md",
    ".rst",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".scss",
    ".less",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".conf",
    ".xml",
    ".html",
    ".sh",
    ".bash",
    ".zsh",
    ".env",
    ".sql",
    ".dockerfile",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}

_MARKDOWN_EXTENSIONS: set[str] = {".md", ".rst"}


class GitConnector(ConnectorBase):
    """Connector for git repositories.

    Clones (or pulls) a remote git repository to a local workspace,
    then discovers and extracts file content.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._workspace: Optional[str] = None
        self._owns_workspace: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_auth_url(self) -> str:
        url = self.config.endpoint
        token_env = self.config.auth_credentials
        creds = os.getenv(token_env, "")
        if creds and url.startswith("https://"):
            url = url.replace(
                "https://", f"https://x-access-token:{creds}@", 1
            )
        return url

    def _git_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        if self.config.auth_method == "ssh-key":
            key_env = self.config.auth_credentials
            key_path = os.getenv(key_env, "")
            if key_path:
                env["GIT_SSH_COMMAND"] = (
                    f"ssh -i {key_path} -o StrictHostKeyChecking=no"
                )
        return env

    def _check_git_available(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _clone_or_pull(self, repo_path: str) -> None:
        url = self._build_auth_url()
        env = self._git_env()

        if os.path.isdir(os.path.join(repo_path, ".git")):
            log.info("Pulling latest changes in %s", repo_path)
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
                check=True,
            )
        else:
            log.info("Cloning %s into %s", self.config.endpoint, repo_path)
            subprocess.run(
                ["git", "clone", url, repo_path],
                capture_output=True,
                text=True,
                env=env,
                timeout=300,
                check=True,
            )

    def _get_head_sha(self, repo_path: str) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return result.stdout.strip()

    def _list_repo_files(
        self, repo_path: str, at_commit: str = "HEAD"
    ) -> list[str]:
        result = subprocess.run(
            ["git", "ls-tree", "--name-only", "-r", at_commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return [
            f.strip() for f in result.stdout.strip().splitlines() if f.strip()
        ]

    def _get_changed_files_since(
        self, repo_path: str, since_commit: str
    ) -> list[str]:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{since_commit}..HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return [
            f.strip() for f in result.stdout.strip().splitlines() if f.strip()
        ]

    def _read_file_at_commit(
        self, repo_path: str, filepath: str, commit: str
    ) -> str:
        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{filepath}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except Exception:
            return ""

    def _get_content_type(self, filepath: str) -> str:
        ext = Path(filepath).suffix.lower()
        if ext in _MARKDOWN_EXTENSIONS:
            return "text/markdown"
        if ext in _SUPPORTED_EXTENSIONS:
            return "text/plain"
        if filepath.lower() == "dockerfile":
            return "text/plain"
        return ""

    @staticmethod
    def _build_remote_url(
        repo_url: str, filepath: str, commit_sha: str
    ) -> str:
        base = repo_url.rstrip(".git")
        return f"{base}/blob/{commit_sha}/{filepath}"

    def _parse_document(
        self,
        filepath: str,
        content: str,
        commit_sha: str,
        remote_url: str,
    ) -> Optional[RemoteDocument]:
        ctype = self._get_content_type(filepath)
        if not ctype:
            return None

        return RemoteDocument(
            remote_id=filepath,
            source_key=self.source_key,
            connector_type=self.connector_type,
            title=filepath,
            content=content,
            content_type=ctype,
            remote_url=self._build_remote_url(
                remote_url, filepath, commit_sha
            ),
            metadata={
                "commit_sha": commit_sha,
                "filepath": filepath,
            },
        )

    # ------------------------------------------------------------------
    # ConnectorBase interface
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        if not self._check_git_available():
            raise RuntimeError("git is not available on this system")

    async def fetch_documents(self, since: Optional[str] = None) -> SyncResult:
        if not self._check_git_available():
            return SyncResult(
                source_key=self.source_key,
                errors=["Git is not available on this system"],
            )

        repo_url = self.config.endpoint
        if self._workspace:
            workspace = self._workspace
        else:
            workspace = tempfile.mkdtemp(prefix="kb-git-")
            self._workspace = workspace
            self._owns_workspace = True

        try:
            self._clone_or_pull(workspace)
            head_sha = self._get_head_sha(workspace)
        except Exception as e:
            log.error("Git operation failed: %s", e)
            return SyncResult(
                source_key=self.source_key,
                errors=[f"Git operation failed: {e}"],
            )

        if since:
            changed = self._get_changed_files_since(
                workspace, since_commit=since
            )
            filepaths = changed
        else:
            filepaths = self._list_repo_files(workspace)

        documents: list[RemoteDocument] = []

        for fp in filepaths:
            content = self._read_file_at_commit(workspace, fp, head_sha)
            if not content:
                continue
            doc = self._parse_document(
                filepath=fp,
                content=content,
                commit_sha=head_sha,
                remote_url=repo_url,
            )
            if doc:
                documents.append(doc)

        return SyncResult(
            source_key=self.source_key,
            documents=documents,
            checkpoint=head_sha,
            total_fetched=len(documents),
        )

    async def fetch_document(self, remote_id: str) -> Optional[RemoteDocument]:
        ws = self._workspace
        if not ws or not os.path.isdir(os.path.join(ws, ".git")):
            return None

        try:
            head_sha = self._get_head_sha(ws)
            content = self._read_file_at_commit(ws, remote_id, head_sha)
            if not content:
                return None
            return self._parse_document(
                filepath=remote_id,
                content=content,
                commit_sha=head_sha,
                remote_url=self.config.endpoint,
            )
        except Exception:
            return None

    async def close(self) -> None:
        if (
            self._owns_workspace
            and self._workspace
            and os.path.isdir(self._workspace)
        ):
            shutil.rmtree(self._workspace, ignore_errors=True)
        self._workspace = None


register("git", GitConnector)
