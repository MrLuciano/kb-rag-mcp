# PHASE 13: Ingestion Automation - Implementation Plan

**Status:** In Progress  
**Duration:** 7 days (Days 106-112)  
**Started:** 2026-05-16  
**Version:** v0.11.0-dev  

---

## Overview

PHASE 13 introduces automated ingestion workflows to eliminate manual 
intervention when documents are added or updated. This phase implements 
three key features:

1. **File Watcher** - Auto-detect file changes and trigger ingestion
2. **Version Extraction** - Parse version info from filenames/paths
3. **Metadata Overrides** - Per-directory `_meta.json` configuration

These features integrate seamlessly with the existing job system and 
maintain full backward compatibility.

---

## Goals

- ✅ Auto-detect file changes and trigger incremental ingestion
- ✅ Extract version information from filenames and index
- ✅ Support per-directory metadata overrides with `_meta.json`
- ✅ Reduce manual ingestion work by 90%+
- ✅ Maintain 70%+ test coverage
- ✅ Zero breaking changes to existing APIs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     File System Events                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  File Watcher    │◄──── watchdog
                  │  (debouncer)     │
                  └────────┬─────────┘
                           │
                           │ create/modify events
                           │
                           ▼
                  ┌──────────────────┐
                  │  MetaLoader      │◄──── _meta.json
                  │  (overrides)     │
                  └────────┬─────────┘
                           │
                           │ metadata
                           │
                           ▼
                  ┌──────────────────┐
                  │ VersionExtractor │◄──── regex patterns
                  │  (filename)      │
                  └────────┬─────────┘
                           │
                           │ version field
                           │
                           ▼
                  ┌──────────────────┐
                  │   JobManager     │
                  │  (queue task)    │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Worker Pool     │
                  │  (process doc)   │
                  └──────────────────┘
```

---

## Feature 1: File Watcher

### Overview
Monitor filesystem for document changes and automatically trigger ingestion 
via the job system. Uses `watchdog` library with 30s debounce window to 
batch changes.

### Implementation

**File:** `ingest/watcher/file_watcher.py` (~250 lines)

```python
"""
Filesystem watcher for automatic document ingestion.

Monitors WATCH_PATH for file create/modify/delete events and triggers
incremental ingestion via JobManager. Uses debouncing to batch changes
within 30s window.

Features:
- Recursive directory monitoring
- Debounce: 30s window, merge multiple changes
- Ignore temp files (.tmp, .swp, .~, ~$*)
- Integration with existing job system
- Health check support

Environment Variables:
- WATCH_PATH: Directory to monitor (default: DOCS_PATH)
- WATCH_DEBOUNCE_SECONDS: Debounce window (default: 30)
- WATCH_IGNORE_PATTERNS: Comma-separated ignore patterns
- WATCH_RECURSIVE: Monitor subdirectories (default: true)

Usage:
    python -m ingest.watcher.file_watcher
    
    # Or via systemd:
    systemctl start kb-rag-watcher
"""

import os
import time
import logging
from pathlib import Path
from threading import Timer
from collections import defaultdict

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ingest.job.manager import JobManager
from ingest.core.file_scanner import FileScanner

logger = logging.getLogger(__name__)


class Debouncer:
    """Debounce file events within a time window."""
    
    def __init__(self, seconds: int = 30):
        self.seconds = seconds
        self.pending: dict[str, Timer] = {}
        self.events: dict[str, list[str]] = defaultdict(list)
    
    def schedule(self, path: str, event_type: str, callback):
        """Schedule callback after debounce window."""
        # Cancel existing timer for this path
        if path in self.pending:
            self.pending[path].cancel()
        
        # Track event
        self.events[path].append(event_type)
        
        # Schedule new timer
        timer = Timer(
            self.seconds,
            lambda: self._execute(path, callback)
        )
        timer.start()
        self.pending[path] = timer
    
    def _execute(self, path: str, callback):
        """Execute callback after debounce window."""
        events = self.events.pop(path, [])
        self.pending.pop(path, None)
        callback(path, events)


