# Metadata Overrides with _meta.json

**FASE 13 Feature**

Override automatic classification with per-directory and per-file metadata.

---

## Overview

The metadata override system allows you to manually specify product and doc_type classifications using `_meta.json` files placed in your documentation directories. This is useful when:

- Automatic classification is incorrect
- Documents lack clear naming patterns
- Multiple products share a directory
- Document types are ambiguous

### Key Features

- **Directory-level defaults**: Apply metadata to all files in a directory
- **File-specific overrides**: Target individual files with custom metadata
- **Precedence rules**: File-specific > directory > CLI > auto-classification
- **Validation**: Ensures doc_type values are valid
- **Flexible products**: Any product name accepted
- **Backward compatible**: Auto-classification still works without _meta.json

---

## Quick Start

### 1. Create a _meta.json File

In any documentation directory:

```bash
cd /path/to/docs/ArchiveCenter_22.3
nano _meta.json
```

```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide"
}
```

### 2. Apply to Specific Files

Override individual files within the directory:

```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    "installation_guide.pdf": {
      "doc_type": "installation_guide"
    },
    "troubleshooting.pdf": {
      "product": "ArchiveCenter Enterprise",
      "doc_type": "troubleshooting_guide"
    }
  }
}
```

### 3. Ingest with Overrides

```bash
# Overrides are automatically detected during ingestion
kb-rag ingest /path/to/docs/ArchiveCenter_22.3

# Check classifications
kb-rag query "installation" --product "ArchiveCenter"
```

---

## File Format

### Basic Structure

```json
{
  "product": "string (optional)",
  "doc_type": "string (optional)",
  "files": {
    "filename.pdf": {
      "product": "string (optional)",
      "doc_type": "string (optional)"
    }
  }
}
```

### Complete Example

```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    "install.pdf": {
      "doc_type": "installation_guide"
    },
    "config.pdf": {
      "doc_type": "configuration_guide"
    },
    "reference.pdf": {
      "doc_type": "reference"
    }
  }
}
```

---

## Valid doc_type Values

The system validates `doc_type` against a predefined list:

### Supported Types

```python
VALID_DOC_TYPES = [
    "admin_guide",           # Administrator's guide
    "user_guide",            # End-user manual
    "installation_guide",    # Installation instructions
    "configuration_guide",   # Configuration reference
    "api_reference",         # API documentation
    "release_notes",         # Version release notes
    "troubleshooting_guide", # Problem-solving guide
    "security_guide",        # Security documentation
    "migration_guide",       # Migration/upgrade guide
    "best_practices",        # Best practices guide
    "reference",             # General reference
    "quickstart",            # Quick start guide
    "tutorial",              # Step-by-step tutorial
    "faq",                   # Frequently asked questions
    "glossary",              # Terms and definitions
    "architecture",          # Architecture documentation
    "deployment_guide",      # Deployment instructions
    "developer_guide",       # Developer documentation
    "integration_guide",     # Integration documentation
    "operations_guide"       # Operations manual
]
```

### Product Validation

**Product names are not validated** - any string is accepted. This allows flexibility for:
- Internal product codes
- Multiple product variants
- Custom naming conventions

---

## Precedence Rules

When multiple sources provide metadata, the system uses this priority:

```
1. File-specific override in _meta.json (highest)
2. Directory default in _meta.json
3. CLI override (--product, --doc-type)
4. Auto-classification (lowest)
```

### Example Precedence

**Directory structure:**
```
/docs/
  _meta.json          → product: "ArchiveCenter"
  manual.pdf
  install.pdf
```

**_meta.json:**
```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    "install.pdf": {
      "doc_type": "installation_guide"
    }
  }
}
```

**CLI command:**
```bash
kb-rag ingest /docs --product "Override"
```

**Result:**
- `manual.pdf`:
  - product: "ArchiveCenter" (from _meta.json directory default)
  - doc_type: "admin_guide" (from _meta.json directory default)
  
- `install.pdf`:
  - product: "ArchiveCenter" (from _meta.json directory default)
  - doc_type: "installation_guide" (from _meta.json file-specific)

**CLI override ignored** because _meta.json takes precedence.

---

## Usage Scenarios

### Scenario 1: Mixed Document Types

**Problem:** Directory contains multiple document types

**Solution:** Use file-specific overrides

