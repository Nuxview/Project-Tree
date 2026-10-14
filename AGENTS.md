# Repository guidance

## Commands
- Setup: `uv sync --all-extras` (test/lint tools are in the `dev` extra, not a dependency group).
- Match CI order: `uv run ruff check .`, then `uv run ruff format --check .`, then `uv run pytest -v`. CI tests Python 3.10–3.13 after lint succeeds.
- Focused test: `uv run pytest tests/test_basic_tree.py::test_single_file`; substitute another file/node ID as needed.
- Run the local CLI: `uv run projtree --help` or `uv run python -m projtree.cli --help`; there is no package `__main__.py`.

## Behavior boundaries
- `projtree.cli:main` is the installed entrypoint; `argparse_main(argv)` returns an exit code and is the testable CLI API.
- `generate_markdown_tree` accepts a `Path` and returns Markdown without writing files. It uses only the passed ignore set: CLI and watcher independently merge defaults, `.projtreeignore`, and CLI extras and handle output exclusion/writes.
- Ignores match exact, case-sensitive names in any relative path segment, not globs or paths. Keep generator filtering and `ignore.is_ignored` behavior aligned. Path-based ignores in `docs/refactor.md` are deferred, not implemented.
- Relative `--output` paths (including default `structure.md`) are relative to the working directory, not the scanned root. CLI and watcher ignore the output basename only if output is under root; this excludes all matching names at any depth.
- Preserve directories-first, `casefold()`-sorted output and full Markdown formatting. `CONTRIBUTING.md` treats output changes as requiring a semver bump; retain v1 CLI and ignore-format compatibility.
- Watcher ignores ordinary `modified` events, but reloads `.projtreeignore` on its events. Regeneration is debounced and skips writes when content is unchanged.

## Verification and maintenance
- Tree-rendering tests assert complete Markdown output, not fragments. `tests/conftest.py` forces imports from this checkout rather than `build/lib` or an installed copy.
- `tests/test_watcher_basic.py` runs a real watchdog observer in a daemon thread with fixed sleeps; it is timing-sensitive and does not stop the watcher. CLI watch tests mock dispatch instead.
- `tests/test_internal_docs.py` checks module, public-function, and test-helper docstrings.
- CLI behavior changes also reach help text and `docs/usage.md`; keep `README.md` and `docs/architecture.md` consistent with behavior. The architecture document's example API signature/layout are stale; use source for exact interfaces.
- Version comes from installed `project-tree` metadata, falling back to `0.0.0-dev`; edit `pyproject.toml`, not a hardcoded package version. Release CI runs `uv build` and requires the built version to match the release tag (optional `v` prefix).
- `.github/workflows/changelog.yml` automatically prepends `CHANGELOG.md` entries after PR merges. `.gitignore` ignores new Markdown files unless explicitly allowlisted, plus the local `.projtreeignore`.