class DocWatcher(FileSystemEventHandler):
    """Handle filesystem events for documents."""
    
    IGNORE_PATTERNS = ['.tmp', '.swp', '.~', '~$', '.git', '__pycache__']
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt']
    
    def __init__(
        self,
        job_manager: JobManager,
        debounce_seconds: int = 30,
        ignore_patterns: list[str] | None = None
    ):
        self.job_manager = job_manager
        self.debouncer = Debouncer(debounce_seconds)
        self.ignore_patterns = ignore_patterns or self.IGNORE_PATTERNS
        logger.info(
            f"DocWatcher initialized (debounce={debounce_seconds}s, "
            f"ignore={self.ignore_patterns})"
        )
    
    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        path_obj = Path(path)
        
        # Ignore directories
        if path_obj.is_dir():
            return True
        
        # Ignore by pattern
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        
        # Ignore unsupported extensions
        if path_obj.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return True
        
        return False
    
    def on_created(self, event):
        """Handle file creation."""
        if self.should_ignore(event.src_path):
            return
        
        logger.info(f"File created: {event.src_path}")
        self.debouncer.schedule(
            event.src_path,
            'created',
            self._trigger_ingestion
        )
    
    def on_modified(self, event):
        """Handle file modification."""
        if self.should_ignore(event.src_path):
            return
        
        logger.info(f"File modified: {event.src_path}")
        self.debouncer.schedule(
            event.src_path,
            'modified',
            self._trigger_ingestion
        )
    
    def on_deleted(self, event):
        """Handle file deletion."""
        if self.should_ignore(event.src_path):
            return
        
        logger.info(f"File deleted: {event.src_path}")
        # TODO: Implement deletion from Qdrant (future phase)
    
    def _trigger_ingestion(self, path: str, events: list[str]):
        """Trigger ingestion job for file."""
        logger.info(
            f"Triggering ingestion for {path} "
            f"(events: {', '.join(events)})"
        )
        
        try:
            # Create job for single file
            job = self.job_manager.create_job(
                job_type='ingest',
                payload={
                    'path': path,
                    'auto_triggered': True,
                    'events': events
                }
            )
            logger.info(f"Job {job.id} created for {path}")
        except Exception as e:
            logger.error(f"Failed to create job for {path}: {e}")


def main():
    """Run file watcher as standalone service."""
    # Load environment
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    
    watch_path = os.getenv('WATCH_PATH') or os.getenv('DOCS_PATH')
    if not watch_path:
        raise ValueError("WATCH_PATH or DOCS_PATH must be set")
    
    watch_path = Path(watch_path)
    if not watch_path.exists():
        raise ValueError(f"Watch path does not exist: {watch_path}")
    
    debounce_seconds = int(os.getenv('WATCH_DEBOUNCE_SECONDS', '30'))
    recursive = os.getenv('WATCH_RECURSIVE', 'true').lower() == 'true'
    ignore_patterns = os.getenv('WATCH_IGNORE_PATTERNS', '').split(',')
    ignore_patterns = [p.strip() for p in ignore_patterns if p.strip()]
    
    logger.info(f"Starting file watcher on {watch_path}")
    logger.info(f"Recursive: {recursive}, Debounce: {debounce_seconds}s")
    
    # Initialize components
    job_manager = JobManager()
    handler = DocWatcher(
        job_manager,
        debounce_seconds=debounce_seconds,
        ignore_patterns=ignore_patterns or None
    )
    
    # Start observer
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=recursive)
    observer.start()
    
    logger.info("File watcher started successfully")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file watcher...")
        observer.stop()
    
    observer.join()
    logger.info("File watcher stopped")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
```

**Configuration:**

Add to `.env`:
```bash
# File Watcher Configuration
WATCH_PATH=/path/to/docs              # Default: DOCS_PATH
WATCH_DEBOUNCE_SECONDS=30             # Debounce window
WATCH_IGNORE_PATTERNS=.tmp,.swp,.~,~$* # Ignore patterns
WATCH_RECURSIVE=true                  # Monitor subdirectories
```

**systemd Service:**

File: `deployment/systemd/kb-rag-watcher.service`

```ini
[Unit]
Description=KB-RAG File Watcher
Documentation=https://github.com/MrLuciano/kb-rag-mcp
After=kb-rag-server.service
Requires=kb-rag-server.service
PartOf=kb-rag.target

[Service]
Type=simple
User=kb-rag
Group=kb-rag
WorkingDirectory=/opt/kb-rag

# Environment
EnvironmentFile=/opt/kb-rag/kb-rag.env

# Execution
ExecStart=/opt/kb-rag/venv/bin/python -m ingest.watcher.file_watcher
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/kb-rag/data /opt/kb-rag/logs

# Resource limits
MemoryMax=512M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kb-rag-watcher

[Install]
WantedBy=kb-rag.target
```

**Tests:**

File: `tests/test_file_watcher.py` (~150 lines)

```python
"""Tests for file watcher."""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch

