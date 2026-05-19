"""
Recursive ZIP archive extractor.

Extracts files from .zip archives up to 2 levels of nesting.
Reuses EXTRACTORS from ingest.ingest for all extracted files.
Skips entries > 500 MB.

Returns list[dict] with keys:
    text: str       — extracted text
    page: int|None  — page/sheet (from underlying extractor)
    source_path: str — relative path inside archive (for metadata)
"""
import logging
import tempfile
import zipfile
from pathlib import Path

log = logging.getLogger("kb-ingest.parsers.zip")

MAX_ENTRY_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_DEPTH = 2


def extract_zip(path: Path, _depth: int = 0) -> list[dict]:
    """
    Extract all supported files from a ZIP archive recursively.

    Args:
        path: Path to .zip file
        _depth: Internal recursion depth counter (do not set manually)

    Returns:
        list[dict] with text, page, source_path keys
    """
    # Lazy import to avoid circular dependency — ingest.ingest imports parsers
    from ingest.ingest import EXTRACTORS, EXT_TYPE_MAP

    path = Path(path)
    if not path.exists():
        return []

    if _depth >= MAX_DEPTH:
        log.debug(f"  ZIP max depth {MAX_DEPTH} reached, skipping {path.name}")
        return []

    if not zipfile.is_zipfile(path):
        log.warning(f"  Not a valid ZIP file: {path.name}")
        return []

    results = []

    try:
        with zipfile.ZipFile(path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                if info.file_size > MAX_ENTRY_BYTES:
                    log.warning(
                        f"  Skipping oversized entry {info.filename} "
                        f"({info.file_size / 1024 / 1024:.0f} MB > 500 MB limit)"
                    )
                    continue

                entry_path = Path(info.filename)
                entry_ext = entry_path.suffix.lower()

                # Nested ZIP — recurse
                if entry_ext == ".zip" and _depth + 1 < MAX_DEPTH:
                    with tempfile.TemporaryDirectory() as tmp:
                        extracted = Path(tmp) / entry_path.name
                        extracted.write_bytes(zf.read(info.filename))
                        nested = extract_zip(extracted, _depth=_depth + 1)
                        for item in nested:
                            item["source_path"] = f"{info.filename}/{item.get('source_path', '')}"
                        results.extend(nested)
                    continue

                # Supported format
                file_type = EXT_TYPE_MAP.get(entry_ext)
                if not file_type:
                    log.debug(f"  Skipping unsupported entry type: {info.filename}")
                    continue

                extractor = EXTRACTORS.get(file_type)
                if not extractor:
                    continue

                try:
                    with tempfile.TemporaryDirectory() as tmp:
                        extracted = Path(tmp) / entry_path.name
                        extracted.write_bytes(zf.read(info.filename))
                        items = extractor(extracted)
                        for item in items:
                            item["source_path"] = info.filename
                        results.extend(items)
                except Exception as e:
                    log.error(f"  Error extracting {info.filename} from ZIP: {e}")

    except Exception as e:
        log.error(f"  Error opening ZIP {path.name}: {e}")
        return []

    return results
