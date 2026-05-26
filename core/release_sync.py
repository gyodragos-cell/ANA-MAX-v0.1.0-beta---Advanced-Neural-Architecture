"""ANA MAX v22 DEV-only release sync scaffolding.

This module is a planning surface for the private ANA development workspace. It
must never perform real synchronization, copying, deletion, documentation
updates, site updates, Git operations, or public release writes. All methods are
read-only placeholders that outline future behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEV_ONLY_NOTICE = "DEV MODE ONLY - read-only planning scaffold"


@dataclass(frozen=True)
class FileTreeSnapshot:
    """Placeholder file tree snapshot for read-only planning."""

    root: str
    files: tuple[str, ...] = field(default_factory=tuple)
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe snapshot shape."""
        return {
            "root": self.root,
            "files": list(self.files),
            "count": len(self.files),
            "simulated": self.simulated,
        }


@dataclass(frozen=True)
class DiffEntry:
    """Placeholder diff entry for future sync review."""

    path: str
    status: str
    action: str = "ignore"
    reason: str = "dev-only scaffold; no sync execution"

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-safe diff entry."""
        return {
            "path": self.path,
            "status": self.status,
            "action": self.action,
            "reason": self.reason,
        }


class ReleaseSync:
    """DEV-only release sync planner with no write or sync behavior."""

    def __init__(self, dev_root: str | Path, release_root: str | Path) -> None:
        """Store roots and initialize placeholder planning structures."""
        self.dev_root = Path(dev_root)
        self.release_root = Path(release_root)
        self.notice = DEV_ONLY_NOTICE
        self.dev_snapshot = FileTreeSnapshot(root=str(self.dev_root))
        self.release_snapshot = FileTreeSnapshot(root=str(self.release_root))
        self.diff_entries: tuple[DiffEntry, ...] = ()
        self.sync_plan: dict[str, Any] = {
            "mode": "dev_only_plan",
            "actions": [],
            "disabled_actions": ["copy", "update", "delete"],
            "allowed_actions": ["ignore", "review"],
        }
        self.documentation_update_plan: dict[str, Any] = {"surfaces": [], "actions": []}
        self.site_update_plan: dict[str, Any] = {"surfaces": [], "actions": []}
        self.release_notes_plan: dict[str, Any] = {"title": "", "bullets": []}
        # TODO(v22): automatic sync execution (disabled).
        # TODO(v22): git commit automation (disabled).
        # TODO(v22): version bumping.
        # TODO(v22): CHANGELOG auto-generation.
        # TODO(v22): README auto-update.
        # TODO(v22): AGENTS.md + PROJECT_MAP_AI_GUIDE auto-sync.
        # TODO(v22): site deployment hooks.

    def scan_dev(self) -> FileTreeSnapshot:
        """Return a read-only placeholder scan of the dev tree."""
        files = self._read_only_list_files(self.dev_root)
        self.dev_snapshot = FileTreeSnapshot(root=str(self.dev_root), files=files)
        return self.dev_snapshot

    def scan_release(self) -> FileTreeSnapshot:
        """Return a read-only placeholder scan of the release tree."""
        files = self._read_only_list_files(self.release_root)
        self.release_snapshot = FileTreeSnapshot(root=str(self.release_root), files=files)
        return self.release_snapshot

    def compare_trees(self) -> tuple[DiffEntry, ...]:
        """Simulate tree comparison without preparing real file operations."""
        dev_files = set(self.dev_snapshot.files or self.scan_dev().files)
        release_files = set(self.release_snapshot.files or self.scan_release().files)
        entries: list[DiffEntry] = []
        for path in sorted(dev_files - release_files):
            entries.append(DiffEntry(path=path, status="dev_only"))
        for path in sorted(release_files - dev_files):
            entries.append(DiffEntry(path=path, status="release_only"))
        for path in sorted(dev_files & release_files):
            entries.append(DiffEntry(path=path, status="shared", action="review"))
        self.diff_entries = tuple(entries)
        return self.diff_entries

    def generate_sync_plan(self) -> dict[str, Any]:
        """Return a simulated sync plan with all real actions disabled."""
        entries = self.diff_entries or self.compare_trees()
        self.sync_plan = {
            "mode": "dev_only_plan",
            "notice": self.notice,
            "actions": [entry.to_dict() for entry in entries],
            "disabled_actions": ["copy", "update", "delete", "commit", "deploy"],
            "will_execute": False,
        }
        return self.sync_plan

    def summarize_differences(self) -> dict[str, Any]:
        """Return counts for simulated diff entries."""
        entries = self.diff_entries or self.compare_trees()
        counts: dict[str, int] = {}
        for entry in entries:
            counts[entry.status] = counts.get(entry.status, 0) + 1
        return {
            "notice": self.notice,
            "counts": counts,
            "total": len(entries),
            "examples": [entry.to_dict() for entry in entries[:5]],
        }

    def prepare_site_updates(self) -> dict[str, Any]:
        """Outline future site updates without modifying site files."""
        self.site_update_plan = {
            "notice": self.notice,
            "surfaces": ["index.html", "videos.html"],
            "actions": ["review only", "no write", "no deploy"],
            "will_modify_files": False,
        }
        return self.site_update_plan

    def prepare_docs_updates(self) -> dict[str, Any]:
        """Outline future documentation updates without modifying docs."""
        self.documentation_update_plan = {
            "notice": self.notice,
            "surfaces": [
                "README.md",
                "CHANGELOG.md",
                "AGENTS.md",
                "docs/PROJECT_MAP_AI_GUIDE.md",
            ],
            "actions": ["review only", "no write", "no sync"],
            "will_modify_files": False,
        }
        return self.documentation_update_plan

    def prepare_release_notes(self) -> dict[str, Any]:
        """Outline future release notes without generating public files."""
        summary = self.summarize_differences()
        self.release_notes_plan = {
            "notice": self.notice,
            "title": "ANA MAX v22 release sync draft (not generated)",
            "bullets": [
                "Release notes are simulated only.",
                f"Simulated diff entries: {summary['total']}",
                "No public release files were modified.",
            ],
            "will_write_file": False,
        }
        return self.release_notes_plan

    @staticmethod
    def _read_only_list_files(root: Path) -> tuple[str, ...]:
        """Return a small read-only file listing for an existing folder."""
        if not root.exists() or not root.is_dir():
            return ()
        files: list[str] = []
        for path in root.rglob("*"):
            if path.is_file():
                files.append(path.relative_to(root).as_posix())
            if len(files) >= 50:
                break
        return tuple(sorted(files))