from ingest.watcher.file_watcher import DocWatcher, Debouncer


class TestDebouncer:
    """Test debouncing logic."""
    
    def test_single_event(self):
        """Single event triggers callback after window."""
        debouncer = Debouncer(seconds=0.1)
        callback = Mock()
        
        debouncer.schedule('/path/file.pdf', 'created', callback)
        time.sleep(0.15)
        
        callback.assert_called_once_with('/path/file.pdf', ['created'])
    
    def test_multiple_events_batched(self):
        """Multiple events within window are batched."""
        debouncer = Debouncer(seconds=0.1)
        callback = Mock()
        
        debouncer.schedule('/path/file.pdf', 'created', callback)
        time.sleep(0.05)
        debouncer.schedule('/path/file.pdf', 'modified', callback)
        time.sleep(0.15)
        
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == '/path/file.pdf'
        assert 'created' in args[1]
        assert 'modified' in args[1]


class TestDocWatcher:
    """Test document watcher."""
    
    @pytest.fixture
    def job_manager(self):
        """Mock job manager."""
        return Mock()
    
    @pytest.fixture
    def watcher(self, job_manager):
        """Create watcher instance."""
        return DocWatcher(job_manager, debounce_seconds=0.1)
    
    def test_ignore_temp_files(self, watcher):
        """Temp files should be ignored."""
        assert watcher.should_ignore('/path/file.tmp')
        assert watcher.should_ignore('/path/~$file.docx')
        assert watcher.should_ignore('/path/.swp')
    
    def test_ignore_unsupported_extensions(self, watcher):
        """Unsupported extensions should be ignored."""
        assert watcher.should_ignore('/path/file.exe')
        assert watcher.should_ignore('/path/file.zip')
        assert not watcher.should_ignore('/path/file.pdf')
    
    def test_on_created_triggers_job(self, watcher, job_manager):
        """File creation should trigger ingestion job."""
        event = Mock()
        event.src_path = '/path/doc.pdf'
        event.is_directory = False
        
        with patch.object(Path, 'is_dir', return_value=False):
            watcher.on_created(event)
            time.sleep(0.15)
        
        job_manager.create_job.assert_called_once()
        call_args = job_manager.create_job.call_args[1]
        assert call_args['job_type'] == 'ingest'
        assert '/path/doc.pdf' in call_args['payload']['path']
