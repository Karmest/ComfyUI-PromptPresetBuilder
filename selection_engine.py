"""Validate visual planner output and resolve chosen library blocks.

Fail closed on malformed selection: silently falling back to manual prompts
would hide an incorrect model decision from the user.
"""
import json
import re

MAX_SELECTION_CHARS = 32000
MAX_SELECTED_BLOCKS = 12


def decode_plan(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Empty selection; connect the visual evaluator output")
    if len(raw) > MAX_SELECTION_CHARS:
        raise ValueError("Selection response exceeds the safety limit")
    value = raw.strip()
    fence = chr(96) * 3
    if value.startswith(fence):
        matched = re.fullmatch(re.escape(fence) + r"(?:json)?\s*(.*?)\s*" + re.escape(fence), value, re.S | re.I)
        if matched:
            value = matched.group(1).strip()
    try:
        obj = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("Evaluator must return JSON with selected_block_ids") from error
    if not isinstance(obj, dict):
        raise ValueError("Evaluator response must be a JSON object")
    if "selected_block_ids" not in obj and isinstance(obj.get("rewritten_prompt"), str):
        return decode_plan(obj["rewritten_prompt"])
    selected = obj.get("selected_block_ids")
    if not isinstance(selected, list) or not selected:
        raise ValueError("Evaluator provided no selected_block_ids")
    if len(selected) > MAX_SELECTED_BLOCKS:
        raise ValueError("Evaluator selected too many blocks")
    if any(not isinstance(value, str) or not value or len(value) > 128 for value in selected):
        raise ValueError("Block IDs must be nonempty strings")
    if len(set(selected)) != len(selected):
        raise ValueError("Duplicate block IDs in evaluator output")
    return obj


def resolve_selection(raw, blocks, limit=MAX_SELECTED_BLOCKS):
    plan = decode_plan(raw)
    selection = plan["selected_block_ids"]
    if len(selection) > limit:
        raise ValueError(f"Evaluator selected {len(selection)} blocks, maximum is {limit}")
    indexed = {block["id"]: block for block in blocks}
    missing = [block_id for block_id in selection if block_id not in indexed]
    if missing:
        raise ValueError("Unknown block IDs from evaluator: " + ", ".join(missing))
    return [indexed[block_id] for block_id in selection]


def selected_fingerprint(raw, blocks):
    """Changing the content of any selected block invalidates cached output."""
    selected = resolve_selection(raw, blocks)
    return [(block["id"], block["text"]) for block in selected]
