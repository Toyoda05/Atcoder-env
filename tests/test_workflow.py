import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib/python"))
from cp_lib.dsu import DSU

spec = importlib.util.spec_from_file_location("cp_workflow", ROOT / "tools/cp.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


class Libraries(unittest.TestCase):
    def test_dsu_against_naive_partition(self):
        rng = random.Random(420)
        n = 35
        labels = list(range(n))
        uf = DSU(n)
        for _ in range(500):
            a, b = rng.randrange(n), rng.randrange(n)
            if rng.randrange(2):
                old, new = labels[b], labels[a]
                labels = [new if x == old else x for x in labels]
                uf.merge(a, b)
            self.assertEqual(uf.same(a, b), labels[a] == labels[b])
            self.assertEqual(uf.size(a), labels.count(labels[a]))

    def test_cpp_library_matches_acl_randomly(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "check.cpp"
            source.write_text('''
#include "cp/dsu.hpp"
#include <atcoder/dsu>
#include <random>
#include <cassert>
int main() {
    std::mt19937 rng(42);
    cp::DSU a(50); atcoder::dsu b(50);
    for (int i = 0; i < 1000; ++i) {
        int x = rng() % 50, y = rng() % 50;
        if (rng() % 2) { a.merge(x,y); b.merge(x,y); }
        assert(a.same(x,y) == b.same(x,y));
        assert(a.size(x) == b.size(x));
    }
}
''', encoding="utf-8")
            subprocess.run(["g++", "-std=c++20", "-fsanitize=address,undefined", "-g",
                            "-I", str(cp.CPPLIB), "-I", str(cp.ACL), str(source), "-o", str(directory / "check")], check=True)
            subprocess.run([str(directory / "check")], check=True)


class Bundles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.lib = self.directory / "libs"
        (self.lib / "cp_lib").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def module(self, name, content):
        path = self.lib / "cp_lib" / (name + ".py")
        path.write_text(content, encoding="utf-8")
        return path

    def program(self, content):
        path = self.directory / "main.py"
        path.write_text(content, encoding="utf-8")
        return path

    def test_python_dependency_order_and_duplicate_imports(self):
        self.module("base", "def twice(x):\n    return 2*x\n")
        self.module("higher", "from cp_lib.base import twice\ndef result():\n    return twice(21)\n")
        source = self.program('from __future__ import annotations\nfrom cp_lib.higher import result\nfrom cp_lib.base import twice\nprint(result(), twice(2))\n')
        content = cp.bundle_python(source, self.lib)
        self.assertEqual(content.count("def twice("), 1)
        standalone = self.directory / "submission.py"
        standalone.write_text(content, encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", str(standalone)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "42 4\n")

    def test_python_rejects_unsupported_import_forms(self):
        self.module("x", "class X: pass\n")
        for content in ["import cp_lib.x\n", "from cp_lib.x import X as Y\n",
                        "from cp_lib.x import *\n", "def f():\n    from cp_lib.x import X\n",
                        "from cp_lib.x import X; print(X)\n"]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                cp.bundle_python(self.program(content), self.lib)

    def test_python_rejects_circular_dependencies(self):
        self.module("a", "from cp_lib.b import B\nclass A: pass\n")
        self.module("b", "from cp_lib.a import A\nclass B: pass\n")
        with self.assertRaisesRegex(ValueError, "循環"):
            cp.bundle_python(self.program("from cp_lib.a import A\n"), self.lib)

    def test_python_rejects_duplicate_library_symbols(self):
        self.module("a", "class X: pass\n")
        self.module("b", "class X: pass\n")
        with self.assertRaisesRegex(ValueError, "衝突"):
            cp.bundle_python(self.program("from cp_lib.a import X\nfrom cp_lib.b import X\n"), self.lib)

    def test_cpp_rejects_missing_header(self):
        source = self.directory / "main.cpp"
        source.write_text('#include "cp/does-not-exist.hpp"\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ヘッダ"):
            cp.bundle_cpp(source)

    def test_cpp_and_python_standalone_match_samples(self):
        for language, suffix in [("python", ".py"), ("cpp", ".cpp")]:
            with self.subTest(language=language):
                original = ROOT / "examples" / language / ("main" + suffix)
                output = self.directory / ("submission" + suffix)
                content = cp.bundle_python(original) if suffix == ".py" else cp.bundle_cpp(original)
                output.write_text(content, encoding="utf-8")
                if suffix == ".py":
                    command = [sys.executable, "-I", str(output)]
                else:
                    executable = self.directory / "submission"
                    subprocess.run(["g++", "-std=c++20", str(output), "-o", str(executable)], check=True)
                    command = [str(executable)]
                sample = original.parent / "test/sample-1.in"
                expected = sample.with_suffix(".out").read_bytes()
                result = subprocess.run(command, input=sample.read_bytes(), capture_output=True,
                                        cwd=self.directory, check=True, env=cp.environment(True))
                self.assertEqual(result.stdout, expected)


class Workflow(unittest.TestCase):
    def test_new_problem_preserves_url_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "templates").mkdir()
            (root / "templates/main.py").write_text("print('template')\n", encoding="utf-8")
            url = "https://atcoder.jp/contests/abs/tasks/abc086_a"
            arguments = ["new", url, "--lang", "python", "--no-download"]
            with patch.object(cp, "ROOT", root):
                cp.main(arguments)
                folder = root / "contests/atcoder/abs/abc086_a/python"
                self.assertEqual(json.loads((folder / "problem.json").read_text())["url"], url)
                (folder / "main.py").write_text("important solution\n", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    cp.main(arguments)
                self.assertEqual((folder / "main.py").read_text(), "important solution\n")

    def test_copy_uses_tested_bundle_as_unicode(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "submission.py"
            content = "# 日本語コメント\nprint(42)\n"
            target.write_text(content, encoding="utf-8")
            with patch.object(cp, "bundle", return_value=target), \
                 patch.object(cp, "test_file") as validate, \
                 patch.object(cp, "call") as external:
                cp.main(["copy", str(ROOT / "examples/python/main.py")])
                validate.assert_called_once()
                self.assertTrue(validate.call_args.kwargs["standalone"])
                self.assertEqual(external.call_args.kwargs["input"].decode("utf-16-le"), content)

    def test_missing_tests_block_preparation(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            cp.test_file(ROOT / "examples/python/main.py", Path(temp))

    def test_wrong_answer_is_rejected_by_real_runner(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "bad.py"
            source.write_text("print('wrong answer')\n", encoding="utf-8")
            with self.assertRaises(subprocess.CalledProcessError):
                cp.test_file(source, ROOT / "examples/python/test", standalone=True)

    def test_failed_test_prevents_submission(self):
        with patch.object(cp, "bundle", return_value=ROOT / "examples/python/main.py"), \
             patch.object(cp, "test_file", side_effect=ValueError("test failed")), \
             patch.object(cp, "call") as external, self.assertRaises(ValueError):
            cp.main(["submit", str(ROOT / "examples/python/main.py"),
                     "--url", "https://atcoder.jp/contests/abs/tasks/abc086_a", "--language", "dummy"])
        external.assert_not_called()

    def test_new_problem_cannot_escape_contests(self):
        with self.assertRaises(ValueError):
            cp.main(["new", "https://atcoder.jp/contests/abs/tasks/abc086_a",
                     "--lang", "python", "--name", "../../outside", "--no-download"])


if __name__ == "__main__":
    unittest.main()