```

**Acceptance Criteria:**
- ✅ Watcher detects new/modified files within 30s
- ✅ Debounce works (batches changes within window)
- ✅ Temp files (.tmp, .swp, ~$) are ignored
- ✅ Service runs continuously without crashes
- ✅ Job creation logged with path and events

---

## Feature 2: Version Extraction

### Overview
Extract version information from filenames and directory paths using regex 
patterns. Add `version` field to Qdrant payload for filtering.

### Implementation

**File:** `ingest/core/version_extractor.py` (~120 lines)

```python
"""
Extract version information from filenames and paths.

Supports common version patterns found in documentation:
- Numeric: 22.3, 16.2.1
- CE prefix: CE 24.4, CE 23.1
- v prefix: v2.5, v1.0.0

Version is extracted from:
1. Filename (highest priority)
2. Parent directory name
3. Grandparent directory name

The first match is used as the version.

Examples:
- "ArchiveCenter_22.3_Admin_Guide.pdf" → "22.3"
- "/docs/xECM/CE 24.4/manual.pdf" → "CE 24.4"
- "Release Notes for version 16.2" → "16.2"
- "file_without_version.pdf" → None

Usage:
    extractor = VersionExtractor()
    version = extractor.extract(Path("/path/to/file_22.3.pdf"))
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VersionExtractor:
    """Extract version info from filenames and paths."""
    
    # Regex patterns for version detection (priority order)
    PATTERNS = [
        # CE prefix: "CE 24.4", "CE 23.1"
        r'CE\s+(\d{2}\.\d+(?:\.\d+)?)',
        
        # v prefix: "v2.5", "v1.0.0"
        r'v(\d+\.\d+(?:\.\d+)?)',
        
        # Numeric: "22.3", "16.2.1"
        r'(\d{2}\.\d+(?:\.\d+)?)',
        
        # Version keyword: "version 16.2"
        r'version\s+(\d+\.\d+(?:\.\d+)?)',
    ]
    
    def extract(self, file_path: Path) -> str | None:
        """
        Extract version from file path.
        
        Args:
            file_path: Path to document file
        
        Returns:
            Version string or None if not found
        """
        # Sources to check (priority order)
        sources = [
            file_path.name,              # filename
            file_path.parent.name,       # parent dir
            file_path.parent.parent.name # grandparent dir
        ]
        
        for source in sources:
            for pattern in self.PATTERNS:
                match = re.search(pattern, source, re.IGNORECASE)
                if match:
                    version = match.group(0)
                    logger.debug(
                        f"Extracted version '{version}' from '{source}'"
                    )
                    return version
        
        logger.debug(f"No version found in path: {file_path}")
        return None
    
    def extract_batch(
        self,
        file_paths: list[Path]
    ) -> dict[Path, str | None]:
        """
        Extract versions for multiple files.
        
        Args:
            file_paths: List of file paths
        
        Returns:
            Dict mapping path to version (or None)
        """
        return {path: self.extract(path) for path in file_paths}
```

**Integration:**

Modify `ingest/core/file_scanner.py`:
```python
from ingest.core.version_extractor import VersionExtractor

class FileScanner:
    def __init__(self):
        # ... existing code ...
        self.version_extractor = VersionExtractor()
    
    def scan(self, docs_path: Path) -> list[dict]:
        files = []
        for file_path in self._scan_directory(docs_path):
            # ... existing metadata extraction ...
            
            # Extract version
            version = self.version_extractor.extract(file_path)
            if version:
                metadata['version'] = version
            
            files.append({'path': file_path, 'metadata': metadata})
        
        return files
```

Modify `server/vector_store.py`:
```python
class VectorStore:
    async def create_collection(self):
        # ... existing code ...
        
        # Add version to payload schema
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="version",
            field_schema=qmodels.TextIndexParams(
                type=qmodels.TextIndexType.KEYWORD,
                tokenizer=qmodels.TokenizerType.KEYWORD,
                lowercase=True
            )
        )
```

Modify `server/server.py` to support version filtering:
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_kb":
        # ... existing code ...
        version = arguments.get("version")
        
        # Build filter
        filter_conditions = []
        # ... existing filters ...
        if version:
            filter_conditions.append(
                qmodels.FieldCondition(
                    key="version",
                    match=qmodels.MatchValue(value=version)
                )
            )
```

**Tests:**

File: `tests/test_version_extractor.py` (~100 lines)

```python
"""Tests for version extraction."""

import pytest
from pathlib import Path

from ingest.core.version_extractor import VersionExtractor


class TestVersionExtractor:
    """Test version extraction logic."""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return VersionExtractor()
    
    def test_extract_from_filename_numeric(self, extractor):
        """Extract numeric version from filename."""
        path = Path("/docs/ArchiveCenter_22.3_Admin_Guide.pdf")
        assert extractor.extract(path) == "22.3"
    
    def test_extract_from_filename_ce_prefix(self, extractor):
        """Extract CE version from filename."""
        path = Path("/docs/manual_CE 24.4.pdf")
        assert extractor.extract(path) == "CE 24.4"
    
    def test_extract_from_filename_v_prefix(self, extractor):
        """Extract v-prefixed version from filename."""
        path = Path("/docs/release_notes_v2.5.pdf")
        assert extractor.extract(path) == "v2.5"
    
    def test_extract_from_parent_dir(self, extractor):
        """Extract version from parent directory."""
        path = Path("/docs/xECM/CE 24.4/manual.pdf")
        # Should extract from parent dir "CE 24.4"
        assert extractor.extract(path) == "CE 24.4"
    
    def test_extract_from_grandparent_dir(self, extractor):
        """Extract version from grandparent directory."""
        path = Path("/docs/v23.1/guides/admin.pdf")
        assert extractor.extract(path) == "v23.1"
    
    def test_no_version_found(self, extractor):
        """Return None when no version found."""
        path = Path("/docs/general/readme.pdf")
        assert extractor.extract(path) is None
    
    def test_version_keyword(self, extractor):
        """Extract version with 'version' keyword."""
        path = Path("/docs/Release Notes for version 16.2.pdf")
        assert extractor.extract(path) in ["version 16.2", "16.2"]
    
    def test_priority_filename_over_dir(self, extractor):
        """Filename version takes priority over directory."""
        path = Path("/docs/v22.3/manual_v24.4.pdf")
        # Filename "v24.4" should take priority
        assert extractor.extract(path) == "v24.4"
```

**Acceptance Criteria:**
- ✅ Extracts version from 90%+ of test filenames
- ✅ Priority: filename > parent dir > grandparent dir
- ✅ `version` field indexed in Qdrant
- ✅ Version filtering works in search_kb tool
- ✅ Returns None gracefully when no version found

---

## Feature 3: Metadata Overrides (_meta.json)

### Overview
Support per-directory metadata overrides via `_meta.json` files. Allows 
manual correction of auto-classification errors without restructuring 
directories.

### Implementation

**File:** `ingest/core/meta_loader.py` (~180 lines)

```python
"""
Load and apply metadata overrides from _meta.json files.