```json
{
  "product": "ArchiveCenter",
  "files": {
    "AC_Admin_Guide_v22.3.pdf": {
      "doc_type": "admin_guide"
    },
    "AC_User_Guide_v22.3.pdf": {
      "doc_type": "user_guide"
    },
    "AC_Install_v22.3.pdf": {
      "doc_type": "installation_guide"
    },
    "AC_Release_Notes_v22.3.pdf": {
      "doc_type": "release_notes"
    }
  }
}
```

### Scenario 2: Shared Directory

**Problem:** Multiple products in same directory

**Solution:** Override product per file

```json
{
  "files": {
    "product_a_manual.pdf": {
      "product": "Product A",
      "doc_type": "user_guide"
    },
    "product_b_manual.pdf": {
      "product": "Product B",
      "doc_type": "user_guide"
    },
    "shared_reference.pdf": {
      "product": "Platform Common",
      "doc_type": "reference"
    }
  }
}
```

### Scenario 3: Ambiguous Filenames

**Problem:** Generic filenames don't indicate content

**Solution:** Explicit classification

```json
{
  "product": "ArchiveCenter",
  "files": {
    "manual.pdf": {
      "doc_type": "admin_guide"
    },
    "guide.pdf": {
      "doc_type": "user_guide"
    },
    "reference.pdf": {
      "doc_type": "api_reference"
    }
  }
}
```

### Scenario 4: Nested Directories

**Problem:** Subdirectories need different metadata

**Solution:** Multiple _meta.json files

```
/docs/
  ArchiveCenter/
    _meta.json         → product: "ArchiveCenter"
    22.3/
      _meta.json       → doc_type: "admin_guide"
      admin_guide.pdf
    23.1/
      _meta.json       → doc_type: "user_guide"
      user_guide.pdf
```

**ArchiveCenter/_meta.json:**
```json
{
  "product": "ArchiveCenter"
}
```

**22.3/_meta.json:**
```json
{
  "doc_type": "admin_guide"
}
```

**Result:**
- `22.3/admin_guide.pdf`:
  - product: "ArchiveCenter" (inherited from parent)
  - doc_type: "admin_guide" (from local _meta.json)

### Scenario 5: Enterprise Editions

**Problem:** Differentiate Enterprise vs Standard editions

**Solution:** Product variants

```json
{
  "files": {
    "standard_guide.pdf": {
      "product": "ArchiveCenter Standard",
      "doc_type": "user_guide"
    },
    "enterprise_guide.pdf": {
      "product": "ArchiveCenter Enterprise",
      "doc_type": "user_guide"
    },
    "enterprise_admin.pdf": {
      "product": "ArchiveCenter Enterprise",
      "doc_type": "admin_guide"
    }
  }
}
```

---

## Best Practices

### 1. Use Directory Defaults for Consistency

**Good:**
```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    "special.pdf": {
      "doc_type": "reference"
    }
  }
}
```

**Why:** All files default to admin_guide, only exceptions need overrides.

**Bad:**
```json
{
  "files": {
    "file1.pdf": {"product": "ArchiveCenter", "doc_type": "admin_guide"},
    "file2.pdf": {"product": "ArchiveCenter", "doc_type": "admin_guide"},
    "file3.pdf": {"product": "ArchiveCenter", "doc_type": "admin_guide"}
  }
}
```

**Why:** Repetitive, error-prone, hard to maintain.

### 2. Minimal Overrides

Only override what's necessary:

```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    "install.pdf": {
      "doc_type": "installation_guide"
      // No need to repeat "product"
    }
  }
}
```

### 3. Validate Before Ingestion

```bash
# Test classification
python3 << EOF
from ingest.core.meta_loader import load_meta
meta = load_meta("/path/to/docs/_meta.json")
print(meta)
EOF
```

### 4. Document Your Overrides

Add comments (JSON5 style, if using parser that supports it):

```json
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide",
  "files": {
    // Installation guide has different doc_type
    "AC_Install_22.3.pdf": {
      "doc_type": "installation_guide"
    },
    // Legacy filename, actually API reference
    "reference.pdf": {
      "doc_type": "api_reference"
    }
  }
}
```

**Note:** Standard JSON doesn't support comments. Use a separate README or this format for documentation, but strip comments for actual _meta.json.

### 5. Test After Changes

```bash
# Force re-ingest after changing _meta.json
kb-rag ingest /path/to/docs --force

# Verify classifications
kb-rag query "test" --product "ArchiveCenter" --limit 5
```

---

## Validation and Errors

### Validation Rules

The system validates _meta.json files during ingestion:

1. **JSON Syntax**: Must be valid JSON
2. **doc_type Values**: Must be in `VALID_DOC_TYPES` list
3. **Structure**: Must match expected format
4. **Files Object**: Must be a dict if present

