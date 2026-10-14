"""Run with: python -m unittest discover -s tests -p test_block_store.py"""
import json
import tempfile
import unittest
from pathlib import Path

from block_store import block_index, fingerprint_for_rows, load_blocks, resolve_row_text, save_blocks


class BlockStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "blocks.json"
        self.block = {"id": "stable-1", "category": "Realism", "name": "Natural texture",
                      "description": "", "text": "Use physical material textures."}

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_library_and_roundtrip(self):
        self.assertEqual(load_blocks(self.path), [])
        save_blocks([self.block], self.path)
        self.assertEqual(load_blocks(self.path), [self.block])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["version"], 1)

    def test_linked_rows_follow_edits_and_freeze_on_missing(self):
        row = {"label": "Natural texture", "text": "Original snapshot",
               "enabled": True, "block_id": "stable-1"}
        before = block_index([self.block])
        self.assertEqual(resolve_row_text(row, before), self.block["text"])
        first = fingerprint_for_rows([row], before)
        edited = {**self.block, "text": "Use true photographic texture."}
        self.assertEqual(resolve_row_text(row, block_index([edited])), edited["text"])
        self.assertNotEqual(first, fingerprint_for_rows([row], block_index([edited])))
        self.assertEqual(resolve_row_text(row, {}), "Original snapshot")

    def test_save_creates_backup(self):
        save_blocks([self.block], self.path)
        save_blocks([{**self.block, "text": "Updated"}], self.path)
        backup = self.path.with_name("blocks.json.bak")
        self.assertTrue(backup.exists())
        self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))["blocks"][0]["text"],
                         self.block["text"])

    def test_invalid_data_fails_without_erasing(self):
        self.path.write_text('{"unexpected":"schema"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            load_blocks(self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), '{"unexpected":"schema"}')

    def test_duplicate_ids_rejected(self):
        self.path.write_text(json.dumps({"version": 1, "blocks": [self.block, self.block]}),
                             encoding="utf-8")
        with self.assertRaises(ValueError):
            load_blocks(self.path)


if __name__ == "__main__":
    unittest.main()
