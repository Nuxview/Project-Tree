#!/usr/bin/env python3

"""Tests for watcher-based regeneration."""

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from watchdog.events import (
    FileClosedEvent,
    FileClosedNoWriteEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileOpenedEvent,
)

from projtree.watcher import _DebouncedHandler, watch_and_generate


@pytest.mark.parametrize(
    "event_class", [FileOpenedEvent, FileClosedNoWriteEvent, FileClosedEvent]
)
@pytest.mark.parametrize("filename", ["file.txt", ".projtreeignore"])
def test_access_events_do_not_reload_or_regenerate(
    tmp_path: Path, event_class, filename
):
    """Reading or closing files must not trigger more reads or tree scans."""
    handler = _DebouncedHandler(tmp_path, tmp_path / "structure.md", 0.1)

    with (
        patch("projtree.watcher.load_ignore_file") as reload_ignores,
        patch.object(handler, "_schedule_regeneration") as schedule,
    ):
        handler.on_any_event(event_class(str(tmp_path / filename)))

    reload_ignores.assert_not_called()
    schedule.assert_not_called()


@pytest.mark.parametrize(
    ("source", "destination", "expected"),
    [
        ("hidden.txt", "visible.txt", True),
        ("visible.txt", "hidden.txt", True),
        ("hidden.txt", "also-hidden.txt", False),
        ("visible.txt", "renamed.txt", True),
    ],
)
def test_moves_check_both_names(tmp_path: Path, source, destination, expected):
    """Moving into or out of the visible tree must refresh its output."""
    handler = _DebouncedHandler(
        tmp_path, tmp_path / "structure.md", 0.1, {"hidden.txt", "also-hidden.txt"}
    )

    with patch.object(handler, "_schedule_regeneration") as schedule:
        handler.on_any_event(
            FileMovedEvent(str(tmp_path / source), str(tmp_path / destination))
        )

    assert schedule.call_count == int(expected)


@pytest.mark.parametrize(
    ("event_class", "source", "destination"),
    [
        (FileCreatedEvent, ".projtreeignore", ""),
        (FileModifiedEvent, ".projtreeignore", ""),
        (FileDeletedEvent, ".projtreeignore", ""),
        (FileMovedEvent, "replacement", ".projtreeignore"),
        (FileMovedEvent, ".projtreeignore", "old-ignore"),
    ],
)
def test_ignore_changes_reload_rules(tmp_path: Path, event_class, source, destination):
    """Ignore edits and replacements must update cached rules and regenerate."""
    handler = _DebouncedHandler(tmp_path, tmp_path / "structure.md", 0.1)
    event = event_class(
        str(tmp_path / source), str(tmp_path / destination) if destination else ""
    )

    with (
        patch(
            "projtree.watcher.load_ignore_file", return_value={"new-ignore"}
        ) as reload_ignores,
        patch.object(handler, "_schedule_regeneration") as schedule,
    ):
        handler.on_any_event(event)

    reload_ignores.assert_called_once_with(tmp_path)
    assert handler._preloaded_ignores == {"new-ignore"}
    schedule.assert_called_once_with()


def test_watcher_regenerates_on_new_file(tmp_path: Path):
    """Regenerate output when a new file appears."""
    output = tmp_path / "STRUCTURE.md"

    watcher_thread = threading.Thread(
        target=watch_and_generate,
        kwargs={
            "root_path": tmp_path,
            "output_path": output,
            "debounce_seconds": 0.1,
        },
        daemon=True,
    )
    watcher_thread.start()

    time.sleep(0.2)

    # Trigger structural change
    (tmp_path / "new_file.txt").write_text("hello")

    time.sleep(0.4)

    assert output.exists()
    contents = output.read_text(encoding="utf-8")

    assert "new_file.txt" in contents
