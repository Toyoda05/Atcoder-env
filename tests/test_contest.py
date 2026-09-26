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
spec = importlib.util.spec_from_file_location("cp_contest", ROOT / "tools/cp.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


class NewContest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / "templates", self.root / "templates")
        root_patch = patch.object(cp, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        stdout = patch("sys.stdout", new_callable=io.StringIO)
        stdout.start()
        self.addCleanup(stdout.stop)

    def page(self, contest, tasks):
        return "".join(
            f'<a href="/contests/{contest}/tasks/{task}">C</a>'
            f'<a href="/contests/{contest}/tasks/{task}?lang=ja">Title</a>'
            for task in tasks
        )

    def fetch(self, contest, tasks):
        return patch.object(cp, "urlopen", return_value=io.BytesIO(self.page(contest, tasks).encode()))

    def folder(self, contest, task, language):
        return self.root / "contests/atcoder" / contest / task / language

    def test_contest_types_preserve_actual_task_ids_and_metadata(self):
        for contest, tasks in [
            ("abc350", ["abc350_a", "abc350_g"]),
            ("arc100", ["arc100_a", "arc100_b"]),
            ("agc001", ["agc001_a", "agc001_f"]),
            ("ahc001", ["ahc001_a"]),
            ("typical90", ["typical90_a", "typical90_cl"]),
            ("tessoku-book", ["tessoku_book_a", "tessoku_book_bz"]),
            ("practice2", ["practice2_a", "practice2_l"]),
            ("company-test_1", ["different_prefix_1"]),
        ]:
            url = f"https://atcoder.jp/contests/{contest}/tasks"
            with self.subTest(contest=contest), self.fetch(contest, tasks) as network, \
                    patch.object(cp, "download") as download:
                cp.main(["new-contest", url + "/?lang=ja#top", "--no-download"])
                self.assertEqual(network.call_args.args[0].full_url, url)
                download.assert_not_called()
                for task in tasks:
                    for language, suffix in [("python", "py"), ("cpp", "cpp")]:
                        folder = self.folder(contest, task, language)
                        self.assertEqual((folder / f"main.{suffix}").read_bytes(),
                                         (ROOT / f"templates/main.{suffix}").read_bytes())
                        self.assertEqual(json.loads((folder / "problem.json").read_text()),
                                         {"url": f"{url}/{task}"})
                        self.assertTrue((folder / "test").is_dir())
                        self.assertEqual((folder / "input.txt").read_bytes(), b"")

    def test_invalid_urls_fail_before_network_and_file_creation(self):
        for url in [
            "http://atcoder.jp/contests/arc100/tasks",
            "https://example.com/contests/arc100/tasks",
            "https://atcoder.jp.evil.test/contests/arc100/tasks",
            "https://user@atcoder.jp/contests/arc100/tasks",
            "https://atcoder.jp:8443/contests/arc100/tasks",
            "https://atcoder.jp/contests/arc100",
            "https://atcoder.jp/contests/arc100/tasks/arc100_a",
            "https://atcoder.jp/contests/../tasks",
            "https://atcoder.jp/contests/%2e%2e/tasks",
            "https://atcoder.jp/contests/a/b/tasks",
            "https://atcoder.jp/contests//tasks",
        ]:
            with self.subTest(url=url), patch.object(cp, "urlopen") as network:
                with self.assertRaises(ValueError):
                    cp.main(["new-contest", url])
                network.assert_not_called()
        self.assertFalse((self.root / "contests").exists())

    def test_samples_download_once_rerun_preserves_solutions_and_custom_tests(self):
        url = "https://atcoder.jp/contests/tessoku-book/tasks"
        calls = []

        def download(directory, task_url):
            calls.append(task_url)
            (directory / "test").mkdir()
            (directory / "test/sample-1.in").write_text("2 3\n")
            (directory / "test/sample-1.out").write_text("5\n")
            (directory / "input.txt").write_text("2 3\n")

        with self.fetch("tessoku-book", ["tessoku_book_a"]), patch.object(cp, "download", side_effect=download):
            cp.main(["new-contest", url])
        self.assertEqual(calls, [url + "/tessoku_book_a"])
        for language in ("python", "cpp"):
            folder = self.folder("tessoku-book", "tessoku_book_a", language)
            self.assertEqual((folder / "test/sample-1.out").read_text(), "5\n")
            self.assertEqual((folder / "input.txt").read_text(), "2 3\n")
        python = self.folder("tessoku-book", "tessoku_book_a", "python")
        (python / "main.py").write_text("print('working solution')\n")
        (python / "test/custom.in").write_text("10\n")
        before = {p.relative_to(python): p.read_bytes() for p in python.rglob("*") if p.is_file()}
        shutil.rmtree(self.folder("tessoku-book", "tessoku_book_a", "cpp"))
        with self.fetch("tessoku-book", ["tessoku_book_a"]), patch.object(cp, "download", side_effect=download):
            cp.main(["new-contest", url])
        self.assertEqual(len(calls), 2)
        self.assertEqual(before, {p.relative_to(python): p.read_bytes() for p in python.rglob("*") if p.is_file()})
        with self.fetch("tessoku-book", ["tessoku_book_a"]), patch.object(cp, "download") as download_mock:
            cp.main(["new-contest", url])
            download_mock.assert_not_called()

    def test_failed_sample_download_keeps_templates_and_continues(self):
        urls = []

        def download(directory, url):
            self.assertEqual(len(list(self.root.rglob("contests/**/main.*"))), 4)
            urls.append(url)
            if len(urls) == 1:
                raise subprocess.CalledProcessError(1, "oj")
            (directory / "test").mkdir()
            (directory / "test/sample-1.in").write_text("1\n")
            (directory / "test/sample-1.out").write_text("1\n")

        with self.fetch("arc100", ["arc100_a", "arc100_b"]), \
                patch.object(cp, "download", side_effect=download), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaisesRegex(ValueError, "1問"):
                cp.main(["new-contest", "https://atcoder.jp/contests/arc100/tasks"])
        self.assertEqual(len(urls), 2)
        self.assertTrue((self.folder("arc100", "arc100_b", "cpp") / "test/sample-1.out").is_file())

    def test_unavailable_task_list_creates_nothing(self):
        for response in (io.BytesIO(b'<a href="/login">Log in</a>'), URLError("unavailable")):
            kwargs = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
            with self.subTest(response=response), patch.object(cp, "urlopen", **kwargs):
                with self.assertRaises(ValueError):
                    cp.main(["new-contest", "https://atcoder.jp/contests/arc100/tasks"])
            self.assertFalse((self.root / "contests").exists())


if __name__ == "__main__":
    unittest.main()
