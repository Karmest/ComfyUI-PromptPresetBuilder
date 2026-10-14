"""Reusable instruction blocks, shared by workflows in this ComfyUI instance.

Blocks are stored separately from existing per-user preset files. A linked
row has a stable block_id plus a text snapshot for portability/fallback.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path


def library_path():
    import folder_paths
    return Path(folder_paths.get_user_directory()) / "prompt_preset_builder" / "blocks.json"


def load_blocks(path=None):
    path = Path(path) if path is not None else library_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("blocks"), list):
        raise ValueError("Unsupported or invalid blocks.json; restore a backup before editing")
    blocks = data["blocks"]
    ids = set()
    for block in blocks:
        if not isinstance(block, dict) or not all(isinstance(block.get(k), str) for k in ("id", "category", "name", "text")):
            raise ValueError("Malformed entry in blocks.json")
        if not block["id"] or block["id"] in ids:
            raise ValueError("Missing or duplicate block ID")
        ids.add(block["id"])
    return blocks


def save_blocks(blocks, path=None):
    path = Path(path) if path is not None else library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    backup = path.with_name(path.name + ".bak")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump({"version": 1, "blocks": blocks}, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        if path.exists():
            shutil.copy2(path, backup)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def block_index(blocks):
    return {item["id"]: item for item in blocks}


def resolve_row_text(row, index):
    """Resolve a linked block; a missing block uses the saved text snapshot."""
    linked = index.get(row.get("block_id")) if isinstance(row.get("block_id"), str) else None
    if linked is not None:
        return linked["text"]
    return str(row.get("text", ""))


def fingerprint_for_rows(rows, index):
    """Include current linked block text so ComfyUI's execution cache invalidates."""
    linked = [(row.get("block_id"), resolve_row_text(row, index))
              for row in rows if isinstance(row, dict) and row.get("block_id")]
    return hashlib.sha256(json.dumps(linked, ensure_ascii=False).encode("utf-8")).hexdigest()