Supports directory-level defaults and file-specific overrides:

_meta.json schema:
{
  "product": "DefaultProduct",
  "doc_type": "default_doc_type",
  "files": {
    "specific_file.pdf": {
      "product": "OverrideProduct",
      "doc_type": "api_guide"
    }
  }
}

Precedence (highest to lowest):
1. File-specific override in _meta.json
2. Directory-level default in _meta.json
3. Auto-classification from metadata.py

Validation:
- product: must exist (any string allowed)
- doc_type: must be in VALID_DOC_TYPES list

Usage:
    loader = MetaLoader()
    meta = loader.load_meta(Path("/docs/xECM"))
    overrides = loader.get_metadata(
        Path("/docs/xECM/manual.pdf"),
        meta
    )
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MetaLoader:
    """Load metadata overrides from _meta.json files."""
    
    META_FILENAME = "_meta.json"
    
    VALID_DOC_TYPES = [
        "admin_guide",
        "install_guide",
        "upgrade_guide",
        "config_guide",
        "user_guide",
        "api_guide",
        "release_notes",
        "howto",
        "training",
        "overview",
        "reference",
        "standard",
        "meeting",
        "release_artifact",
        "document"
    ]
    
    def load_meta(self, directory: Path) -> dict:
        """
        Load _meta.json from directory.
        
        Args:
            directory: Directory to search for _meta.json
        
        Returns:
            Metadata dict (empty if file doesn't exist)
        
        Raises:
            ValueError: If metadata schema is invalid
        """
        meta_file = directory / self.META_FILENAME
        
        if not meta_file.exists():
            return {}
        
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in {meta_file}: {e}"
            ) from e
        
        # Validate schema
        self._validate_meta(meta, meta_file)
        
        logger.info(f"Loaded metadata overrides from {meta_file}")
        return meta
    
    def _validate_meta(self, meta: dict, meta_file: Path):
        """Validate _meta.json schema."""
        # Validate directory-level doc_type
        if "doc_type" in meta:
            if meta["doc_type"] not in self.VALID_DOC_TYPES:
                raise ValueError(
                    f"Invalid doc_type in {meta_file}: "
                    f"{meta['doc_type']} (must be one of "
                    f"{', '.join(self.VALID_DOC_TYPES)})"
                )
        
        # Validate file-specific overrides
        if "files" in meta:
            if not isinstance(meta["files"], dict):
                raise ValueError(
                    f"'files' must be a dict in {meta_file}"
                )
            
            for filename, overrides in meta["files"].items():
                if not isinstance(overrides, dict):
                    raise ValueError(
                        f"Overrides for '{filename}' must be a dict"
                    )
                
                if "doc_type" in overrides:
                    if overrides["doc_type"] not in self.VALID_DOC_TYPES:
                        raise ValueError(
                            f"Invalid doc_type for '{filename}' in "
                            f"{meta_file}: {overrides['doc_type']}"
                        )
    
    def get_metadata(
        self,
        file_path: Path,
        meta: dict
    ) -> dict:
        """
        Get metadata for file considering precedence.
        
        Args:
            file_path: File to get metadata for
            meta: Loaded _meta.json dict
        
        Returns:
            Dict with 'product' and 'doc_type' (or None if not set)
        """
        filename = file_path.name
        
        # File-specific override (highest priority)
        if "files" in meta and filename in meta["files"]:
            file_meta = meta["files"][filename]
            
            # File-specific overrides, fallback to directory defaults
            return {
                "product": file_meta.get(
                    "product",
                    meta.get("product")
                ),
                "doc_type": file_meta.get(
                    "doc_type",
                    meta.get("doc_type")
                )
            }
        
        # Directory-level defaults
        return {
            "product": meta.get("product"),
            "doc_type": meta.get("doc_type")
        }
    
    def scan_directory(
        self,
        directory: Path
    ) -> dict[Path, dict]:
        """
        Load all _meta.json files in directory tree.
        
        Args:
            directory: Root directory to scan
        
        Returns:
            Dict mapping directory path to loaded metadata
        """
        meta_map = {}
        
        for meta_file in directory.rglob(self.META_FILENAME):
            dir_path = meta_file.parent
            try:
                meta_map[dir_path] = self.load_meta(dir_path)
            except Exception as e:
                logger.error(f"Failed to load {meta_file}: {e}")
        
        logger.info(
            f"Loaded {len(meta_map)} _meta.json files from {directory}"
        )
        return meta_map
