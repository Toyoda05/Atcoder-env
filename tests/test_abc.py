import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cp_abc", ROOT / "tools/cp.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


class NewABC(unittest.TestCase):
    URL = "https://atcoder.jp/contests/abc350/tasks"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "templates", self.root / "templates")
        self.root_patch = patch.object(cp, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.stdout = patch("sys.stdout", new_callable=io.StringIO)
        self.stdout.start()
        self.addCleanup(self.stdout.stop)

    def page(self, task_ids, contest="abc350"):
        return "<table>" + "".join(
            f'<tr><td><a href="/contests/{contest}/tasks/{task}">A</a></td>'
            f'<td><a href="https://atcoder.jp/contests/{contest}/tasks/{task}?lang=ja">名前</a></td></tr>'
            for task in task_ids
        ) + "</table>"

    def fetch(self, html):
        return patch.object(cp, "urlopen", return_value=io.BytesIO(html.encode("utf-8")))

    def folder(self, task="abc350_a", lang="python"):
        return self.root / "contests/atcoder/abc350" / task / lang

    def snapshot(self, folder):
        return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*") if p.is_file()}

    def test_actual_task_ids_order_and_duplicates(self):
        for contest, ids in [
            ("abc001", ["abc001_1", "abc001_2", "abc001_3", "abc001_4"]),
            ("abc350", [f"abc350_{letter}" for letter in "abcdefg"]),
            ("abc212", [f"abc212_{letter}" for letter in "abcdefgh"]),
        ]:
            with self.subTest(contest=contest), self.fetch(self.page(ids, contest)):
                base = f"https://atcoder.jp/contests/{contest}/tasks"
                self.assertEqual(cp.fetch_abc_tasks(base), [f"{base}/{task}" for task in ids])

    def test_parser_ignores_unrelated_and_unsafe_links(self):
        parser = cp.TaskLinks(self.URL)
        parser.feed('''
            <a href="/contests/abc350/tasks/abc350_b">B</a>
            <a href="/contests/abc349/tasks/abc349_a">other contest</a>
            <a href="https://example.com/contests/abc350/tasks/bad">external</a>
            <a href="/contests/abc350/tasks/../bad">traversal</a>
            <a href="/contests/abc350/tasks/%2e%2e">encoded</a>
            <a href="/contests/abc350/tasks/a/b">nested</a>
            <a href="/contests/abc350/tasks">list</a>
            <a href="/contests/abc350/tasks_print">print</a>
            <a>no href</a>
            <a href="/contests/abc350/tasks/abc350_a#section">A</a>
        ''')
        self.assertEqual(parser.urls, [self.URL + "/abc350_b", self.URL + "/abc350_a"])

    def test_url_validation_happens_before_network_or_writes(self):
        for url in [
            "http://atcoder.jp/contests/abc350/tasks",
            "https://atcoder.jp.evil.test/contests/abc350/tasks",
            "https://name@atcoder.jp/contests/abc350/tasks",
            "https://atcoder.jp:8443/contests/abc350/tasks",
            "https://atcoder.jp/contests/arc100/tasks",
            self.URL + "/abc350_a",
            "https://atcoder.jp/contests/abc350",
        ]:
            with self.subTest(url=url), patch.object(cp, "urlopen") as network:
                with self.assertRaises(ValueError):
                    cp.main(["new-abc", url])
                network.assert_not_called()
        self.assertFalse((self.root / "contests").exists())

    def test_creates_both_languages_with_metadata_without_downloads(self):
        ids = ["abc350_a", "abc350_b", "abc350_g"]
        with self.fetch(self.page(ids)) as network, patch.object(cp, "download") as download:
            cp.main(["new-abc", self.URL + "/?lang=ja#top", "--no-download"])
            download.assert_not_called()
            self.assertEqual(network.call_args.args[0].full_url, self.URL)
            self.assertEqual(network.call_args.kwargs["timeout"], 30)
        for task in ids:
            for lang, suffix in [("python", "py"), ("cpp", "cpp")]:
                folder = self.folder(task, lang)
                self.assertEqual((folder / f"main.{suffix}").read_bytes(),
                                 (ROOT / "templates" / f"main.{suffix}").read_bytes())
                self.assertEqual(json.loads((folder / "problem.json").read_text()), {"url": self.URL + "/" + task})
                self.assertTrue((folder / "test").is_dir())
                self.assertEqual((folder / "input.txt").read_bytes(), b"")

    def test_rerun_preserves_every_existing_file_and_creates_missing_language(self):
        with self.fetch(self.page(["abc350_a", "abc350_b"])):
            cp.main(["new-abc", self.URL, "--no-download"])
        folder = self.folder()
        (folder / "main.py").write_text("print('my solution')\n")
        (folder / "input.txt").write_text("custom input\n")
        (folder / "test/custom.in").write_text("42\n")
        before = self.snapshot(self.root / "contests")
        with self.fetch(self.page(["abc350_a", "abc350_b"])), patch.object(cp, "download") as download:
            cp.main(["new-abc", self.URL])
            download.assert_not_called()
        self.assertEqual(before, self.snapshot(self.root / "contests"))
        shutil.rmtree(self.folder(lang="cpp"))
        before = self.snapshot(folder)
        with self.fetch(self.page(["abc350_a", "abc350_b"])):
            cp.main(["new-abc", self.URL, "--no-download"])
        self.assertEqual(before, self.snapshot(folder))
        self.assertTrue((self.folder(lang="cpp") / "main.cpp").is_file())

    def test_samples_download_once_and_are_copied_to_both_languages(self):
        def download(directory, url):
            (directory / "test").mkdir()
            (directory / "test/sample-1.in").write_text("2 3\n")
            (directory / "test/sample-1.out").write_text("5\n")
            (directory / "input.txt").write_text("2 3\n")

        with self.fetch(self.page(["abc350_a", "abc350_b"])), \
                patch.object(cp, "download", side_effect=download) as get_samples:
            cp.main(["new-abc", self.URL])
            self.assertEqual(get_samples.call_count, 2)
        for task in ("abc350_a", "abc350_b"):
            for lang in ("python", "cpp"):
                folder = self.folder(task, lang)
                self.assertEqual((folder / "test/sample-1.in").read_text(), "2 3\n")
                self.assertEqual((folder / "test/sample-1.out").read_text(), "5\n")
                self.assertEqual((folder / "input.txt").read_text(), "2 3\n")

    def test_failed_samples_keep_all_templates_and_continue(self):
        seen = []

        def download(directory, url):
            self.assertEqual(len(list((self.root / "contests").rglob("main.*"))), 4)
            seen.append(url)
            if len(seen) == 1:
                raise subprocess.CalledProcessError(1, "oj")
            (directory / "test").mkdir()
            (directory / "test/sample-1.in").write_text("1\n")
            (directory / "test/sample-1.out").write_text("1\n")

        with self.fetch(self.page(["abc350_a", "abc350_b"])), \
                patch.object(cp, "download", side_effect=download), \
                patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaisesRegex(ValueError, "1問"):
                cp.main(["new-abc", self.URL])
        self.assertEqual(seen, [self.URL + "/abc350_a", self.URL + "/abc350_b"])
        self.assertTrue((self.folder("abc350_b", "cpp") / "test/sample-1.out").is_file())

    def test_empty_or_login_page_creates_nothing(self):
        with self.fetch('<html><a href="/login">Sign in</a></html>'):
            with self.assertRaisesRegex(ValueError, "問題リンク"):
                cp.main(["new-abc", self.URL])
        self.assertFalse((self.root / "contests").exists())

    def test_network_failure_creates_nothing(self):
        with patch.object(cp, "urlopen", side_effect=URLError("unavailable")):
            with self.assertRaisesRegex(ValueError, "取得できません"):
                cp.main(["new-abc", self.URL])
        self.assertFalse((self.root / "contests").exists())

    def test_destination_symlink_cannot_escape_contests(self):
        outside = self.root / "outside"
        outside.mkdir()
        parent = self.root / "contests/atcoder"
        parent.mkdir(parents=True)
        (parent / "abc350").symlink_to(outside, target_is_directory=True)
        with self.fetch(self.page(["abc350_a"])):
            with self.assertRaises(ValueError):
                cp.main(["new-abc", self.URL, "--no-download"])
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
