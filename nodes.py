import json
import random

from .dynamic_prompt import resolve
from .block_store import load_blocks, block_index, resolve_row_text, fingerprint_for_rows
from .selection_engine import resolve_selection, selected_fingerprint


class PromptPresetBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # UI state (label / text / enabled per element). Hidden by the JS side.
                "preset_data": ("STRING", {"default": "[]"}),
                "separator": ("STRING", {"default": ", "}),
                "seed": ("INT", {
                    "default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "control_after_generate": True,
                }),
            },
            "optional": {
                "selection_json": ("STRING", {"forceInput": True}),
                "max_selected_blocks": ("INT", {"default": 5, "min": 1, "max": 12}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "build"
    CATEGORY = "utils/prompt"
    DESCRIPTION = "Build a prompt from named elements. Supports {a|b|0.4::c} syntax and named presets."

    @classmethod
    def IS_CHANGED(cls, preset_data, separator, seed, selection_json=None, max_selected_blocks=5):
        try:
            if selection_json is not None:
                return json.dumps(selected_fingerprint(selection_json, load_blocks(), limit=max_selected_blocks), ensure_ascii=False)
            rows = json.loads(preset_data) if preset_data.strip() else []
            if not isinstance(rows, list) or not any(isinstance(r, dict) and r.get("block_id") for r in rows):
                return ""
            return fingerprint_for_rows(rows, block_index(load_blocks()))
        except (ValueError, OSError):
            return "block-library-error"

    def build(self, preset_data, separator, seed, selection_json=None, max_selected_blocks=5):
        try:
            rows = json.loads(preset_data) if preset_data.strip() else []
        except ValueError:
            rows = []
        if not isinstance(rows, list):
            rows = []

        rng = random.Random(seed)
        sep = separator.replace("\\n", "\n")

        # Optional automated mode replaces manual rows for this execution.
        # A connected but invalid/empty evaluator result must fail visibly.
        if selection_json is not None:
            selected = resolve_selection(selection_json, load_blocks(), limit=max_selected_blocks)
            parts = []
            for entry in selected:
                text = resolve(entry["text"], rng).strip().strip(",").strip()
                if text:
                    parts.append(text)
            result = sep.join(parts)
            return {"ui": {"text": [result]}, "result": (result,)}

        # Linked rows resolve at execution, not when the preset was saved.
        try:
            blocks = block_index(load_blocks()) if any(
                isinstance(r, dict) and r.get("block_id") for r in rows) else {}
        except (ValueError, OSError) as error:
            raise RuntimeError("Could not read the reusable block library") from error

        rng = random.Random(seed)
        sep = separator.replace("\\n", "\n")

        parts = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("enabled", True):
                continue
            text = resolve(resolve_row_text(row, blocks), rng).strip().strip(",").strip()
            if text:
                parts.append(text)

        result = sep.join(parts)
        return {"ui": {"text": [result]}, "result": (result,)}


NODE_CLASS_MAPPINGS = {"PromptPresetBuilder": PromptPresetBuilder}
NODE_DISPLAY_NAME_MAPPINGS = {"PromptPresetBuilder": "Prompt Preset Builder"}
