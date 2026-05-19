"""
Validate a KB-RAG migration package (.tar.gz).

Checks:
- Package is a valid .tar.gz
- manifest.json is present
- All files listed in manifest are present
- SHA256 checksums match
"""
import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path


def validate_package(package_path: Path) -> dict:
    """
    Validate a migration package.

    Returns:
        {"valid": bool, "errors": list[str], "files": list[str]}
    """
    package_path = Path(package_path)
    errors = []
    files_found = []

    if not package_path.exists():
        return {"valid": False, "errors": [f"File not found: {package_path}"], "files": []}

    if not tarfile.is_tarfile(package_path):
        return {"valid": False, "errors": ["Not a valid tar file"], "files": []}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            with tarfile.open(package_path, "r:gz") as tar:
                safe_members = [
                    m for m in tar.getmembers()
                    if not os.path.isabs(m.name) and ".." not in m.name
                ]
                tar.extractall(tmp_path, members=safe_members)
        except Exception as e:
            return {"valid": False, "errors": [f"Extraction failed: {e}"], "files": []}

        manifest_path = tmp_path / "manifest.json"
        if not manifest_path.exists():
            return {"valid": False, "errors": ["manifest.json not found in package"], "files": []}

        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            return {"valid": False, "errors": [f"manifest.json invalid JSON: {e}"], "files": []}

        for filename, expected_hash in manifest.items():
            if filename == "manifest.json":
                continue  # manifest doesn't verify itself
            f = tmp_path / filename
            if not f.exists():
                errors.append(f"Missing file: {filename}")
                continue
            actual_hash = hashlib.sha256(f.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                errors.append(f"Checksum mismatch: {filename}")
            else:
                files_found.append(filename)

    if len(errors) == 0:
        files_found.append("manifest.json")
    return {"valid": len(errors) == 0, "errors": errors, "files": files_found}


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate a KB-RAG migration package")
    parser.add_argument("package", help="Path to .tar.gz package")
    args = parser.parse_args()

    result = validate_package(Path(args.package))
    if result["valid"]:
        print(f"[OK] Package valid. Files: {', '.join(result['files'])}")
        sys.exit(0)
    else:
        print("[FAIL] Package invalid:")
        for e in result["errors"]:
            print(f"  - {e}")
        sys.exit(1)
