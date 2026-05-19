# Legacy and Extended Format Support

KB-RAG-MCP supports the following file formats beyond standard modern Office files.

## Supported Formats

| Extension | Format | Parser | Quality | Notes |
|---|---|---|---|---|
| `.doc` | Word 97-2003 | docx2txt → python-docx fallback | Good | Works when saved in compatibility mode |
| `.xls` | Excel 97-2003 | xlrd | Good | All sheets extracted as separate chunks |
| `.ppt` | PowerPoint 97-2003 | python-pptx (best-effort) | Partial | Binary `.ppt` may fail; save as `.pptx` for best results |
| `.odt` | OpenDocument Text | odfpy | Good | Full paragraph extraction |
| `.ods` | OpenDocument Spreadsheet | odfpy | Good | All sheets extracted as separate chunks |
| `.odp` | OpenDocument Presentation | odfpy | Good | Per-slide extraction |
| `.wpd` | WordPerfect | heuristic text strip | Low | No Python parser exists; raw latin-1 decode only |
| `.zip` | ZIP Archive | recursive (stdlib) | Good | Up to 2 levels of nesting; all supported types extracted |

## ZIP Extraction Rules

- **Max depth:** 2 levels (ZIP containing ZIP containing files — third level and deeper skipped)
- **Max entry size:** 500 MB per entry (larger entries skipped with a warning log)
- **Path metadata:** `source_path` in chunk payload records the relative path inside the archive
- **Unsupported types inside ZIP:** Skipped silently (`.exe`, `.dll`, `.bin`, etc.)
- **Nested ZIP at depth limit:** Logged at DEBUG level and skipped

## Dependencies

These packages must be installed (included in `requirements.txt`):

```bash
pip install docx2txt xlrd odfpy
```

They are listed in `requirements.in` and included in `requirements.txt`.

## Limitations

- **`.ppt` binary format** (pre-Office 2007) has no reliable Python parser. If extraction fails,
  the file is skipped with a warning. Re-save as `.pptx` for reliable extraction.
- **`.wpd` (WordPerfect)** extraction is heuristic — expect noise characters in complex documents.
  Only plain-text WordPerfect documents will produce usable output.
- **Encrypted or password-protected** files of any format are not supported and will
  produce an error log entry. The file is skipped and ingest continues.
- **`.xls` formulas** are evaluated to their cached values. If the original file had
  uncalculated formulas, cells may appear blank.
