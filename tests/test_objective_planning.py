"""Focused offline tests for Objective -> Evaluator -> Blocks selection.

Run: python -m unittest discover -s tests -p test_objective_planning.py -v
"""
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "promptbuilder_planning_tests"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(ROOT)]
sys.modules.setdefault(PACKAGE, pkg)

selection = importlib.import_module(PACKAGE + ".selection_engine")
store = importlib.import_module(PACKAGE + ".objective_store")
engine = importlib.import_module(PACKAGE + ".objective_engine")
nodes = importlib.import_module(PACKAGE + ".nodes")
objective_node = importlib.import_module(PACKAGE + ".objective_node")

BLOCKS = [
    {"id": "a", "name": "Natural lighting", "category": "Photo", "description": "Lighting", "text": "Natural light"},
    {"id": "b", "name": "Skin fidelity", "category": "People", "description": "People", "text": "Preserve facial identity"},
    {"id": "c", "name": "Remove noise", "category": "Restoration", "description": "Noise", "text": "Reduce digital noise"},
]


class SelectionTests(unittest.TestCase):
    def test_exact_ids_and_order(self):
        payload = json.dumps({"selected_block_ids": ["c", "a"], "reason": "Ruido e iluminación"})
        self.assertEqual([x["id"] for x in selection.resolve_selection(payload, BLOCKS)], ["c", "a"])

    def test_fenced_json(self):
        payload = chr(96) * 3 + "json\n" + json.dumps({"selected_block_ids": ["b"]}) + "\n" + chr(96) * 3
        self.assertEqual([x["id"] for x in selection.resolve_selection(payload, BLOCKS)], ["b"])

    def test_rewritten_prompt_wrapper(self):
        nested = json.dumps({"selected_block_ids": ["b"]})
        result = json.dumps({"rewritten_prompt": nested})
        self.assertEqual([x["id"] for x in selection.resolve_selection(result, BLOCKS)], ["b"])

    def test_unknown_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unknown block IDs"):
            selection.resolve_selection('{"selected_block_ids":["invented"]}', BLOCKS)

    def test_invalid_json_or_empty_selection_fails(self):
        for raw in ["", "not JSON", '{"selected_block_ids":[]}', '{"selected_block_ids":["a","a"]}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                selection.resolve_selection(raw, BLOCKS)

    def test_library_edit_changes_fingerprint(self):
        raw = '{"selected_block_ids":["a"]}'
        before = selection.selected_fingerprint(raw, BLOCKS)
        edited = [dict(item) for item in BLOCKS]
        edited[0]["text"] = "Different natural illumination"
        self.assertNotEqual(before, selection.selected_fingerprint(raw, edited))


class ObjectiveTests(unittest.TestCase):
    def test_default_goals_and_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "objectives.json"
            goals = store.load_objectives(path)
            self.assertTrue(any(o["id"] == "goal.realism" for o in goals))
            store.save_objectives(goals, path)
            self.assertEqual(store.load_objectives(path), goals)
            goals[0]["description"] = "Updated description"
            store.save_objectives(goals, path)
            self.assertTrue((Path(tmp) / "objectives.json.bak").exists())

    def test_evaluator_includes_real_catalog_and_goal(self):
        goal = store.objective_by_id("goal.realism", store.DEFAULT_OBJECTIVES)
        system, prompt = engine.make_evaluator_prompts(goal, BLOCKS, 3)
        self.assertIn('"id":"a"', system)
        self.assertNotIn("Preserve facial identity", system)  # full block instructions are not sent
        self.assertIn("Select between 1 and 3 blocks", system)
        self.assertIn("Realismo absoluto", prompt)
        self.assertIn("<image1>", prompt)

    def test_cannot_plan_with_empty_library(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            engine.make_evaluator_prompts(store.DEFAULT_OBJECTIVES[0], [], 4)


class NodeContractTests(unittest.TestCase):
    def test_manual_mode_unchanged(self):
        obj = nodes.PromptPresetBuilder()
        manual = json.dumps([{"text": "existing instruction", "enabled": True}])
        output = obj.build(manual, ", ", 0)
        self.assertEqual(output["result"][0], "existing instruction")

    def test_automatic_mode_uses_selected_ids_not_manual_rows(self):
        original = nodes.load_blocks
        nodes.load_blocks = lambda: BLOCKS
        try:
            builder = nodes.PromptPresetBuilder()
            result = builder.build('[{"text":"not selected"}]', r"\n\n", 0,
                                   '{"selected_block_ids":["c","b"]}')
            self.assertEqual(result["result"][0], "Reduce digital noise\n\nPreserve facial identity")
        finally:
            nodes.load_blocks = original

    def test_connected_invalid_selector_fails(self):
        original = nodes.load_blocks
        nodes.load_blocks = lambda: BLOCKS
        try:
            builder = nodes.PromptPresetBuilder()
            with self.assertRaises(ValueError):
                builder.build('[{"text":"fallback should not be used"}]', ", ", 0, "")
        finally:
            nodes.load_blocks = original

    def test_objective_node_produces_two_outputs(self):
        saved_load_blocks = objective_node.load_blocks
        saved_load_objectives = objective_node.load_objectives
        objective_node.load_blocks = lambda: BLOCKS
        objective_node.load_objectives = lambda: store.DEFAULT_OBJECTIVES
        try:
            output = objective_node.PromptObjectiveBuilder().build("goal.people", 4, "")
            self.assertEqual(len(output["result"]), 3)
            self.assertIn('"selected_block_ids"', output["result"][0])
            self.assertIn("Mejorar fotos con personas", output["result"][1])
            self.assertIn("Edit <image1>", output["result"][2])
        finally:
            objective_node.load_blocks = saved_load_blocks
            objective_node.load_objectives = saved_load_objectives


if __name__ == "__main__":
    unittest.main()