### Common Errors

#### Invalid JSON

**Error:**
```
ERROR: Invalid JSON in _meta.json: Expecting ',' delimiter
```

**Fix:**
```json
// Bad
{
  "product": "ArchiveCenter"  // Missing comma
  "doc_type": "admin_guide"
}

// Good
{
  "product": "ArchiveCenter",
  "doc_type": "admin_guide"
}
```

#### Invalid doc_type

**Error:**
```
ERROR: Invalid doc_type 'administrator_guide' in _meta.json
Valid types: admin_guide, user_guide, ...
```

**Fix:**
```json
// Bad
{
  "doc_type": "administrator_guide"
}

// Good
{
  "doc_type": "admin_guide"
}
```

#### Invalid Structure

**Error:**
```
ERROR: 'files' must be a dict in _meta.json
```

**Fix:**
```json
// Bad
{
  "files": ["file1.pdf", "file2.pdf"]
}

// Good
{
  "files": {
    "file1.pdf": {"doc_type": "admin_guide"},
    "file2.pdf": {"doc_type": "user_guide"}
  }
}
```

### Error Handling

**During ingestion:**
- Invalid _meta.json files are logged and skipped
- Ingestion continues with auto-classification
- Files with invalid overrides use directory defaults or auto-classification

**Example:**
```
WARNING: Invalid _meta.json in /docs/dir1: Invalid doc_type 'guide'
INFO: Falling back to auto-classification for /docs/dir1
```

---

## Advanced Usage

### Conditional Overrides

Use directory structure to apply overrides conditionally:

```
/docs/
  current/
    _meta.json  → {"product": "ArchiveCenter 23.1"}
  archive/
    22.3/
      _meta.json  → {"product": "ArchiveCenter 22.3"}
    22.2/
      _meta.json  → {"product": "ArchiveCenter 22.2"}
```

### Partial Overrides

Override only product or doc_type, not both:

```json
{
  "doc_type": "admin_guide",
  // Product determined by auto-classification
  "files": {
    "special.pdf": {
      "product": "Special Edition"
      // doc_type inherited from directory default
    }
  }
}
```

### Bulk Generation

Generate _meta.json programmatically for large directories:

```python
import json
from pathlib import Path

docs_dir = Path("/path/to/docs")
meta = {
    "product": "ArchiveCenter",
    "doc_type": "admin_guide",
    "files": {}
}

for pdf_file in docs_dir.glob("*.pdf"):
    if "install" in pdf_file.stem.lower():
        meta["files"][pdf_file.name] = {
            "doc_type": "installation_guide"
        }

with open(docs_dir / "_meta.json", "w") as f:
    json.dump(meta, f, indent=2)
```

### Migration from Auto-classification

**Step 1:** Audit current classifications

```bash
# Export current classifications
kb-rag query "" --limit 1000 > current_classifications.json
```

**Step 2:** Identify incorrect classifications

```python
import json

with open("current_classifications.json") as f:
    results = json.load(f)

for chunk in results:
    if chunk["product"] != "Expected Product":
        print(f"Fix: {chunk['file']} -> {chunk['product']}")
```

**Step 3:** Create _meta.json files

```bash
# For each directory with issues
cd /docs/problematic_dir
nano _meta.json
# Add overrides
```

**Step 4:** Re-ingest with overrides

```bash
kb-rag ingest /docs --force
```

---

## Troubleshooting

### Overrides Not Applied

**Symptom:** Files still use auto-classification despite _meta.json

**Check:**
1. **File named correctly**: Must be exactly `_meta.json`
   ```bash
   ls -la _meta.json  # Not meta.json or _meta.txt
   ```

2. **JSON valid**: Use validator
   ```bash
   python3 -m json.tool _meta.json
   ```

3. **Filename matches**: Case-sensitive
   ```json
   // If file is "Manual.pdf"
   {
     "files": {
       "Manual.pdf": {...}  // Not "manual.pdf"
     }
   }
   ```

4. **Re-ingest with --force**:
   ```bash
   kb-rag ingest /path/to/docs --force
   ```

### Precedence Confusion

**Symptom:** CLI override doesn't work

**Explanation:** _meta.json takes precedence over CLI

**Fix:** Either:
- Remove _meta.json to use CLI
- Update _meta.json with correct values

### Validation Errors

**Symptom:** Invalid doc_type warning

**Check:**
```bash
# View valid types
python3 << EOF
from ingest.validation.doc_type_validator import DocTypeValidator
validator = DocTypeValidator()
print(validator.valid_types)
EOF
```

