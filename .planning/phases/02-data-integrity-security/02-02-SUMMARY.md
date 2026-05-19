# Plan 02-02 Summary: Untrack .env Files and Document Secret Remediation

**Status:** DONE

## Files Changed

- `.gitignore` — added `# Environment / secrets` section with rules for `.env`, `.env.*`, `config/.env.*`; template exceptions preserved
- `config/.env.template` — created with safe placeholder values (no real credentials)
- `CONTRIBUTING.md` — created at project root with git-filter-repo remediation steps (Steps 1–6)
- `.env`, `config/.env.local`, `config/.env.lxc` — removed from git tracking (files remain on disk)

## Commit

`f69f6e6` — `chore: untrack .env files, add CONTRIBUTING.md (DATA-02, DATA-03)`

## Verification

- `git ls-files | grep '\.env' | grep -v template` → empty (no secret env files tracked)
- `config/.env.template` tracked and committed
- `.gitignore` contains `config/.env.*` and `!config/.env.template`
- Physical files `.env`, `config/.env.local`, `config/.env.lxc` remain on disk (only untracked)

## Concerns

None. All success criteria met.
