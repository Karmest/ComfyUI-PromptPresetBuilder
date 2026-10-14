import json
import random

from .dynamic_prompt import resolve
from .block_store import load_blocks, block_index, resolve_row_text, fingerprint_for_rows


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
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "build"
    CATEGORY = "utils/prompt"
    DESCRIPTION = "Build a prompt from named elements. Supports {a|b|0.4::c} syntax and named presets."

    @classmethod
    def IS_CHANGED(cls, preset_data, separator, seed):
        try:
            rows = json.loads(preset_data) if preset_data.strip() else []
            if not isinstance(rows, list) or not any(isinstance(r, dict) and r.get("block_id") for r in rows):
                return ""
            return fingerprint_for_rows(rows, block_index(load_blocks()))
        except (ValueError, OSError):
            return "block-library-error"

    def build(self, preset_data, separator, seed):
        try:
            rows = json.loads(preset_data) if preset_data.strip() else []
        except ValueError:
            rows = []
        if not isinstance(rows, list):
            rows = []

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