**Fix:** Use exact type from list (case-sensitive)

### Missing Overrides in Subdirectories

**Symptom:** Only root directory overrides work

**Explanation:** _meta.json files are per-directory, not recursive

**Fix:** Create _meta.json in each subdirectory that needs overrides:

```bash
# Create for each subdirectory
find /docs -type d -exec bash -c '
  cd "$1" && 
  echo "{\"product\": \"ArchiveCenter\"}" > _meta.json
' _ {} \;
```

---

## API Reference

### load_meta(meta_path)

Load and validate a _meta.json file.

**Parameters:**
- `meta_path` (str | Path): Path to _meta.json file

**Returns:**
- `dict | None`: Metadata dict or None if invalid

**Example:**
```python
from ingest.core.meta_loader import load_meta

meta = load_meta("/docs/_meta.json")
if meta:
    print(f"Product: {meta.get('product')}")
    print(f"Doc Type: {meta.get('doc_type')}")
```

### get_meta_for_file(meta_path, filename)

Get metadata for a specific file with precedence.

**Parameters:**
- `meta_path` (str | Path): Path to _meta.json file
- `filename` (str): Filename to get metadata for

**Returns:**
- `dict`: Metadata with file-specific overrides applied

**Example:**
```python
from ingest.core.meta_loader import get_meta_for_file

meta = get_meta_for_file("/docs/_meta.json", "install.pdf")
print(f"Product: {meta.get('product')}")
print(f"Doc Type: {meta.get('doc_type')}")
```

### MetaLoader.scan_directory(docs_path)

Scan directory tree for all _meta.json files.

**Parameters:**
- `docs_path` (str | Path): Root directory to scan

**Returns:**
- `dict`: Mapping of directory paths to metadata

**Example:**
```python
from ingest.core.meta_loader import MetaLoader

loader = MetaLoader()
all_meta = loader.scan_directory("/docs")

for dir_path, meta in all_meta.items():
    print(f"{dir_path}: {meta.get('product')}")
```

---

## Migration from FASE 12

### Breaking Changes

**None.** Metadata overrides are additive - existing ingestion still works.

### New Features

- `_meta.json` support (opt-in)
- Per-file metadata overrides
- Validation of doc_type values

### Upgrade Path

1. Upgrade to v0.11.0-dev
2. Optionally add _meta.json files
3. Re-ingest directories with overrides

**No action required** if auto-classification works for you.

---

## Performance Impact

### Load Time

- **Per _meta.json file**: <10ms
- **Per 100 files**: <50ms overhead
- **Negligible** for typical directories (<1000 files)

### Memory Usage

- **Per _meta.json**: ~1KB
- **Per 100 files with overrides**: ~10KB
- **Minimal** compared to document processing

### Disk I/O

- **Read only**: _meta.json files read once per ingestion
- **No writes**: System doesn't modify _meta.json
- **Cached**: Metadata cached during single ingestion run

---

## FAQ

**Q: Do I need _meta.json files?**  
A: No. They're optional for overriding auto-classification when needed.

**Q: Can I mix auto-classification and overrides?**  
A: Yes. Files without overrides use auto-classification.

**Q: What happens if _meta.json is invalid?**  
A: The file is skipped with a warning, and auto-classification is used.

**Q: Can I use comments in _meta.json?**  
A: No, standard JSON doesn't support comments. Keep documentation separate.

**Q: How do I override product but keep auto doc_type?**  
A: Only specify `"product"` in _meta.json, omit `"doc_type"`.

**Q: Does _meta.json apply to subdirectories?**  
A: No, it only applies to files in the same directory. Create _meta.json in each subdirectory.

**Q: Can I validate _meta.json before ingestion?**  
A: Yes, use `python3 -m json.tool _meta.json` or the API functions.

**Q: What if file-specific override conflicts with directory default?**  
A: File-specific always wins (highest precedence).

**Q: How do I remove overrides?**  
A: Delete _meta.json and re-ingest with `--force`.

**Q: Can I use wildcards in filename overrides?**  
A: No, filenames must be exact matches (case-sensitive).

---

## See Also

- [Auto Ingestion](AUTO_INGESTION.md) - Automatic file watching
- [Version Filtering](VERSION_FILTERING.md) - Search by document version
- [Classification System](../README.md#classification) - How auto-classification works
- [Validation](../README.md#validation) - Input validation rules

---

**FASE 13 Feature** | Last Updated: 2026-05-16 | [Report Issues](https://github.com/MrLuciano/kb-rag-mcp/issues)
