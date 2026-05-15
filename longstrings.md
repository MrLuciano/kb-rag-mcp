# Long Lines (E501) - Manual Fix Required

**Date**: 2026-05-15  
**Status**: Deferred for manual handling

## Overview

The following files contain lines exceeding 79 characters (flake8 E501).
These are primarily docstrings, comments, and string literals that Black's
auto-formatter does not break automatically.

## Files Affected

### server/server.py (26 lines)

| Line | Length | Context |
|------|--------|---------|
| 48   | 80     | Comment or docstring |
| 81   | 115    | Comment or docstring |
| 82   | 82     | Comment or docstring |
| 83   | 89     | Comment or docstring |
| 84   | 112    | Comment or docstring |
| 85   | 95     | Comment or docstring |
| 97   | 83     | Comment or docstring |
| 105  | 91     | Comment or docstring |
| 106  | 93     | Comment or docstring |
| 113  | 83     | Comment or docstring |
| 114  | 89     | Comment or docstring |
| 115  | 81     | Comment or docstring |
| 116  | 83     | Comment or docstring |
| 117  | 86     | Comment or docstring |
| 124  | 106    | Comment or docstring |
| 135  | 90     | Comment or docstring |
| 143  | 93     | Comment or docstring |
| 152  | 95     | Comment or docstring |
| 157  | 86     | Comment or docstring |
| 167  | 93     | Comment or docstring |
| 168  | 87     | Comment or docstring |
| 175  | 80     | Comment or docstring |
| 179  | 98     | Comment or docstring |
| 190  | 117    | Comment or docstring |
| 237  | 107    | Comment or docstring |
| 253  | 86     | Comment or docstring |

**Command to reproduce:**
```bash
.venv/bin/flake8 server/server.py --select=E501
```

### server/vector_store.py (5 lines)

| Line | Length | Context |
|------|--------|---------|
| 68   | 80     | Comment or docstring |
| 78   | 86     | Comment or docstring |
| 171  | 80     | Comment or docstring |
| 236  | 85     | Comment or docstring |
| 281  | 80     | Comment or docstring |

**Command to reproduce:**
```bash
.venv/bin/flake8 server/vector_store.py --select=E501
```

## Impact Assessment

- **Severity**: Low (cosmetic only)
- **Functional Impact**: None
- **Type Safety**: Not affected
- **Test Coverage**: Not affected
- **Blocking**: No - does not block FASE 2

## Manual Fix Guidelines

When addressing these lines manually:

1. **For docstrings**: Break into multiple lines at natural phrase boundaries
2. **For comments**: Split at logical points, maintain readability
3. **For string literals**: Use implicit string concatenation or parenthesized multi-line strings
4. **Run after each fix**: `.venv/bin/flake8 <file>` and `.venv/bin/black <file>`

## Example Fixes

### Before:
```python
def example():
    """This is a very long docstring that exceeds the 79 character limit and needs to be wrapped."""
    pass
```

### After:
```python
def example():
    """
    This is a very long docstring that exceeds the 79 character limit
    and needs to be wrapped.
    """
    pass
```

## Resolution Plan

These issues are tracked for manual resolution in a future hygiene pass.
They do not block progression to FASE 2 (async/concurrency improvements).

---

**Total lines to fix**: 31 (26 in server.py, 5 in vector_store.py)