```

**Integration:**

Modify `ingest/core/file_scanner.py`:
```python
from ingest.core.meta_loader import MetaLoader

class FileScanner:
    def __init__(self):
        # ... existing code ...
        self.meta_loader = MetaLoader()
    
    def scan(self, docs_path: Path) -> list[dict]:
        # Load all _meta.json files
        meta_map = self.meta_loader.scan_directory(docs_path)
        
        files = []
        for file_path in self._scan_directory(docs_path):
            # ... existing metadata extraction ...
            
            # Apply _meta.json overrides
            for dir_path, meta in meta_map.items():
                if dir_path in file_path.parents or dir_path == file_path.parent:
                    overrides = self.meta_loader.get_metadata(file_path, meta)
                    
                    # Override auto-classification
                    if overrides.get('product'):
                        metadata['product'] = overrides['product']
                    if overrides.get('doc_type'):
                        metadata['doc_type'] = overrides['doc_type']
                    
                    break
            
            files.append({'path': file_path, 'metadata': metadata})
        
        return files
```

**Example _meta.json:**

```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    "special_manual.pdf": {
      "product": "xECM",
      "doc_type": "user_guide"
    },
    "release_notes.pdf": {
      "doc_type": "release_notes"
    }
  }
}
```

**Tests:**

File: `tests/test_meta_loader.py` (~150 lines)

```python
"""Tests for metadata loader."""

import pytest
import json
import tempfile
from pathlib import Path

from ingest.core.meta_loader import MetaLoader


class TestMetaLoader:
    """Test metadata loading and precedence."""
    
    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return MetaLoader()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_load_meta_not_exists(self, loader, temp_dir):
        """Return empty dict when _meta.json doesn't exist."""
        meta = loader.load_meta(temp_dir)
        assert meta == {}
    
    def test_load_meta_valid(self, loader, temp_dir):
        """Load valid _meta.json."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(json.dumps({
            "product": "TestProduct",
            "doc_type": "admin_guide"
        }))
        
        meta = loader.load_meta(temp_dir)
        assert meta["product"] == "TestProduct"
        assert meta["doc_type"] == "admin_guide"
    
    def test_validate_invalid_doc_type(self, loader, temp_dir):
        """Reject invalid doc_type."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(json.dumps({
            "doc_type": "invalid_type"
        }))
        
        with pytest.raises(ValueError, match="Invalid doc_type"):
            loader.load_meta(temp_dir)
    
    def test_precedence_file_specific(self, loader):
        """File-specific override takes precedence."""
        meta = {
            "product": "DirProduct",
            "doc_type": "admin_guide",
            "files": {
                "test.pdf": {
                    "product": "FileProduct",
                    "doc_type": "user_guide"
                }
            }
        }
        
        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)
        
        assert overrides["product"] == "FileProduct"
        assert overrides["doc_type"] == "user_guide"
    
    def test_precedence_directory_default(self, loader):
        """Directory default used when no file-specific."""
        meta = {
            "product": "DirProduct",
            "doc_type": "admin_guide"
        }
        
        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)
        
        assert overrides["product"] == "DirProduct"
        assert overrides["doc_type"] == "admin_guide"
    
    def test_partial_file_override(self, loader):
        """File can override doc_type only, inherit product."""
        meta = {
            "product": "DirProduct",
            "doc_type": "admin_guide",
            "files": {
                "test.pdf": {
                    "doc_type": "user_guide"
                }
            }
        }
        
        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)
        
        assert overrides["product"] == "DirProduct"
        assert overrides["doc_type"] == "user_guide"
