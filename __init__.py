from . import presets  # noqa: F401  (registers the HTTP routes)
from . import block_library  # noqa: F401 (registers reusable-block routes)
from . import objectives_api  # noqa: F401 (registers objective routes)
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .style_presets import PromptStylePresets
from .objective_node import PromptObjectiveBuilder

NODE_CLASS_MAPPINGS = {**NODE_CLASS_MAPPINGS, "PromptStylePresets": PromptStylePresets, "PromptObjectiveBuilder": PromptObjectiveBuilder}
NODE_DISPLAY_NAME_MAPPINGS = {**NODE_DISPLAY_NAME_MAPPINGS, "PromptStylePresets": "Prompt Style Presets", "PromptObjectiveBuilder": "Objetivos - Prompt Builder", "PromptPresetBuilder": "Bloques - Prompt Builder"}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
