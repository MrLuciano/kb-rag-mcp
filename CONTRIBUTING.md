# Contributing to kb-rag-mcp

Thank you for contributing! This guide covers the most important contribution
rules for this project.

---

## Never Commit Secrets

This project handles embedding API keys, Qdrant credentials, and other secrets
via `.env` files. These files are **gitignored** and must never be committed.

The only committed reference is `config/.env.template` — a file with placeholder
values and no real credentials.

If you need a local config, copy the template:

```bash
cp config/.env.template .env
# then fill in your values in .env
```

---

## Removing Secrets from Git History

If secrets were accidentally committed in a previous commit, follow these steps
to scrub them from the entire git history.

> **Warning:** This rewrites history. Coordinate with your team before running on
> a shared branch. Everyone must re-clone or hard-reset after the rewrite.

### Prerequisites

Install `git-filter-repo` (requires Python 3):

```bash
pip install git-filter-repo
# or on macOS:
brew install git-filter-repo
```

Verify installation:

```bash
git filter-repo --version
```

### Step 1 — Work on a fresh clone

```bash
git clone --no-local <your-repo-url> kb-rag-mcp-clean
cd kb-rag-mcp-clean
```

### Step 2 — Remove env files from all history

```bash
git filter-repo --path .env --invert-paths
git filter-repo --path config/.env.local --invert-paths
git filter-repo --path config/.env.lxc --invert-paths
```

Each command rewrites all commits to remove that path. Run all three even if
only one file had secrets — the tool is idempotent.

### Step 3 — Remove files matching a pattern (optional)

If secrets may exist in other `.env`-style files:

```bash
git filter-repo --path-regex '^config/\.env\.' \
    --path-regex-invert '^config/\.env\.template$' \
    --invert-paths
```

### Step 4 — Verify the rewrite

```bash
git log --all --full-history -- .env
# Should return no commits
git ls-files | grep -i '\.env' | grep -v template
# Should return empty
```

### Step 5 — Force-push the cleaned history

```bash
git remote add origin <your-repo-url>
git push origin --force --all
git push origin --force --tags
```

### Step 6 — Invalidate old clones

Every team member must:

```bash
# Option A: fresh clone (recommended)
rm -rf kb-rag-mcp
git clone <your-repo-url>

# Option B: hard reset (if local changes must be preserved)
git fetch origin
git reset --hard origin/main
```

> Stale clones still have the old history in `.git/`. A fresh clone is the
> safest option.

---

## Code Style

- Python: `black` (line length 79), `isort` (black profile), `flake8`
- Run before committing:
  ```bash
  black . && isort . && flake8
  ```
- Tests: `pytest tests/ -x -q`
- All 268+ baseline tests must pass before opening a PR

---

## Pre-commit Hook (Recommended)

To prevent accidental secret commits, install a pre-commit hook:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml at project root with:
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
EOF

pre-commit install
```

This runs `gitleaks` on every commit and blocks pushes containing secrets.
