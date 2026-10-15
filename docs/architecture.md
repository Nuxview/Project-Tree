# Project Tree v1 Architecture

<!--toc:start-->
- [Project Tree v1 Architecture](#project-tree-v1-architecture)
  - [1. Purpose](#1-purpose)
  - [2. High-Level Overview](#2-high-level-overview)
  - [3. Directory Structure](#3-directory-structure)
    - [Directory and File Roles](#directory-and-file-roles)
  - [4. CLI Layer (cli.py)](#4-cli-layer-clipy)
    - [Responsibilities](#responsibilities)
    - [Interface (v1)](#interface-v1)
    - [Flag Semantics](#flag-semantics)
    - [Design Constraints (v1)](#design-constraints-v1)
  - [5. Generation Layer (generator.py)](#5-generation-layer-generatorpy)
    - [Role and Responsibilities](#role-and-responsibilities)
    - [Key Characteristics](#key-characteristics)
    - [Core API](#core-api)
  - [6. Ignore System (ignore.py)](#6-ignore-system-ignorepy)
    - [6.1 Purpose and Scope](#61-purpose-and-scope)
    - [6.2 Sources of Ignore Rules](#62-sources-of-ignore-rules)
    - [6.3 Resolution Order](#63-resolution-order)
    - [6.4 Matching Rules](#64-matching-rules)
    - [6.5 Directory vs File Behavior](#65-directory-vs-file-behavior)
    - [6.6 Output File Handling](#66-output-file-handling)
    - [6.7 Edge Cases and Clarifications](#67-edge-cases-and-clarifications)
      - [6.7.1 Conflicting Rules](#671-conflicting-rules)
      - [6.7.2 Empty or Missing Ignore Files](#672-empty-or-missing-ignore-files)
      - [6.7.3 Duplicate Entries](#673-duplicate-entries)
      - [6.7.4 Path-Like Entries](#674-path-like-entries)
    - [6.8 Interaction with the Watcher Layer](#68-interaction-with-the-watcher-layer)
    - [6.9 Non-Goals (v1)](#69-non-goals-v1)
    - [6.10 Core API](#610-core-api)
  - [7. Watcher Layer (watcher.py)](#7-watcher-layer-watcherpy)
    - [Function](#function)
    - [Definition: Structural Change (v1)](#definition-structural-change-v1)
    - [Debounce Behavior](#debounce-behavior)
    - [Non-Guarantees (Explicit)](#non-guarantees-explicit)
    - [Loop Prevention](#loop-prevention)
    - [Non-Goals (v1)](#non-goals-v1)
  - [8. Testing Strategy](#8-testing-strategy)
    - [8.1 Objectives](#81-objectives)
    - [8.2 Core Principle: Full-Output Assertion](#82-core-principle-full-output-assertion)
    - [8.3 Pure Logic vs Side Effects](#83-pure-logic-vs-side-effects)
    - [8.4 Watcher Testing Philosophy](#84-watcher-testing-philosophy)
    - [8.5 Justification for Minimal Watcher Tests](#85-justification-for-minimal-watcher-tests)
    - [8.6 CLI Testing Rules](#86-cli-testing-rules)
    - [8.7 Regression Lock-In](#87-regression-lock-in)
    - [8.8 Non-Goals](#88-non-goals)
    - [8.9 Summary](#89-summary)
  - [9. Design Philosophy](#9-design-philosophy)
  - [10. Deferred Features](#10-deferred-features)
  - [11. Versioning](#11-versioning)
  - [12. Summary](#12-summary)
<!--toc:end-->

## 1. Purpose

Project Tree is a small, deterministic utility that generates a Markdown representation of a project directory structure. The installed command is `projtree`. Its primary goals are:

- Produce stable, predictable output suitable for documentation and version control
- Respect common project ignore conventions
- Remain simple, inspectable, and testable
- Support optional watch mode for continuous regeneration

Version 1 (v1) intentionally limits scope to ensure correctness and reliability.

---

## 2. High-Level Overview

Project Tree consists of four core layers:

1. CLI Layer - Argument parsing and orchestration
2. Generation Layer - Read-only, deterministic logic for building Markdown output
3. Ignore System - Centralized ignore resolution
4. Watcher Layer - Optional filesystem monitoring

The design principle is separation of concerns: generation is read-only and deterministic, while I/O and side effects are isolated.

---

## 3. Directory Structure

Selected tracked files are shown below; local caches and build artifacts are omitted:

```text
.
├── .github
├── docs
│   ├── architecture.md
│   ├── refactor.md
│   └── usage.md
├── projtree
│   ├── __init__.py
│   ├── cli.py
│   ├── generator.py
│   ├── ignore.py
│   └── watcher.py
├── tests
│   ├── conftest.py
│   ├── test_basic_tree.py
│   ├── test_cli.py
│   ├── test_internal_docs.py
│   ├── test_watcher_basic.py
│   └── utils.py
├── .gitignore
├── .projtreeignore
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

### Directory and File Roles

`projtree/` - Core package implementation

- __init__.py: Reads the installed package version via `importlib.metadata`, with a `0.0.0-dev` fallback
- cli.py: Command-line interface entry point and argument parsing
- generator.py: Read-only, deterministic Markdown tree generation logic
- ignore.py: Ignore rule resolution (defaults + .projtreeignore)
- watcher.py: Optional filesystem watching using watchdog

`tests/` - Test suite

- conftest.py: Test environment setup (import paths)
- test_basic_tree.py: Verifies generator output correctness and determinism
- test_cli.py: CLI argument parsing and orchestration tests
- test_internal_docs.py: Module, function, and test-helper docstring checks
- test_watcher_basic.py: Event-handler regression tests and one live watcher smoke test
- utils.py: Shared helpers for test setup and assertions

`docs/` - Documentation

- architecture.md: Design overview and behavior
- refactor.md: Deferred refactor notes
- usage.md: CLI usage reference

Top-level files

- AGENTS.md: Repository-specific agent guidance
- CONTRIBUTING.md: Contribution and testing guidelines
- CHANGELOG.md: Historical PR summaries, updated by the merge workflow
- .gitignore: Git ignore rules for the repository
- .projtreeignore: Project-specific ignore rules consumed by Project Tree
- LICENSE: Project license
- README.md: Project overview and quickstart
- pyproject.toml: Packaging metadata, dependencies, and entry points
- uv.lock: Locked dependencies used by uv and CI

`.github/workflows/` contains CI, release publishing, PR labeling, and changelog automation.

---

## 4. CLI Layer (cli.py)

### Responsibilities

The CLI layer is responsible for all user-facing interaction and orchestration. It translates command-line arguments into well-defined actions without embedding any generation or watcher logic.

Specifically, the CLI:

- Parses and validates command-line arguments
- Resolves filesystem paths
- Aggregates ignore rules from all sources
- Dispatches execution to either one-shot generation or watch mode
- Handles user-facing errors and exit codes
- Exposes version information via -v / --version

---

### Interface (v1)

The CLI interface in v1 is intentionally compact and stable. The current help output is:

```text
usage: projtree [-h] [-v] [-o OUTPUT] [--ignore IGNORE] [--watch]
                [--watch-only]
                [path]

Generate a deterministic Markdown project tree.

positional arguments:
  path                  root directory of the project (default: current
                        directory)

options:
  -h, --help            show this help message and exit
  -v, --version         show installed version and exit
  -o OUTPUT, --output OUTPUT
                        change output file name (default: structure.md)
  --ignore IGNORE       comma-separated list of file or directory names to
                        ignore
  --watch               watch filesystem and regenerate on structural changes
  --watch-only          watch for changes without initial generation
```

---

### Flag Semantics

- path
  - Root directory to scan
  - Defaults to the current working directory

- -v / --version
  - Prints the installed version in the format:

    ```text
    projtree: <version>
    ```

  - Exits immediately
  - Implemented natively via argparse

- -o / --output
  - Path to the generated Markdown file
  - Defaults to structure.md in the current directory
  - Relative paths use the working directory, not the scanned root; the parent output directory must already exist

- --ignore
  - Comma-separated list of file or directory names to ignore
  - Names are matched exactly (no globbing)
  - Combined with built-in ignores and .projtreeignore

- --watch
  - Enables filesystem watching using watchdog
  - Regenerates output on structural changes

- --watch-only
  - Requires --watch
  - Skips the initial generation
  - Only regenerates after the first detected change

---

### Design Constraints (v1)

- The CLI performs no filesystem traversal itself
- All generation logic lives in generator.py
- Watch mode is optional and explicitly opt-in
- Invalid flag combinations are rejected early
- The CLI relies solely on the Python standard library (argparse) for argument handling

---

## 5. Generation Layer (generator.py)

### Role and Responsibilities

- Traverse the filesystem
- Apply ignore rules
- Produce Markdown output

### Key Characteristics

- Read-only: no filesystem writes; traversal reads the current filesystem state
- Directories come before files; both groups are sorted by `name.casefold()`. Equal sort keys retain filesystem enumeration order, so names differing only in case have no guaranteed tie-break order
- Output format is strictly defined
- Does not handle output file ignoring (delegated to CLI/watcher layers)

### Core API

```python
def generate_markdown_tree(
    root_path: Path,
    ignore: set[str] | None = None,
) -> str
```

This function:

- Walks directories top-down
- Sorts entries in case-insensitive lexicographic order
- Applies ignore filtering by name
- Emits Markdown using a fixed indentation scheme

`root_path` must be a `Path`, not a string. The generator uses only the supplied ignore set; it does not load built-in defaults or `.projtreeignore` itself.

---

## 6. Ignore System (ignore.py)

### 6.1 Purpose and Scope

The Ignore System defines how Project Tree determines which files and directories are excluded from traversal, display, and watcher-triggered regeneration.

Its goals are:

- Deterministic behavior across platforms
- Explicit, predictable resolution order
- Minimal magic: no globbing or implicit pattern expansion in v1
- Consistency between generation and watcher behavior

The ignore system operates only on names, not paths or patterns.

---

### 6.2 Sources of Ignore Rules

Ignore rules may originate from up to three sources, listed here in the loading order:

1. Built-in defaults
  Hardcoded exclusions required for correct operation (e.g., .git).
2. Project ignore file (.projtreeignore)
  Located at the root of the traversal.
3. CLI-provided ignores
  Passed via --ignore, as a comma-separated list of names.

Ignore lists are unioned across sources, so the order describes how entries are loaded, not overridden.

---

### 6.3 Resolution Order

Ignore resolution proceeds in the following order:

1. Initialize the ignore set with built-in defaults
2. Load and merge rules from .projtreeignore (if present)
3. Load and merge rules from --ignore CLI arguments
4. Orchestration layers (CLI/watcher) add the output file name only when the output path is under the project root
5. Pass the effective set to each generation run. The watcher caches file entries in `_preloaded_ignores` and reloads them on qualifying `.projtreeignore` events (see Chapter 7)

---

### 6.4 Matching Rules

Ignore rules are evaluated using the following rules:

- Matching is done against any path component (segment) of the relative path (top-level or nested; operates only on names)
- Matching is exact and case-sensitive
- No globbing, wildcards, regex, or pattern-based matching is supported in v1

Examples:

- node_modules ignores all directories named node_modules at any depth
- __pycache__ ignores all __pycache__ directories at any depth
- src ignores any file or directory named src anywhere in the tree
- `*.log` matches only that literal name, not all names ending in `.log`

This constraint is intentional to preserve simplicity and predictability.

The generator matches traversal-relative path segments; `is_ignored` resolves paths before matching, so symlink handling can differ between generation and watcher filtering.

---

### 6.5 Directory vs File Behavior

Ignore rules apply uniformly to:

- Files
- Directories

However, directories have an additional effect:

- If a directory is ignored, its entire subtree is pruned
- The generator does not traverse that subtree. The observer still watches recursively under the root; the handler filters ignored events after delivery

This ensures both performance and correctness.

---

### 6.6 Output File Handling

The output file (default: structure.md, or the value of --output) is treated specially:

- It is ignored by the CLI and watcher when the output path is under the project root, regardless of user configuration
- Exclusion uses the output basename, so other entries with the same name are also ignored at any depth
- The generator itself has no knowledge of the output file; ignore enforcement happens at orchestration layers
- This prevents:

  - Self-inclusion in the generated tree
  - Infinite regeneration loops when using --watch

This behavior is non-configurable in v1.

---

### 6.7 Edge Cases and Clarifications

#### 6.7.1 Conflicting Rules

If the same name appears in multiple sources:

- The name is ignored if any source includes it
- There is no allowlist or negation mechanism in v1

Example:

- .projtreeignore ignores dist
- CLI does not mention dist
- Result: dist is ignored

---

#### 6.7.2 Empty or Missing Ignore Files

- A missing .projtreeignore is treated as an empty file
- An empty .projtreeignore has no effect
- Whitespace-only lines are ignored

---

#### 6.7.3 Duplicate Entries

Duplicate ignore entries:

- Are silently deduplicated
- Do not affect behavior or performance

---

#### 6.7.4 Path-Like Entries

Entries containing path separators (e.g., `src/build`) do not match nested paths. Use `build` to ignore that name at any depth.

This avoids ambiguity and platform-specific behavior.

---

### 6.8 Interaction with the Watcher Layer

The ignore system directly affects the watcher:

- The observer watches recursively, including ignored subtrees
- Ignored events are filtered in the handler; a move is discarded only if both source and destination are ignored
- Qualifying events for a name `.projtreeignore` reload the root ignore file, even if that event's path would otherwise be ignored

When .projtreeignore changes:

1. The existing handler reloads `.projtreeignore` into `_preloaded_ignores`
2. Regeneration is scheduled after debounce without reinitializing the watcher or observer

See Chapter 7 for watcher guarantees and non-guarantees.

---

### 6.9 Non-Goals (v1)

The following are explicitly out of scope for v1:

- Glob patterns
- Negation rules (!)
- Per-directory ignore files
- Path-based matching
- Git-compatible ignore semantics

These may be considered in future versions but are intentionally excluded to keep v1 minimal and reliable.

---

### 6.10 Core API

```python
def is_ignored(
    path: Path,
    root: Path,
    *,
    extra_ignores: set[str] | None = None,
    preloaded_ignores: set[str] | None = None,
) -> bool
```

---

## 7. Watcher Layer (watcher.py)

### Function

The watcher layer provides optional, continuous regeneration of the project tree by monitoring filesystem changes. It is intentionally thin and conservative in scope.

Its responsibilities are:

- Observe filesystem events under the project root
- Detect structural changes
- Trigger regeneration via the existing generator logic
- Avoid infinite regeneration loops

---

### Definition: Structural Change (v1)

In Project Tree v1, a structural change is defined as create/delete/move events that may alter the directory tree, including:

- Creation of files or directories
- Deletion of files or directories
- Renaming or moving files or directories (including directory moves)

Importantly:

- The watcher ignores open/close events and ordinary `modified` events; changes to `.projtreeignore` still reload ignore rules
- Structural changes are detected via create/delete/move events; moves check both source and destination so renaming an ignored entry to a visible name regenerates the tree

This definition is intentionally broad to ensure correctness across platforms and filesystems.

---

### Debounce Behavior

Filesystem operations frequently emit multiple events for a single user action. To prevent excessive regeneration, the watcher applies a time-based debounce strategy:

- On the first qualifying event, regeneration is scheduled after a short delay
- Additional events received during the debounce window reset the timer
- Regeneration occurs once no new events have been observed for the duration of the debounce interval

The CLI uses a 0.4-second debounce interval. Python callers can override `watch_and_generate(debounce_seconds=...)`.

---

### Non-Guarantees (Explicit)

The watcher layer in v1 deliberately makes no guarantees about:

- Capturing every individual filesystem event
- The ordering or type of events received from the operating system
- Immediate regeneration after a change
- Cross-platform event consistency

For delivered qualifying events, the handler schedules a debounced full rescan. Updating output depends on generation and filesystem I/O succeeding; missed events do not trigger an automatic rescan.

---

### Loop Prevention

To avoid infinite regeneration loops:

- The output file itself is explicitly ignored by the watcher (when under the project root)
- Writing is skipped if the generated Markdown equals the existing file's decoded text; the tree is still regenerated for comparison
- Open/close events are discarded before ignore-file loading, preventing reads from triggering further reloads

---

### Non-Goals (v1)

The watcher layer does not provide:

- Fine-grained event filtering
- One-shot watch semantics
- Incremental or partial regeneration
- Snapshot diffs or change summaries

All advanced watch behavior is deferred to future versions.

---

## 8. Testing Strategy

### 8.1 Objectives

The Project Tree test suite is designed to enforce the following properties:

- Deterministic, stable output for a given filesystem state
- Clear separation between pure logic and side-effecting components
- High signal-to-noise ratio in test failures
- Minimal coupling to platform-specific filesystem behavior

The test suite prioritizes correctness guarantees over exhaustive behavioral simulation.

---

### 8.2 Core Principle: Full-Output Assertion

Tree-format tests must assert against the full output, not partial fragments. The repeatability test compares two generated outputs.

This rule exists to ensure:

- Ordering is deterministic
- No unintended output is added or removed
- Formatting regressions are immediately detected

CLI and watcher tests may use targeted assertions for orchestration behavior rather than tree formatting.

---

### 8.3 Pure Logic vs Side Effects

The test suite distinguishes between:

- Pure, deterministic logic (tree generation, ignore resolution)
- Side-effecting orchestration (filesystem watching, debounce timing)

Rendering tests call the generator directly; CLI tests cover selected ignore behavior and argument handling.

Real-observer integration is tested minimally; handler decisions are tested directly with scheduling mocked.

---

### 8.4 Watcher Testing Philosophy

Filesystem watchers are inherently:

- Platform-dependent
- Timing-sensitive
- Non-deterministic under load

As a result, real-observer testing is limited to a new-file regeneration smoke test. Event-handler rules are tested directly with scheduling and reload calls mocked.

Watcher tests verify:

1. A new file appears in output with a real observer
2. Access events do not reload ignores or schedule regeneration
3. Renames check both source and destination visibility
4. Ignore-file create, modify, delete, and move events reload cached rules and schedule regeneration

The live smoke test uses fixed sleeps and a daemon thread; it does not stop the watcher or verify shutdown.

They do not attempt to verify:

- Exact debounce timing
- Event coalescing behavior
- OS-specific event semantics
- High-frequency event storms

Watchdog supplies OS event delivery; this repository implements debounce scheduling and regeneration, but does not exhaustively test their timing or failure paths.

---

### 8.5 Justification for Minimal Watcher Tests

Attempting to fully simulate watcher behavior would:

- Introduce flaky tests
- Require arbitrary sleeps and timing heuristics
- Reduce confidence rather than increase it
- Obscure genuine regressions with environmental noise

Instead, the suite tests event-handler decisions directly and keeps real-observer integration coverage small.

---

### 8.6 CLI Testing Rules

Current CLI tests:

- Call `argparse_main(argv)` directly, not an installed subprocess
- Check returned exit codes and `SystemExit` for argparse actions and errors
- Mock generation or watch dispatch where isolating orchestration behavior

Version and invalid-flag tests use targeted stdout/stderr assertions. There is no separate automated help-output test.

---

### 8.7 Regression Lock-In

Once behavior is covered by a test:

- Changing that behavior requires updating the test
- Updating the test requires a corresponding documentation change

This enforces alignment between:

- Code
- Tests
- Architecture documentation

Silent behavior changes are treated as regressions, not refactors.

---

### 8.8 Non-Goals

The test suite does not aim to:

- Benchmark performance
- Stress-test filesystem event throughput
- Validate third-party library correctness
- Simulate every possible filesystem edge case

Those concerns are intentionally excluded to preserve test clarity and reliability.

---

### 8.9 Summary

In short:

- Pure logic is tested strictly
- Side effects are tested minimally
- Rendering format is asserted in full
- Flakiness is treated as a failure of design

This strategy ensures that Project Tree remains stable, predictable, and maintainable as it evolves.

---

## 9. Design Philosophy

Project Tree v1 prioritizes:

- Correctness over features
- Simplicity over abstraction
- Explicit behavior over cleverness

Every component should be:

- Readable in isolation
- Testable directly where practical; orchestration tests may mock dispatch and scheduling
- Easy to remove or extend

---

## 10. Deferred Features

The following are intentionally out of scope for v1:

- Snapshot or diff engine
- Machine-readable output formats
- Ignore pattern matching
- Incremental regeneration
- Advanced watch semantics

These will be introduced incrementally after v1 stabilization.

---

## 11. Versioning

- v1.x: Stable Markdown generator with watch support
- v2.x (planned): Snapshot model and extensible outputs

---

## 12. Summary

Project Tree v1 is a deliberately minimal, robust foundation. It solves one problem well: generating a clean, deterministic project tree. All future enhancements build on this stable core.
