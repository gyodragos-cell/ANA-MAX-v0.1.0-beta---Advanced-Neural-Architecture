"""
ANA MAX - Precise Edit Tool
===========================
Exact file editing helper designed for local models.
"""

from __future__ import annotations

import difflib

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.path_safety import is_protected_path, resolve_workspace_path, safe_display_path


class EditTool(Tool):
    """Perform precise file edits without rewriting whole files."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="edit",
            description=(
                "Editeaza punctual un fisier prin replace exact sau insertii in jurul unui anchor text. "
                "Poate si previzualiza diff-ul fara sa scrie pe disc."
            ),
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Tipul de editare",
                    type="string",
                    required=True,
                    choices=["replace", "insert_before", "insert_after", "append", "prepend"],
                ),
                ToolParameter(
                    name="path",
                    description="Calea fisierului de editat",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="old_text",
                    description="Textul exact de inlocuit pentru operation=replace",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="new_text",
                    description="Textul nou care va fi inserat/scris",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="anchor_text",
                    description="Textul anchor pentru insert_before / insert_after",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="replace_all",
                    description="Inlocuieste toate aparitiile pentru replace",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="preview_only",
                    description="Returneaza doar diff-ul fara sa modifice fisierul",
                    type="boolean",
                    required=False,
                    default=False,
                ),
            ],
            category="files",
            requires_confirmation=False,
            dangerous=True,
        )

    def execute(self, operation: str, path: str, new_text: str = "", **kwargs) -> ToolResult:
        try:
            file_path = resolve_workspace_path(path)
        except (OSError, ValueError) as exc:
            return ToolResult(status=ToolStatus.BLOCKED, error=str(exc))
        if is_protected_path(file_path):
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to edit protected path: {safe_display_path(file_path)}")
        if not file_path.exists():
            return ToolResult(status=ToolStatus.ERROR, error=f"Fisierul nu exista: {path}")
        if operation not in {"replace", "insert_before", "insert_after", "append", "prepend"}:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

        original = file_path.read_text(encoding="utf-8")
        try:
            updated, matches = self._apply_operation(original, operation, new_text, **kwargs)
        except ValueError as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

        if original == updated:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"changed": False, "diff": "", "matches": matches},
                message="Nicio modificare necesara",
            )

        diff = "".join(
            difflib.unified_diff(
                original.splitlines(True),
                updated.splitlines(True),
                fromfile=safe_display_path(file_path),
                tofile=safe_display_path(file_path),
            )
        )
        preview_only = bool(kwargs.get("preview_only", False))
        if not preview_only:
            file_path.write_text(updated, encoding="utf-8")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"changed": True, "diff": diff, "matches": matches, "path": safe_display_path(file_path)},
            message="Previzualizare edit generata" if preview_only else "Editare aplicata",
        )

    def _apply_operation(self, original: str, operation: str, new_text: str, **kwargs):
        if operation == "replace":
            old_text = kwargs.get("old_text", "") or ""
            if not old_text:
                raise ValueError("Parametrul 'old_text' este necesar pentru replace")
            match_count = original.count(old_text)
            if match_count == 0:
                raise ValueError("Textul de inlocuit nu a fost gasit exact")
            replace_all = bool(kwargs.get("replace_all", False))
            if match_count > 1 and not replace_all:
                raise ValueError("Textul apare de mai multe ori. Foloseste replace_all sau rafineaza targetul")
            limit = match_count if replace_all else 1
            return original.replace(old_text, new_text, limit), match_count

        if operation == "insert_before":
            anchor = kwargs.get("anchor_text", "") or ""
            if not anchor:
                raise ValueError("Parametrul 'anchor_text' este necesar pentru insert_before")
            if anchor not in original:
                raise ValueError("Anchor text nu a fost gasit")
            return original.replace(anchor, new_text + anchor, 1), 1

        if operation == "insert_after":
            anchor = kwargs.get("anchor_text", "") or ""
            if not anchor:
                raise ValueError("Parametrul 'anchor_text' este necesar pentru insert_after")
            if anchor not in original:
                raise ValueError("Anchor text nu a fost gasit")
            return original.replace(anchor, anchor + new_text, 1), 1

        if operation == "append":
            return original + new_text, 1

        if operation == "prepend":
            return new_text + original, 1

        raise ValueError(f"Operatie necunoscuta: {operation}")
