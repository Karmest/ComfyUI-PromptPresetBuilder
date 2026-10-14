"""Separate, selectable objective node: prepares system + user prompts for visual PE."""
import hashlib
import json

from .block_store import load_blocks
from .objective_store import load_objectives, objective_by_id
from .objective_engine import make_evaluator_prompts


class PromptObjectiveBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "objective_id": ("STRING", {"default": "goal.auto"}),
            "max_blocks": ("INT", {"default": 5, "min": 1, "max": 12}),
            "extra_context": ("STRING", {"default": "", "multiline": True}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("system_prompt", "prompt", "final_prompt")
    FUNCTION = "build"
    CATEGORY = "utils/prompt"
    DESCRIPTION = "Choose a goal for visual Qwen PE evaluation, not a final generation prompt."

    @classmethod
    def IS_CHANGED(cls, objective_id, max_blocks, extra_context):
        try:
            objectives = load_objectives()
            chosen = objective_by_id(objective_id, objectives)
            if chosen is None:
                return "missing-objective:" + str(objective_id)
            blocks = load_blocks()
            metadata = [(b["id"], b["name"], b["category"], b.get("description", "")) for b in blocks]
            content = json.dumps([chosen, metadata], ensure_ascii=False, sort_keys=True)
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        except (ValueError, OSError):
            return "objective-or-library-error"

    def build(self, objective_id, max_blocks, extra_context):
        chosen = objective_by_id(objective_id, load_objectives())
        if chosen is None:
            raise ValueError(f"Unknown objective: {objective_id}; select one in Objective Builder")
        system, prompt = make_evaluator_prompts(chosen, load_blocks(), max_blocks, extra_context)
        final_prompt = (
            "Edit <image1> to achieve the following result: "
            + chosen["name"] + ". " + chosen["instruction"]
            + " Apply only improvements justified by the input image, "
              "preserving everything else. Do not add unrelated objects or change identities."
        )
        return {"ui": {"text": [chosen["name"]]}, "result": (system, prompt, final_prompt)}
