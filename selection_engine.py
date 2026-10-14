"""Validate visual planner output and resolve chosen library blocks.

Fail closed on malformed selection: silently falling back to manual prompts
would hide an incorrect model decision from the user.
"""
import json
import logging
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
        # Qwen PE may emit a complete valid selection and then keep generating
        # junk until max_length. Recover only a JSON object at the very START,
        # never one embedded somewhere in free-form model output.
        try:
            obj, end = json.JSONDecoder().raw_decode(value)
        except json.JSONDecodeError:
            raise ValueError("Evaluator must start with a valid JSON selection") from error
        if not isinstance(obj, dict):
            raise ValueError("Evaluator's first JSON value must be an object") from error
        rest = value[end:].strip()
        if rest.startswith("{") or rest.startswith("["):
            raise ValueError("Evaluator returned multiple JSON values") from error
        if not rest:
            raise ValueError("Invalid evaluator output after the first JSON value") from error
        if "selected_block_ids" not in obj and "rewritten_prompt" not in obj:
            raise ValueError("Evaluator did not begin with a selection JSON") from error
        logging.warning("Visual evaluator: ignored %d characters after a complete JSON selection; reduce PE max_length.", len(rest))
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


def resolve_selection(raw, blocks, limit=5):
    plan = decode_plan(raw)
    selection = plan["selected_block_ids"]
    if not isinstance(limit, int) or not 1 <= limit <= MAX_SELECTED_BLOCKS:
        raise ValueError("max_selected_blocks must be between 1 and 12")
    indexed = {block["id"]: block for block in blocks}
    missing = [block_id for block_id in selection if block_id not in indexed]
    if missing:
        raise ValueError("Unknown block IDs from evaluator: " + ", ".join(missing))
    if len(selection) > limit:
        logging.warning(
            "Visual evaluator selected %d valid blocks, keeping the first %d ranked IDs.",
            len(selection), limit,
        )
    return [indexed[block_id] for block_id in selection[:limit]]


def selected_fingerprint(raw, blocks, limit=5):
    """Changing the content of any selected block invalidates cached output."""
    selected = resolve_selection(raw, blocks, limit=limit)
    return [(block["id"], block["text"]) for block in selected]