```

**Acceptance Criteria:**
- ✅ `_meta.json` loaded and validated correctly
- ✅ Precedence works: file-specific > directory > auto
- ✅ Validation rejects invalid doc_type values
- ✅ Manual overrides take priority over classification
- ✅ Partial overrides work (e.g., doc_type only)

---

## Integration Points

### 1. File Scanner
- Load `_meta.json` files during scan
- Apply overrides before auto-classification
- Extract version from path

### 2. Document Processor
- Receive metadata with overrides applied
- Include version in Qdrant payload

### 3. Vector Store
- Create payload index for `version` field
- Support version filtering in queries

### 4. MCP Server
- Add `version` parameter to search_kb tool
- Document version filtering in tool description

### 5. Job Manager
- Accept file-specific ingestion jobs from watcher
- Track auto-triggered vs manual jobs

---

## Testing Strategy

### Unit Tests (~400 lines total)
- `test_file_watcher.py`: Debouncer, event handling, ignore patterns
- `test_version_extractor.py`: Regex patterns, priority, edge cases
- `test_meta_loader.py`: Loading, validation, precedence

### Integration Tests (~200 lines)
- `test_auto_ingestion.py`: Create file → watcher → job → ingestion
- `test_version_search.py`: Ingest with version → search with filter
- `test_meta_override.py`: Override classification via _meta.json

### E2E Test Scenarios
1. Add new file to watched directory → auto-ingested within 30s
2. Modify file multiple times in 30s → single job created
3. Version extracted from filename and searchable
4. _meta.json overrides auto-classification correctly
5. Watcher service restarts after crash

---

## Migration Guide

### For Existing Deployments

**Step 1: Install Dependencies**
```bash
# Add to requirements.in
watchdog>=3.0.0

# Compile and sync
pip-compile requirements.in
pip-sync requirements.txt
```

**Step 2: Update Environment**
```bash
# Add to .env
WATCH_PATH=/path/to/docs
WATCH_DEBOUNCE_SECONDS=30
WATCH_IGNORE_PATTERNS=.tmp,.swp,.~,~$*
WATCH_RECURSIVE=true
```

**Step 3: Deploy Watcher Service**
```bash
# Copy service file
sudo cp deployment/systemd/kb-rag-watcher.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable kb-rag-watcher
sudo systemctl start kb-rag-watcher

# Check status
sudo systemctl status kb-rag-watcher
```

**Step 4: Re-index for Version Field**
```bash
# Re-ingest existing documents to add version field
kb-rag ingest /path/to/docs --force

