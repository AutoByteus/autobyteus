
import unittest
from autobyteus.utils.diff_utils import apply_unified_diff, PatchApplicationError

class TestFuzzyPatching(unittest.TestCase):
    
    def test_ignore_whitespace(self):
        original = ["def foo():\n", "    return True\n"]
        # Patch has 2 spaces indentation in context, original has 4
        patch = """@@ -1,2 +1,2 @@
 def foo():
-  return True
+  return False
"""
        # Strict (default) should fail
        with self.assertRaises(PatchApplicationError):
            apply_unified_diff(original, patch)
            
        # With ignore_whitespace=True, it should pass
        patched = apply_unified_diff(original, patch, ignore_whitespace=True)
        self.assertEqual(patched, ["def foo():\n", "  return False\n"])
        # wait, if I used '  ' in patch +, it should be '  ' in output.
        # context line 'def foo():' matches. 
        # original line 2 '    return True' is removed.
        # new line '  return False' is added.
        
    def test_fuzz_factor(self):
        original = ["a\n", "b\n", "c\n", "d\n", "e\n"]
        # Hunk matches 'b' (line 2). 
        # Header says line 1 (which is 'a').
        # Strict fails.
        patch = """@@ -1,1 +1,1 @@
-b
+z
"""
        with self.assertRaises(PatchApplicationError):
            apply_unified_diff(original, patch)
            
        # With fuzz_factor=1, it should find 'b' at line 2 (offset +1 from specified 1).
        patched = apply_unified_diff(original, patch, fuzz_factor=1)
        # Expected result: 'a', 'z', 'c', 'd', 'e'
        self.assertEqual(patched, ["a\n", "z\n", "c\n", "d\n", "e\n"])

    def test_fuzz_factor_negative(self):
        original = ["a\n", "b\n", "c\n", "d\n", "e\n"]
        # Hunk matches 'b' (line 2).
        # Header says line 3 (which is 'c').
        # Strict fails.
        patch = """@@ -3,1 +3,1 @@
-b
+z
"""
        # With fuzz_factor=1, it should find 'b' at line 2 (offset -1 from specified 3).
        patched = apply_unified_diff(original, patch, fuzz_factor=1)
        self.assertEqual(patched, ["a\n", "z\n", "c\n", "d\n", "e\n"])

    def test_combined_fuzzy(self):
        # Wrong line number AND wrong whitespace
        original = ["    start\n", "    mid\n", "    end\n"]
        # Patch target: 'mid' (line 2). 
        # Header says line 1.
        # Content has different whitespace 'mid' vs '    mid'.
        
        patch = """@@ -1,1 +1,1 @@
-mid
+changed
"""
        patched = apply_unified_diff(original, patch, fuzz_factor=2, ignore_whitespace=True)
        self.assertEqual(patched, ["    start\n", "changed\n", "    end\n"])

if __name__ == '__main__':
    unittest.main()
