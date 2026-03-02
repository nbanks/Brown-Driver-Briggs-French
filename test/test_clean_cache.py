#!/usr/bin/env python3
"""Tests for clean cache invalidation in scripts/llm_common.py."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from llm_common import load_clean_cache, update_clean_cache, check_clean_cache


class TestCacheScriptInvalidation(unittest.TestCase):
    """Cache should be invalidated when scripts are newer than cache file."""

    def test_cache_invalidated_when_scripts_newer(self):
        """If any script in scripts_dir is newer than the cache, ignore cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create dummy input files
            orig = tmpdir / "orig.html"
            txt_fr = tmpdir / "txt_fr.txt"
            fr = tmpdir / "fr.html"
            orig.write_text("<html>orig</html>")
            txt_fr.write_text("texte")
            fr.write_text("<html>fr</html>")

            # Build a cache with one clean entry
            cache_path = tmpdir / "clean.txt"
            update_clean_cache(cache_path, "BDB1234", orig, txt_fr, fr)

            # Verify the cache works normally (no scripts_dir = real scripts,
            # but we'll use a controlled dir for the invalidation test)
            scripts_dir = tmpdir / "scripts"
            scripts_dir.mkdir()

            # Scripts older than cache — cache should be valid
            old_script = scripts_dir / "dummy.py"
            old_script.write_text("pass")
            past = time.time() - 200
            os.utime(old_script, (past, past))

            cache = load_clean_cache(cache_path, scripts_dir=scripts_dir)
            self.assertIn("BDB1234", cache)
            self.assertTrue(
                check_clean_cache(cache, "BDB1234", orig, txt_fr, fr))

            # Now make a script newer than the cache
            new_script = scripts_dir / "new_validator.py"
            new_script.write_text("# changed")
            future = time.time() + 100
            os.utime(new_script, (future, future))

            cache2 = load_clean_cache(cache_path, scripts_dir=scripts_dir)
            self.assertEqual(cache2, {},
                             "Cache should be empty when scripts are newer")

    def test_cache_valid_when_scripts_older(self):
        """If all scripts are older than the cache, cache is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            orig = tmpdir / "orig.html"
            txt_fr = tmpdir / "txt_fr.txt"
            fr = tmpdir / "fr.html"
            orig.write_text("<html>orig</html>")
            txt_fr.write_text("texte")
            fr.write_text("<html>fr</html>")

            # Controlled scripts dir with old scripts
            scripts_dir = tmpdir / "scripts"
            scripts_dir.mkdir()
            old_script = scripts_dir / "dummy.py"
            old_script.write_text("pass")
            past = time.time() - 200
            os.utime(old_script, (past, past))

            cache_path = tmpdir / "clean.txt"
            update_clean_cache(cache_path, "BDB5678", orig, txt_fr, fr)

            cache = load_clean_cache(cache_path, scripts_dir=scripts_dir)
            self.assertIn("BDB5678", cache)


if __name__ == "__main__":
    unittest.main()
