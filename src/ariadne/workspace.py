"""Opt-in, workspace-scoped text file tools for Ariadne."""

import os
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any, Callable


class Workspace:
    """Expose bounded file operations inside one explicitly selected directory."""

    MAX_READ_BYTES = 200_000
    MAX_WRITE_BYTES = 200_000
    MAX_LIST_ENTRIES = 200

    def __init__(
        self,
        root: str | Path,
        confirm_write: Callable[[str, bool], bool] | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("workspace path must be an existing directory")
        self._confirm_write = confirm_write

    def list_files(self, relative_path: str = ".") -> dict[str, Any]:
        directory = self._resolve(relative_path, allow_root=True)
        if not directory.is_dir():
            raise ValueError("workspace path is not a directory")

        scanned: list[Path] = []
        for entry in directory.iterdir():
            if entry.name == ".git" or entry.is_symlink():
                continue
            scanned.append(entry)
            if len(scanned) > self.MAX_LIST_ENTRIES:
                break
        visible = sorted(scanned[: self.MAX_LIST_ENTRIES], key=lambda item: item.name.casefold())
        entries = [
            {"name": entry.name, "type": "directory" if entry.is_dir() else "file"}
            for entry in visible
        ]
        return {
            "path": self._display_path(directory),
            "entries": entries,
            "truncated": len(scanned) > self.MAX_LIST_ENTRIES,
        }

    def read_file(self, relative_path: str) -> dict[str, str]:
        path = self._resolve(relative_path)
        if not path.is_file():
            raise ValueError("workspace path is not a file")
        size = path.stat().st_size
        if size > self.MAX_READ_BYTES:
            raise ValueError(f"file is larger than the {self.MAX_READ_BYTES}-byte read limit")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("file is not valid UTF-8 text") from exc
        return {"path": self._display_path(path), "content": content}

    def write_file(
        self, relative_path: str, content: str, overwrite: bool = False
    ) -> dict[str, Any]:
        path = self._resolve(relative_path)
        if not path.parent.is_dir():
            raise ValueError("parent directory does not exist")
        if path.exists() and not overwrite:
            raise ValueError("file already exists; set overwrite=true to replace it")
        if path.exists() and not path.is_file():
            raise ValueError("workspace path is not a regular file")
        existed_before = path.exists()
        encoded = content.encode("utf-8")
        if len(encoded) > self.MAX_WRITE_BYTES:
            raise ValueError(
                f"content is larger than the {self.MAX_WRITE_BYTES}-byte write limit"
            )
        if self._confirm_write is None or not self._confirm_write(
            self._display_path(path), existed_before
        ):
            raise ValueError("workspace write was not approved")

        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=path.parent, prefix=".ariadne-", delete=False
            ) as temporary:
                temporary_path = temporary.name
                temporary.write(encoded)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return {
            "path": self._display_path(path),
            "bytes_written": len(encoded),
            "overwrote_existing_file": existed_before,
        }

    def _resolve(self, relative_path: str, allow_root: bool = False) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("path must be a non-empty relative path")
        supplied = relative_path.strip()
        windows_path = PureWindowsPath(supplied)
        candidate_path = Path(supplied)
        if candidate_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise ValueError("absolute paths are not allowed")
        if any(part == ".." for part in supplied.replace("\\", "/").split("/")):
            raise ValueError("parent-directory paths are not allowed")
        if any(part.casefold() == ".git" for part in candidate_path.parts) or any(
            part.casefold() == ".git" for part in windows_path.parts
        ):
            raise ValueError("the Git metadata directory is not available")
        try:
            resolved = (self.root / candidate_path).resolve(strict=True)
        except FileNotFoundError:
            resolved = (self.root / candidate_path).resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise ValueError("path resolves outside the configured workspace")
        if any(
            part.casefold() == ".git" for part in resolved.relative_to(self.root).parts
        ):
            raise ValueError("the Git metadata directory is not available")
        if resolved == self.root and not allow_root:
            raise ValueError("a file path inside the workspace is required")
        return resolved

    def _display_path(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix() or "."
