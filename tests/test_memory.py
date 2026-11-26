"""Storage safety tests for core/memory.py (Task 2: D1, D6)."""
import glob
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from core import memory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MemoryTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "data", "memory.json")
        patcher = mock.patch.object(memory, "MEMORY_FILE", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_raw(self, raw: bytes):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "wb") as f:
            f.write(raw)

    def backups(self):
        return glob.glob(self.path + ".corrupt-*")


class TestPath(unittest.TestCase):
    def test_path_is_anchored_to_project_not_cwd(self):
        # Import from a different cwd and check where MEMORY_FILE points.
        out = subprocess.check_output(
            [sys.executable, "-c", "from core import memory; print(memory.MEMORY_FILE)"],
            cwd=tempfile.gettempdir(),
            env={**os.environ, "PYTHONPATH": ROOT},
            text=True,
        ).strip()
        self.assertEqual(out, os.path.join(ROOT, "data", "memory.json"))


class TestSave(MemoryTestCase):
    def test_save_creates_missing_data_dir(self):
        memory.save_message("user", "hello")
        self.assertIn("User: hello", memory.get_history())

    def test_concurrent_saves_lose_nothing(self):
        def worker(tag):
            for i in range(100):
                memory.save_message("user", f"{tag}-{i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in "ab"]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(memory.load_memory()["history"]), 200)

    def test_failed_write_leaves_old_file_intact(self):
        memory.save_message("user", "keep me")
        before = Path(self.path).read_bytes()

        with mock.patch.object(memory.os, "replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                memory.save_message("user", "lost")

        self.assertEqual(Path(self.path).read_bytes(), before)
        leftovers = [n for n in os.listdir(os.path.dirname(self.path)) if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])


class TestCorruption(MemoryTestCase):
    def assert_backed_up(self, raw: bytes):
        self.write_raw(raw)
        self.assertEqual(memory.load_memory(), {"facts": {}, "history": []})
        [backup] = self.backups()
        self.assertEqual(Path(backup).read_bytes(), raw)
        self.assertFalse(os.path.exists(self.path))

    def test_invalid_json_is_backed_up(self):
        self.assert_backed_up(b'{"facts": {}, "history": [')

    def test_non_dict_is_backed_up(self):
        self.assert_backed_up(b"[1, 2, 3]")

    def test_wrong_field_types_are_backed_up(self):
        self.assert_backed_up(json.dumps({"facts": [], "history": {}}).encode())

    def test_history_entry_without_content_is_backed_up(self):
        self.assert_backed_up(json.dumps({"history": [{"role": "user"}]}).encode())

    def test_valid_file_with_missing_keys_is_kept(self):
        self.write_raw(json.dumps({"facts": {"user_name": "Alex"}}).encode())
        self.assertEqual(memory.get_user_name(), "Alex")
        self.assertEqual(self.backups(), [])

    def test_next_save_after_corruption_does_not_touch_backup(self):
        raw = b"not json at all"
        self.write_raw(raw)
        memory.save_message("user", "fresh start")
        [backup] = self.backups()
        self.assertEqual(Path(backup).read_bytes(), raw)
        self.assertIn("User: fresh start", memory.get_history())


if __name__ == "__main__":
    unittest.main()