# Or trigger incremental update by touching files
find /path/to/docs -name "*.pdf" -exec touch {} +
```

**Step 5: Create _meta.json (Optional)**
```bash
# Example: Override classification for specific directory
cat > /path/to/docs/xECM/_meta.json <<EOF
{
  "product": "xECM",
  "doc_type": "admin_guide",
  "files": {
    "special_manual.pdf": {
      "doc_type": "user_guide"
    }
  }
}
EOF
```

### Backward Compatibility

- ✅ All features are opt-in
- ✅ Watcher service is optional (existing manual workflow still works)
- ✅ Version field is optional (searches work without it)
- ✅ _meta.json is optional (auto-classification fallback)
- ✅ No breaking changes to APIs or CLI

---

## Documentation

### User Guides
- `docs/AUTO_INGESTION.md`: Watcher setup and configuration
- `docs/METADATA_OVERRIDES.md`: _meta.json schema and examples
- `docs/VERSION_FILTERING.md`: How to use version search

### Operator Guides
- `deployment/systemd/README.md`: Service management
- `docs/TROUBLESHOOTING.md`: Add watcher debugging section

### API Documentation
- Update MCP tool descriptions with version parameter
- Add examples of version filtering to README

---

## Performance Characteristics

### File Watcher
- **Latency:** 30s debounce window (configurable)
- **Memory:** ~50MB baseline + 1KB per watched file
- **CPU:** <1% idle, 5-10% during events
- **I/O:** Minimal (event-driven, not polling)

### Version Extraction
- **Latency:** <1ms per file (regex matching)
- **Accuracy:** 90%+ on typical documentation filenames
- **Fallback:** None needed (returns None gracefully)

### Metadata Loading
- **Latency:** <10ms to load _meta.json per directory
- **Memory:** ~1KB per _meta.json file
- **Validation:** O(n) where n = number of file overrides

---

## Rollout Plan

### Day 1-2: Core Implementation
- Implement `file_watcher.py` with debouncer
- Implement `version_extractor.py` with regex patterns
- Implement `meta_loader.py` with validation
- Unit tests (70%+ coverage)

### Day 3-4: Integration
- Integrate with FileScanner
- Integrate with VectorStore (payload index)
- Integrate with MCP server (version parameter)
- Integration tests

### Day 5: systemd Service
- Create `kb-rag-watcher.service`
- Update `kb-rag.target` to include watcher
- Test service lifecycle (start/stop/restart)
- Document deployment steps

### Day 6: Documentation
- Write `AUTO_INGESTION.md`
- Write `METADATA_OVERRIDES.md`
- Write `VERSION_FILTERING.md`
- Update README with new features

### Day 7: QA & Release
- E2E testing with real documents
- Performance validation
- Create `PHASE13_COMPLETION.md`
- Tag v0.11.0-dev
- Update CHANGELOG

---

## Success Metrics

### Functionality
- ✅ Watcher detects 100% of file changes within 30s
- ✅ Version extracted from 90%+ of test files
- ✅ _meta.json overrides work in 100% of cases
- ✅ No crashes during 24h stress test

### Performance
- ✅ Watcher uses <512MB memory under load
- ✅ Version extraction <1ms per file
- ✅ Metadata loading <10ms per directory

### Quality
- ✅ 70%+ test coverage maintained
- ✅ All integration tests passing
- ✅ Zero breaking changes to existing APIs

### Documentation
- ✅ 3+ comprehensive user guides
- ✅ Deployment instructions clear and tested
- ✅ Troubleshooting scenarios documented

---

## Risks & Mitigation

### Risk 1: Watcher Crashes
**Mitigation:**
- systemd Restart=always
- Comprehensive error handling
- Health check integration

### Risk 2: Version Regex Mismatches
**Mitigation:**
- 90% target (not 100%)
- Extensive test coverage with real filenames
- Manual override via _meta.json

### Risk 3: _meta.json Conflicts
**Mitigation:**
- Clear precedence rules documented
- Validation with helpful error messages
- CLI command to validate all _meta.json files

### Risk 4: High File Churn
**Mitigation:**
- 30s debounce window
- Job queue with rate limiting (existing)
- Resource limits in systemd service

---

## Future Enhancements (Post-PHASE 13)

### PHASE 14+
- Delete handling (remove from Qdrant when file deleted)
- Move detection (avoid re-processing on renames)
- Batch validation for all _meta.json files
- Web UI to edit _meta.json via browser
- Advanced version comparison (semantic versioning)
- Version ranges in search (e.g., ">=22.3")

---

## Appendix: File Structure

```
kb-rag-mcp/
├── ingest/
│   ├── watcher/
│   │   ├── __init__.py
│   │   └── file_watcher.py          # NEW: Filesystem watcher
│   └── core/
│       ├── version_extractor.py     # NEW: Version extraction
│       ├── meta_loader.py           # NEW: _meta.json loader
│       ├── file_scanner.py          # MODIFIED: Integrate extractors
│       └── metadata.py              # MODIFIED: Use overrides
├── deployment/
│   └── systemd/
│       ├── kb-rag-watcher.service   # NEW: Watcher systemd service
│       └── kb-rag.target            # MODIFIED: Add watcher dependency
├── tests/
│   ├── test_file_watcher.py         # NEW: Watcher tests
│   ├── test_version_extractor.py    # NEW: Version tests
│   ├── test_meta_loader.py          # NEW: Metadata tests
│   └── e2e/
│       └── test_auto_ingestion.py   # NEW: E2E watcher test
├── docs/
│   ├── PHASE13_PLAN.md               # THIS FILE
│   ├── PHASE13_COMPLETION.md         # Created at end
│   ├── AUTO_INGESTION.md            # NEW: User guide
│   ├── METADATA_OVERRIDES.md        # NEW: _meta.json guide
│   └── VERSION_FILTERING.md         # NEW: Version search guide
└── requirements.in                   # MODIFIED: Add watchdog
```

**Total New Files:** 11  
**Total Modified Files:** 7  
**Estimated Lines:** ~1,800 (900 code + 600 tests + 300 docs)

---

## Conclusion

PHASE 13 delivers automated ingestion workflows that significantly reduce 
manual intervention. The three features (watcher, version extraction, 
metadata overrides) work together seamlessly while maintaining full 
backward compatibility.

Key achievements:
- ✅ Auto-detection via watchdog with 30s debounce
- ✅ Version extraction with 90%+ accuracy
- ✅ Flexible metadata overrides via _meta.json
- ✅ systemd service for production deployment
- ✅ Comprehensive tests and documentation
- ✅ Zero breaking changes

Ready to start implementation!

---

**Plan Status:** APPROVED  
**Next Action:** Begin Day 1-2 implementation (file_watcher.py)  
**Blocked By:** None  
**Dependencies:** watchdog>=3.0.0 (to be added)
